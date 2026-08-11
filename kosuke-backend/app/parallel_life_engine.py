"""Parallel Life generation engine.

Parallel Life is the first primary public experience of Kosuke Protocol (see
product spec). It reads a single life branch — a job not taken, a city not
lived in, a relationship not continued — as a structured document: the
branch point, the chosen path, the unchosen life, what was lost, what was
protected, the residue that still returns, an Observatory Layer that reads
the branch through two-to-four social lenses, a cross-lens synthesis, a small
re-branch, and a closing.

Generation prefers an LLM (via ``OPENAI_API_KEY``) with strict structured
validation and one safe retry, and always falls back to a coherent, native,
language-safe heuristic so the experience works with no API key configured
(product spec §7, §28, §34).

Nothing here talks to ChromaDB or the fragment ecosystem — Parallel Life is a
self-contained structured-generation flow, not a sampling flow.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass

from app.models import (
    ClarificationQuestion,
    ObservatoryLayer,
    ParallelLifeClarifications,
    ParallelLifeRequest,
    ParallelLifeResult,
)
from app.observatory_lenses import (
    OBSERVATORY_LENSES,
    select_observatory_lenses,
    validate_lens_ids,
)
from app.parallel_life_facts import (
    ParallelLifeFacts,
    extract_parallel_life_facts,
    facts_prompt_block,
    validate_factual_consistency,
)
from app.parallel_life_seed import seed_line_for_domain

_CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def _is_ja(language: str, text: str = "") -> bool:
    if language and language.lower().startswith("ja"):
        return True
    return bool(_CJK_RE.search(text))


def _has_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def _seed(*parts: str) -> int:
    joined = "|".join(p or "" for p in parts)
    return int(hashlib.md5(joined.encode("utf-8")).hexdigest(), 16)


_REPEATED_DOTS_RE = re.compile(r"\.{2,}")
_ELLIPSIS_RUN_RE = re.compile(r"…+")


def _clean_line(text: str) -> str:
    """Normalize a line of generated or user-provided text.

    Public Parallel Life output never contains truncated source excerpts (see
    the editorial-quality pass), but user-authored clarification answers or
    stray LLM output could still contain repeated-period or double-ellipsis
    artifacts (e.g. "went....", "hometow…."). This collapses both into a
    single, correct ellipsis character so no field can leak a malformed
    truncation marker.
    """
    cleaned = (text or "").strip().strip('"').strip("“”").strip("「」")
    cleaned = _REPEATED_DOTS_RE.sub("…", cleaned)
    cleaned = _ELLIPSIS_RUN_RE.sub("…", cleaned)
    return cleaned.strip()


# --- Clarification questions -------------------------------------------------

_QUESTION_POOL_JA: dict[str, str] = {
    "age": "そのとき、何歳でしたか。",
    "chosen_path": "実際に選んだ道は何でしたか。",
    "unchosen_path": "選ばなかった道は何でしたか。",
    "what_remains": "今も心に残っているのは、どんなことですか。",
    "constraints": "当時、選択を制限していたものは何でしたか。",
    "lost": "今振り返ると、失ったと感じるものはありますか。",
    "protected": "逆に、守られたと思うものはありますか。",
}

_QUESTION_POOL_EN: dict[str, str] = {
    "age": "How old were you at the time?",
    "chosen_path": "What path did you actually choose?",
    "unchosen_path": "What path did you leave unchosen?",
    "what_remains": "What still remains with you now?",
    "constraints": "What limited your choices at the time?",
    "lost": "What do you feel was lost?",
    "protected": "What do you feel may have been protected?",
}

_AGE_RE = re.compile(r"(\d{1,3})\s*(?:歳|才|years?\s*old|yo\b)", re.IGNORECASE)
_UNCHOSEN_HINT_RE = re.compile(
    r"(もし.{0,20}(たら|れば)|だったら|していたら|残っていたら|続けていたら|"
    r"\bif i (had|stayed|continued|kept|took|moved)\b|\bwhat if\b)",
    re.IGNORECASE,
)


def _default_question_order(ja: bool) -> list[str]:
    return ["age", "what_remains", "constraints", "lost"]


def _heuristic_clarification_questions(
    source_text: str, language: str
) -> list[ClarificationQuestion]:
    ja = _is_ja(language, source_text)
    pool = _QUESTION_POOL_JA if ja else _QUESTION_POOL_EN

    candidates = _default_question_order(ja)
    if _AGE_RE.search(source_text or ""):
        candidates = [q for q in candidates if q != "age"]
    if _UNCHOSEN_HINT_RE.search(source_text or ""):
        candidates = [q for q in candidates if q != "unchosen_path"]

    # Keep it compact: prefer 3, never exceed 4.
    selected = candidates[:3] if len(candidates) >= 3 else candidates
    if not selected:
        selected = ["what_remains"]

    return [ClarificationQuestion(id=qid, question=pool[qid]) for qid in selected[:4]]


async def _llm_clarification_questions(
    source_text: str, language: str, api_key: str
) -> list[ClarificationQuestion]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    ja = _is_ja(language, source_text)
    pool = _QUESTION_POOL_JA if ja else _QUESTION_POOL_EN
    ids = ", ".join(pool.keys())

    if ja:
        system_prompt = (
            "あなたは Parallel Life（Kosuke Protocol）の一部として、書かれた人生の分岐について、"
            "本文にまだ書かれていない、必要最小限の追加質問を選びます。守ること：\n"
            "- 選択肢のIDだけを、次の集合から選ぶ：" + ids + "\n"
            "- すでに文章の中で答えられている質問は選ばない\n"
            "- 2〜3個を優先し、最大4個まで\n"
            "- 実名・住所・勤務先名・病名・具体的な金額・第三者を特定できる情報は求めない\n"
            "JSON配列だけで答える。例：[\"age\", \"what_remains\"]"
        )
    else:
        system_prompt = (
            "You are part of Parallel Life (Kosuke Protocol). Given a written life branch, "
            "choose the minimal set of additional questions not already answered in the text. "
            "Rules:\n"
            "- Choose only IDs from this set: " + ids + "\n"
            "- Never choose a question already answered in the text\n"
            "- Prefer 2-3, never more than 4\n"
            "- Never ask for full names, addresses, employer names, medical diagnoses, "
            "exact financial amounts, or identifying details about third parties\n"
            "Respond with a JSON array only, e.g. [\"age\", \"what_remains\"]"
        )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Branch text:\n{source_text}"},
        ],
        temperature=0.3,
        max_tokens=80,
    )
    content = (response.choices[0].message.content or "").strip()
    content = content.strip("`")
    if content.lower().startswith("json"):
        content = content[4:].strip()
    ids_out = json.loads(content)
    if not isinstance(ids_out, list):
        raise ValueError("Expected a JSON array of question ids")

    result: list[ClarificationQuestion] = []
    seen: set[str] = set()
    for qid in ids_out:
        if isinstance(qid, str) and qid in pool and qid not in seen:
            seen.add(qid)
            result.append(ClarificationQuestion(id=qid, question=pool[qid]))
    if not result:
        raise ValueError("LLM returned no valid question ids")
    return result[:4]


async def generate_clarification_questions(
    source_text: str, language: str = "ja"
) -> list[ClarificationQuestion]:
    """Return 0-4 optional clarification questions for a life branch.

    Answers are never required; the caller may skip straight to generation.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            return await _llm_clarification_questions(source_text, language, api_key)
        except Exception:
            pass
    return _heuristic_clarification_questions(source_text, language)


# --- Topic extraction (heuristic generation only) ----------------------------
#
# The public document never quotes or paraphrases the raw source text back at
# the user ("The branch appears inside \"...\"", "という入力の中には..."). Instead
# it extracts a *topic* — a short, natural category the branch is about — and
# writes original editorial prose around it. Each topic carries two forms:
# ``prose`` (a natural phrase for use inside a sentence, e.g. "that
# relationship") and ``title`` (a bare noun phrase with no leading
# article/demonstrative, safe to compose into title templates like
# "The {title} Not Chosen" without duplicating a determiner).


@dataclass(frozen=True)
class _Topic:
    keywords: tuple[str, ...]
    prose: str
    title: str
    # Coarse branch category used only to select a relevant, concrete
    # Re-branch pool (education / work / relationship / place / creativity /
    # care / default). Never shown to the user directly.
    category: str = "default"


_TOPICS_JA: tuple[_Topic, ...] = (
    # Family-formation MUST outrank creativity/work — explicit childbirth /
    # fertility events must never be reclassified as creative practice.
    _Topic(
        ("不妊", "授かった", "産まれ", "生まれた", "出産", "息子", "娘", "二人目", "三人家族"),
        "家族形成",
        "家族形成",
        category="family_formation",
    ),
    _Topic(("東京",), "東京", "東京", category="place"),
    _Topic(("京都",), "京都", "京都", category="place"),
    _Topic(("大阪",), "大阪", "大阪", category="place"),
    _Topic(("海外", "留学"), "海外", "海外", category="place"),
    _Topic(("大学", "受験", "進学", "入試", "浪人"), "その進学先", "進学先", category="education"),
    _Topic(
        ("結婚", "彼氏", "彼女", "恋愛", "パートナー", "交際"),
        "その恋愛",
        "恋愛",
        category="relationship",
    ),
    _Topic(
        ("子ども", "子供", "育児"),
        "子どもを持つこと",
        "子どもを持つ人生",
        category="family_formation",
    ),
    _Topic(("介護",), "家族の介護", "介護", category="care"),
    # Creativity keywords are intentionally narrow — avoid 「作品」「表現」
    # which can appear in unrelated literary commentary.
    _Topic(
        ("創作", "小説", "執筆", "音楽活動", "画家"), "その創作", "創作", category="creativity"
    ),
    _Topic(
        ("会社", "仕事", "就職", "転職", "退職", "内定"), "その仕事", "仕事", category="work"
    ),
    _Topic(("地元", "故郷", "田舎", "帰郷"), "地元", "地元", category="place"),
)
# The default (no keyword matched) topic is deliberately a plain, natural
# phrase — "その道" ("that path") — rather than "あの分岐" ("that branch"),
# because it is reused inside many different sentence frames (chosen path,
# unchosen life, residue). "分岐" reads naturally as a bare title noun but
# awkwardly when substituted into "〜を退けたというより" style sentences.
_DEFAULT_TOPIC_JA = _Topic((), "その道", "分岐")

_TOPICS_EN: tuple[_Topic, ...] = (
    _Topic(
        ("fertility", "gave birth", "was born", "had a son", "had a daughter", "second child"),
        "family formation",
        "Family Formation",
        category="family_formation",
    ),
    _Topic(("tokyo",), "Tokyo", "Tokyo", category="place"),
    _Topic(
        ("abroad", "overseas", "study abroad"),
        "that time abroad",
        "Time Abroad",
        category="place",
    ),
    _Topic(
        ("university", "college", "exam", "admission"),
        "that university path",
        "University Path",
        category="education",
    ),
    _Topic(
        ("love", "relationship", "partner", "boyfriend", "girlfriend", "married", "marry"),
        "that relationship",
        "Relationship",
        category="relationship",
    ),
    _Topic(("child", "children", "kids", "parenthood"), "having children", "Parenthood", category="family_formation"),
    _Topic(("caregiving",), "family care", "Family Care", category="care"),
    _Topic(
        ("creative practice", "stopped writing", "left writing", "novel", "painting career"),
        "that creative work",
        "Creative Work",
        category="creativity",
    ),
    _Topic(
        ("job", "work", "career", "company", "resign", "quit"),
        "that job",
        "Job",
        category="work",
    ),
    _Topic(("hometown", "countryside", "home town"), "home", "Hometown", category="place"),
)
# See the note on ``_DEFAULT_TOPIC_JA`` above — "that path" reads naturally
# inside every sentence frame that substitutes a topic; the old fallback
# ("that branch") is also what produced the reported malformed title.
_DEFAULT_TOPIC_EN = _Topic((), "that path", "Path")


def _match_topic(text: str, ja: bool) -> _Topic:
    lowered = (text or "").lower()
    table = _TOPICS_JA if ja else _TOPICS_EN
    for topic in table:
        for kw in topic.keywords:
            if (kw in text) if ja else (kw in lowered):
                return topic
    return _DEFAULT_TOPIC_JA if ja else _DEFAULT_TOPIC_EN


def _format_age(age: str | None, ja: bool) -> str | None:
    if not age:
        return None
    match = re.search(r"\d{1,3}", age)
    if not match:
        return age.strip() or None
    num = match.group(0)
    return f"{num}歳" if ja else f"{num}"


# --- Title / subtitle ---------------------------------------------------------
#
# Every title template below composes a *bare* noun phrase (``_Topic.title`` —
# no leading article, demonstrative, or gerund marker, e.g. "Relationship",
# not "that relationship" or "having children"). This is the fix for the
# reported "The that branch Not Chosen at 24" bug: the old fallback topic
# string ("that branch") already carried an implicit determiner, which
# collided with the template's own "The ...". Because every title noun here
# is bare, "The {kw} ..." can never produce a duplicated determiner.

# Default title pools assume a "not-chosen / left" polarity. Polarity-aware
# pools below override these when extract_parallel_life_facts() detects an
# explicit admitted / stayed / resigned / married direction.
_JA_TITLE_WITH_AGE = [
    "{kw}に残らなかった{age}",
    "{age}、{kw}を選ばなかった年",
    "{kw}を離れた{age}",
]
_JA_TITLE_NO_AGE = [
    "戻らなかった{kw}",
    "選ばなかった{kw}",
    "{kw}という分岐点",
    "{kw}に残した問い",
    "続けなかった{kw}",
]
_EN_TITLE_WITH_AGE = [
    "The {kw} Not Chosen at {age}",
    "Leaving {kw} at {age}",
    "Not Choosing {kw} at {age}",
]
_EN_TITLE_NO_AGE = [
    "The {kw} Not Returned To",
    "Not Choosing the {kw}",
    "What the {kw} Did Not Become",
    "A Question Left in the {kw}",
    "The {kw} Left Behind",
]

# Admission / success polarity — must never use rejection title frames.
_JA_TITLE_ADMITTED_WITH_AGE = [
    "{age}、{kw}に進んだ年",
    "{kw}に受かった{age}",
    "{age}の{kw}",
]
_JA_TITLE_ADMITTED_NO_AGE = [
    "{kw}という分岐点",
    "受かったあとの{kw}",
    "{kw}に進んだ道",
    "{kw}が開いた問い",
]
_EN_TITLE_ADMITTED_WITH_AGE = [
    "Entering {kw} at {age}",
    "Accepted to {kw} at {age}",
    "The {kw} Chosen at {age}",
]
_EN_TITLE_ADMITTED_NO_AGE = [
    "The {kw} That Opened",
    "After Getting Into {kw}",
    "Choosing the {kw}",
    "A Question After {kw}",
]

_JA_TITLE_STAYED_NO_AGE = [
    "{kw}に残った道",
    "{kw}という選択",
    "残った先の{kw}",
]
_EN_TITLE_STAYED_NO_AGE = [
    "Staying in {kw}",
    "The {kw} That Remained",
    "Choosing to Stay in {kw}",
]
_JA_TITLE_LEFT_NO_AGE = [
    "{kw}を離れた道",
    "離れたあとの{kw}",
    "{kw}という分岐点",
]
_EN_TITLE_LEFT_NO_AGE = [
    "Leaving {kw}",
    "After Leaving {kw}",
    "The Branch Away from {kw}",
]
_JA_TITLE_RESIGNED_NO_AGE = [
    "辞めたあとの{kw}",
    "{kw}を離れた道",
    "{kw}という分岐点",
]
_EN_TITLE_RESIGNED_NO_AGE = [
    "After Leaving the {kw}",
    "The {kw} Set Aside",
    "A Branch After the {kw}",
]
_JA_TITLE_WORK_STAYED_NO_AGE = [
    "{kw}に残った道",
    "続けた{kw}",
    "{kw}という選択",
]
_EN_TITLE_WORK_STAYED_NO_AGE = [
    "Staying with the {kw}",
    "Continuing the {kw}",
    "The {kw} Kept",
]
_JA_TITLE_MARRIED_NO_AGE = [
    "結婚という分岐点",
    "結婚したあとの問い",
    "選んだ結婚",
]
_EN_TITLE_MARRIED_NO_AGE = [
    "The Marriage Chosen",
    "After Getting Married",
    "A Branch Around Marriage",
]
_JA_TITLE_NOT_MARRIED_NO_AGE = [
    "結婚しなかった道",
    "結婚という分岐点",
    "選ばなかった結婚",
]
_EN_TITLE_NOT_MARRIED_NO_AGE = [
    "The Marriage Not Chosen",
    "Not Marrying",
    "A Branch Around Not Marrying",
]

_JA_SAFE_FALLBACK_TITLE = "名前のない分岐点"
_JA_SAFE_NEUTRAL_TITLE = "進学をめぐる分岐点"
_EN_SAFE_FALLBACK_TITLE = "A Path Not Chosen"
_EN_SAFE_NEUTRAL_TITLE = "A Branch Around Education"

_JA_SUBTITLE_POOL = [
    "捨てたのではなく、まず自分の生活をつくろうとした。",
    "どちらか一方を否定するための選択ではなかった。",
    "手放したものと、守ろうとしたものが、同時にあった。",
    "選んだのは道そのものではなく、そのときの生き方だった。",
    "正しさの問題ではなく、そのとき何が可能だったかの問題だった。",
]
_EN_SUBTITLE_POOL = [
    "It was not a rejection, but an attempt to build a life first.",
    "The choice did not require condemning what it left behind.",
    "What was released and what was protected arrived at the same time.",
    "What was chosen was a way of living, not the path itself.",
    "It was less a question of right and wrong than of what was possible then.",
]

# Function words allowed to stay lowercase inside a Title Case English title
# (but never as the first or last word).
_EN_TITLE_CASE_MINOR_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "at", "by", "to",
    "in", "of", "on", "with", "not", "as", "into", "from",
}
# Determiner-class words that must never sit directly next to one another
# (the exact shape of the reported bug: "The that branch").
_EN_DETERMINERS = {"the", "a", "an", "that", "this", "these", "those", "another"}
_EN_TITLE_BAD_SUBSTRINGS = (
    "not chose ", "not chose.", "did not chosen", "not chosen the not",
)


def _is_valid_english_title(title: str) -> bool:
    """Structural validation for a generated English title.

    Catches the reported bug class (duplicated adjacent determiners, e.g.
    "The that branch"), template leftovers, truncation markers, unbalanced
    quotes, and titles that are not in a plausible title-case, complete-
    noun-phrase shape. This is intentionally structural rather than a full
    grammar checker — it cannot verify verb tense, but it does reject the
    specific malformed constructions this pass was asked to prevent.
    """
    title = (title or "").strip()
    if not title:
        return False
    if "{" in title or "}" in title or "None" in title or "null" in title.lower():
        return False
    if "…" in title or ".." in title:
        return False
    if title.count('"') % 2 != 0:
        return False
    lowered = title.lower()
    if any(bad in lowered for bad in _EN_TITLE_BAD_SUBSTRINGS):
        return False

    words = title.split()
    if not (3 <= len(words) <= 12):
        return False

    normalized = [re.sub(r"[^\w'-]", "", w).lower() for w in words]
    for i in range(len(normalized) - 1):
        if not normalized[i] or not normalized[i + 1]:
            continue
        if normalized[i] == normalized[i + 1]:
            return False  # duplicated adjacent word, e.g. "The The"
        if normalized[i] in _EN_DETERMINERS and normalized[i + 1] in _EN_DETERMINERS:
            return False  # duplicated adjacent determiner, e.g. "The that"

    def _starts_upper(word: str) -> bool:
        core = re.sub(r"^[^A-Za-z0-9]+", "", word)
        if not core:
            return False
        # A title may end in a bare age numeral (e.g. "... at 24"); digits
        # have no case, so treat them as satisfying title-case at a boundary.
        return core[0].isdigit() or core[0].isupper()

    if not _starts_upper(words[0]) or not _starts_upper(words[-1]):
        return False
    for word in words[1:-1]:
        core = re.sub(r"[^\w'-]", "", word)
        if core and core[0].islower() and core.lower() not in _EN_TITLE_CASE_MINOR_WORDS:
            return False
    return True


def _is_valid_japanese_title(title: str) -> bool:
    """Structural validation for a generated Japanese title."""
    title = (title or "").strip()
    if not title:
        return False
    if "{" in title or "}" in title:
        return False
    if "…" in title or ".." in title:
        return False
    if title.count('"') % 2 != 0 or title.count("「") != title.count("」"):
        return False
    if not (2 <= len(title) <= 40):
        return False
    return _has_cjk(title)


def _safe_fallback_title(
    topic: _Topic, age: str | None, ja: bool, facts: ParallelLifeFacts | None = None
) -> str:
    """A guaranteed-valid title, used if a generated title fails validation."""
    if facts and facts.education_polarity == "admitted":
        if ja:
            inst = facts.primary_institution() or topic.title
            candidate = f"{inst}という分岐点"
            return candidate if _is_valid_japanese_title(candidate) else _JA_SAFE_NEUTRAL_TITLE
        inst = facts.primary_institution() or topic.title
        candidate = f"After Getting Into {inst}" if not age else f"Entering {inst} at {age}"
        return candidate if _is_valid_english_title(candidate) else _EN_SAFE_NEUTRAL_TITLE
    if ja:
        candidate = f"{topic.title}という分岐点" if topic.title else _JA_SAFE_FALLBACK_TITLE
        return candidate if _is_valid_japanese_title(candidate) else _JA_SAFE_FALLBACK_TITLE
    candidate = f"The {topic.title} Not Chosen at {age}" if age else f"The {topic.title} Not Chosen"
    return candidate if _is_valid_english_title(candidate) else _EN_SAFE_FALLBACK_TITLE


def _title_keyword(topic: _Topic, facts: ParallelLifeFacts | None, ja: bool) -> str:
    """Prefer an explicit institution name over a generic topic noun."""
    if facts:
        inst = facts.primary_institution()
        if inst:
            return inst
    return topic.title


def _title_and_subtitle(
    topic: _Topic,
    age: str | None,
    ja: bool,
    seed: int,
    facts: ParallelLifeFacts | None = None,
    grounded: "object | None" = None,
) -> tuple[str, str]:
    from app.parallel_life_domain import GroundedPrimaryBranch, family_formation_title

    kw = _title_keyword(topic, facts, ja)
    facts = facts or ParallelLifeFacts()
    subtitle_override: str | None = None

    if (
        grounded is not None
        and isinstance(grounded, GroundedPrimaryBranch)
        and grounded.primary_domain == "family-formation"
    ) or topic.category == "family_formation":
        g = grounded if isinstance(grounded, GroundedPrimaryBranch) else None
        if g is not None:
            title, subtitle_override = family_formation_title(g, ja=ja, seed=seed)
        elif ja:
            title = "子どもを授かった、その先"
            subtitle_override = "叶った願いのそばに、まだ開いている分岐がある。"
        else:
            title = "After Receiving a Child"
            subtitle_override = "Beside a wish fulfilled, another branch remains open."
    elif facts.education_polarity == "admitted":
        if age:
            pool = _JA_TITLE_ADMITTED_WITH_AGE if ja else _EN_TITLE_ADMITTED_WITH_AGE
            title = pool[seed % len(pool)].format(kw=kw, age=age)
        else:
            pool = _JA_TITLE_ADMITTED_NO_AGE if ja else _EN_TITLE_ADMITTED_NO_AGE
            title = pool[seed % len(pool)].format(kw=kw)
    elif facts.place_polarity == "stayed":
        pool = _JA_TITLE_STAYED_NO_AGE if ja else _EN_TITLE_STAYED_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)
        if age and ja:
            title = f"{age}、{title}"
    elif facts.place_polarity == "left":
        pool = _JA_TITLE_LEFT_NO_AGE if ja else _EN_TITLE_LEFT_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)
    elif facts.work_polarity == "resigned":
        pool = _JA_TITLE_RESIGNED_NO_AGE if ja else _EN_TITLE_RESIGNED_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)
    elif facts.work_polarity == "stayed":
        pool = _JA_TITLE_WORK_STAYED_NO_AGE if ja else _EN_TITLE_WORK_STAYED_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)
    elif facts.marriage_polarity == "married":
        pool = _JA_TITLE_MARRIED_NO_AGE if ja else _EN_TITLE_MARRIED_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)
    elif facts.marriage_polarity == "not_married":
        pool = _JA_TITLE_NOT_MARRIED_NO_AGE if ja else _EN_TITLE_NOT_MARRIED_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)
    elif topic.category == "education" and not facts.polarity_known:
        title = _JA_SAFE_NEUTRAL_TITLE if ja else _EN_SAFE_NEUTRAL_TITLE
    elif age:
        pool = _JA_TITLE_WITH_AGE if ja else _EN_TITLE_WITH_AGE
        title = pool[seed % len(pool)].format(kw=kw, age=age)
    else:
        pool = _JA_TITLE_NO_AGE if ja else _EN_TITLE_NO_AGE
        title = pool[seed % len(pool)].format(kw=kw)

    is_valid = _is_valid_japanese_title(title) if ja else _is_valid_english_title(title)
    if not is_valid:
        title = _safe_fallback_title(topic, age, ja, facts)

    if subtitle_override:
        subtitle = subtitle_override
    else:
        sub_pool = _JA_SUBTITLE_POOL if ja else _EN_SUBTITLE_POOL
        subtitle = sub_pool[(seed // 3) % len(sub_pool)]
    return title, subtitle


# --- Branch point / chosen path / unchosen life -------------------------------
#
# None of these describe the source text as text ("The branch appears inside
# ...", "という入力の中には..."). They read the situation directly, as a finished
# editorial document would, and ground each section in the branch's topic and
# any provided clarifications rather than repeating the same sentence shape
# for every result (editorial-quality pass, §2, §4, §5, §6).


def _branch_point(
    topic: _Topic,
    age: str | None,
    clar: ParallelLifeClarifications,
    ja: bool,
    facts: ParallelLifeFacts | None = None,
) -> str:
    facts = facts or ParallelLifeFacts()
    inst = facts.primary_institution()

    if facts.education_polarity == "admitted":
        subject = inst or (topic.prose if topic.category == "education" else topic.prose)
        if ja:
            base = (
                f"{subject}への合格は、一つの結果であると同時に、その後の生活を開く分岐でもあった。"
                "進学先での学び、出会う人、暮らす場所、そして仕事への道筋が、同時に重なり始めていた。"
            )
            if age:
                base += f" それは{age}のころのことだった。"
            if clar.constraints:
                base += f" 当時それを形づくっていた条件には、{_clean_line(clar.constraints)}もあった。"
            base += " 合格という事実そのものは確定しているが、その先で何が開かれていくかは、当時すべて見えていたわけではない。"
            return base
        base = (
            f"Admission to {subject} was both an outcome and a branch that opened the life that followed — "
            "study, the people met there, a place to live, and the path into work began to overlap at once."
        )
        if age:
            base += f" It happened around age {age}."
        if clar.constraints:
            base += f" Among the conditions shaping it was {_clean_line(clar.constraints)}."
        base += " The fact of admission is settled; what would open after it was not fully visible then."
        return base

    if facts.education_polarity == "rejected":
        subject = inst or topic.prose
        if ja:
            base = (
                f"{subject}に届かなかったことは、一つの結果であると同時に、その後の進路を静かに変えていく分岐でもあった。"
                "進学先、暮らす場所、仕事、人との関係が、同時に別の形へ向かい始めていた。"
            )
            if age:
                base += f" それは{age}のころのことだった。"
            if clar.constraints:
                base += f" 当時それを制限していたのは、{_clean_line(clar.constraints)}だった。"
            base += " すべてが分かっていたわけではなく、当時の本人にも、どこまで見えていたかは定かではない。"
            return base
        base = (
            f"Not reaching {subject} was both an outcome and a branch that quietly redirected what followed — "
            "school, place, work, and relationships began to take another shape."
        )
        if age:
            base += f" It happened around age {age}."
        if clar.constraints:
            base += f" What limited it at the time was {_clean_line(clar.constraints)}."
        base += " Not everything here is certain, and it is not clear how much was visible then."
        return base

    if topic.category == "education" and not facts.polarity_known:
        if ja:
            base = "その時、進学をめぐる大きな分岐があった。人との関係、暮らす場所、仕事、そして自分の生活をどう築くかが、同時に重なる場所でもあった。"
            if age:
                base += f" それは{age}のころのことだった。"
            base += " 方向を断定できる材料はまだ揃っていない。"
            return base
        base = (
            "At that time there was a major branch around education — "
            "where relationships, place, work, and building a life all met at once."
        )
        if age:
            base += f" It happened around age {age}."
        base += " There is not yet enough to assert a single direction."
        return base

    if ja:
        base = (
            f"{topic.prose}をめぐる分岐は、一つの単純な選択には収まらない。"
            "人との関係、暮らす場所、仕事、そして自分の生活をどう築くかが、同時に重なる場所で生まれた。"
        )
        if age:
            base += f" それは{age}のころのことだった。"
        if clar.constraints:
            base += f" 当時それを制限していたのは、{_clean_line(clar.constraints)}だった。"
        base += " すべてが分かっていたわけではなく、当時の本人にも、どこまで見えていたかは定かではない。"
        return base
    base = (
        f"The branch around {topic.prose} did not come down to a single, simple choice — "
        "it took shape where a relationship, a place to live, work, and the need to build "
        "an independent life all met at once."
    )
    if age:
        base += f" It happened around age {age}."
    if clar.constraints:
        base += f" What limited it at the time was {_clean_line(clar.constraints)}."
    base += " Not everything here is certain, and it is not clear how much was visible to the person living it at the time."
    return base


_JA_CHOSEN_OPENERS = [
    "実際に選んだ人生は、{topic}を手放した結果ではない。当時の条件のなかで、まず生活を成り立たせようとした道だった。",
    "選んだのは、{topic}をあきらめることではなく、そのとき目の前にあった生活を引き受けることだった。",
    "{topic}を退けたというより、そのとき現実的に築ける生活を選び取ったというほうが近い。",
]
_EN_CHOSEN_OPENERS = [
    "The life that followed was not a rejection of {topic}. Within the conditions of that time, "
    "it was an attempt to make a livable life first.",
    "What was chosen was not giving up on {topic}, but taking on the life that was actually in "
    "front of them at the time.",
    "It reads less as turning away from {topic} than as choosing the life that was realistically "
    "buildable then.",
]
_JA_CHOSEN_ADMITTED = [
    "実際に選んだのは、{subject}へ進むことそのものだった。合格という結果を引き受け、その先の生活を始めようとした道である。",
    "進んだのは{subject}だった。そこでの学びや人間関係が、その後の生活の出発点になっていった。",
]
_EN_CHOSEN_ADMITTED = [
    "What was chosen was entering {subject} itself — accepting the admission and beginning the life that followed from it.",
    "The path taken was {subject}. Study and relationships there became a starting point for the life that followed.",
]
_JA_CHOSEN_ENABLING = [
    "その道は、仕事を続けること、収入の見通し、家族との近さ、あるいは自分の生活を自分の手で保つ感覚を、同時に支えていた可能性がある。",
    "そこには、生活の基盤を整えること、まわりとの関係を保つこと、そして自分のペースで先を決められることが、同時に含まれていたかもしれない。",
]
_EN_CHOSEN_ENABLING = [
    "That path may have supported continuing the work already begun, a clearer sense of income, "
    "and closeness to family, all at the same time.",
    "It may have carried a stable footing, nearby relationships, and room to decide the next "
    "step at one's own pace, all at once.",
]


def _chosen_path(
    topic: _Topic,
    clar: ParallelLifeClarifications,
    ja: bool,
    seed: int,
    facts: ParallelLifeFacts | None = None,
) -> str:
    facts = facts or ParallelLifeFacts()
    stated = _clean_line(clar.chosen_path) if clar.chosen_path else ""
    inst = facts.primary_institution()

    if facts.education_polarity == "admitted":
        subject = stated or inst or topic.prose
        if ja:
            base = _JA_CHOSEN_ADMITTED[seed % len(_JA_CHOSEN_ADMITTED)].format(subject=subject)
            base += " それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            base += " 学びの場、そこで出会う人、そしてその後の進路が、同時に開かれていったかもしれない。"
            return base
        base = _EN_CHOSEN_ADMITTED[seed % len(_EN_CHOSEN_ADMITTED)].format(subject=subject)
        base += (
            " It does not need to be read as failure or compromise; it can be read as a life "
            "that began from a real decision."
        )
        base += " Study, people met there, and the path afterward may all have opened at once."
        return base

    if facts.work_polarity == "stayed":
        if ja:
            return (
                "実際に選んだのは、その仕事に残ることだった。"
                "辞める道ではなく、いまの役割のなかで生活を続けようとした道である。"
                "それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            )
        return (
            "What was chosen was staying with that work — not leaving, but continuing inside the role. "
            "It does not need to be read as failure or compromise; it can be read as a life that began from a real decision."
        )

    if facts.work_polarity == "resigned":
        if ja:
            return (
                "実際に選んだのは、その仕事を離れることだった。"
                "残る道ではなく、役割を手放して次の生活へ進もうとした道である。"
                "それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            )
        return (
            "What was chosen was leaving that work — not staying, but setting the role aside and moving on. "
            "It does not need to be read as failure or compromise; it can be read as a life that began from a real decision."
        )

    if facts.place_polarity == "stayed":
        if ja:
            return (
                f"実際に選んだのは、{topic.prose}に残ることだった。"
                "離れる道ではなく、いまの場所で生活を続けようとした道である。"
                "それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            )
        return (
            f"What was chosen was staying in {topic.prose} — not leaving, but continuing a life there. "
            "It does not need to be read as failure or compromise; it can be read as a life that began from a real decision."
        )

    if facts.place_polarity == "left":
        if ja:
            return (
                f"実際に選んだのは、{topic.prose}を離れることだった。"
                "残る道ではなく、別の場所で生活を始めようとした道である。"
                "それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            )
        return (
            f"What was chosen was leaving {topic.prose} — not staying, but beginning a life elsewhere. "
            "It does not need to be read as failure or compromise; it can be read as a life that began from a real decision."
        )

    if facts.marriage_polarity == "married":
        if ja:
            return (
                "実際に選んだのは、結婚することだった。"
                "それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            )
        return (
            "What was chosen was marrying. "
            "It does not need to be read as failure or compromise; it can be read as a life that began from a real decision."
        )

    if facts.marriage_polarity == "not_married":
        if ja:
            return (
                "実際に選んだのは、結婚しない道だった。"
                "それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
            )
        return (
            "What was chosen was not marrying. "
            "It does not need to be read as failure or compromise; it can be read as a life that began from a real decision."
        )

    if topic.category == "education" and not facts.polarity_known:
        if ja:
            return (
                "その時、進学をめぐる大きな分岐があった。"
                "実際にどの方向へ進んだのかを、ここで断定することはできない。"
                "わかっているのは、進学が生活の条件を静かに変えていく地点だったということだけだ。"
            )
        return (
            "At that time there was a major branch around education. "
            "The exact direction taken cannot be asserted from what is given. "
            "What is clear is that education was a point where the conditions of life quietly changed."
        )

    if ja:
        base = _JA_CHOSEN_OPENERS[seed % len(_JA_CHOSEN_OPENERS)].format(topic=topic.prose)
        if stated:
            base += f" 実際に進んだ先は、{stated}だった。"
        base += " それは失敗や妥協として読む必要はなく、実際の決断から始まった生活として見ることができる。"
        base += " " + _JA_CHOSEN_ENABLING[seed % len(_JA_CHOSEN_ENABLING)]
        return base
    base = _EN_CHOSEN_OPENERS[seed % len(_EN_CHOSEN_OPENERS)].format(topic=topic.prose)
    if stated:
        base += f" What followed was {stated}."
    base += (
        " It does not need to be read as failure or compromise; it can be read as a life "
        "that began from a real decision."
    )
    base += " " + _EN_CHOSEN_ENABLING[seed % len(_EN_CHOSEN_ENABLING)]
    return base


_JA_UNCHOSEN_HEDGES = [
    "ただ、その道が長く続いたのか、途中で別の形に変わっていたのかは分からない。",
    "ただ、それが今より満たされた日々だったとは言い切れない。",
    "ただ、別の場所でも、別の種類の難しさに出会っていた可能性がある。",
]
_EN_UNCHOSEN_HEDGES = [
    " But it is not clear whether that path would have lasted, or changed into something else along the way.",
    " But it cannot be said that those days would have been more fulfilling than these.",
    " But a different place may simply have carried a different kind of difficulty.",
]


def _unchosen_life(
    topic: _Topic,
    clar: ParallelLifeClarifications,
    ja: bool,
    seed: int,
    facts: ParallelLifeFacts | None = None,
) -> str:
    facts = facts or ParallelLifeFacts()
    stated = _clean_line(clar.unchosen_path) if clar.unchosen_path else ""

    def _unchosen_sentence(subject: str) -> str:
        if ja:
            base = f"{subject}を選んでいたら、暮らしは今とは違う形になっていたかもしれない。"
            base += _JA_UNCHOSEN_HEDGES[seed % len(_JA_UNCHOSEN_HEDGES)]
            base += " あり得た人生のひとつではあるが、実現しなかった完成品として扱うことはできない。"
            return base
        base = f"Had {subject} been chosen, daily life may have taken a different shape."
        base += _EN_UNCHOSEN_HEDGES[seed % len(_EN_UNCHOSEN_HEDGES)]
        base += " It remains one possible life, not an unlived finished product."
        return base

    if facts.education_polarity == "admitted":
        # The chosen school was entered — do not narrate it as the unchosen life.
        subject = stated or (
            "進学しなかった側の道" if ja else "a path that did not follow that admission"
        )
        return _unchosen_sentence(subject)

    if facts.education_polarity == "rejected":
        subject = stated or facts.primary_institution() or topic.prose
        if ja:
            base = f"{subject}へ進んでいたら、暮らしは今とは違う形になっていたかもしれない。"
            base += _JA_UNCHOSEN_HEDGES[seed % len(_JA_UNCHOSEN_HEDGES)]
            base += " あり得た人生のひとつではあるが、実現しなかった完成品として扱うことはできない。"
            return base
        base = f"Had {subject} been entered, daily life may have taken a different shape."
        base += _EN_UNCHOSEN_HEDGES[seed % len(_EN_UNCHOSEN_HEDGES)]
        base += " It remains one possible life, not an unlived finished product."
        return base

    if facts.work_polarity == "stayed":
        subject = stated or ("仕事を離れる道" if ja else "leaving that work")
        return _unchosen_sentence(subject)
    if facts.work_polarity == "resigned":
        subject = stated or ("仕事に残る道" if ja else "staying in that work")
        return _unchosen_sentence(subject)
    if facts.place_polarity == "stayed":
        subject = stated or (f"{topic.prose}を離れる道" if ja else f"leaving {topic.prose}")
        return _unchosen_sentence(subject)
    if facts.place_polarity == "left":
        subject = stated or (f"{topic.prose}に残る道" if ja else f"staying in {topic.prose}")
        return _unchosen_sentence(subject)
    if facts.marriage_polarity == "married":
        subject = stated or ("結婚しない道" if ja else "not marrying")
        return _unchosen_sentence(subject)
    if facts.marriage_polarity == "not_married":
        subject = stated or ("結婚する道" if ja else "marrying")
        return _unchosen_sentence(subject)

    if topic.category == "education" and not facts.polarity_known:
        if ja:
            return (
                "進学をめぐるもう一方の道が、どのような形だったのかは、ここでは断定できない。"
                "あり得た人生のひとつではあるが、実現しなかった完成品として扱うことはできない。"
            )
        return (
            "What the other educational path would have looked like cannot be asserted from what is given. "
            "It remains one possible life, not an unlived finished product."
        )

    subject = stated or topic.prose
    if ja:
        base = f"{subject}を選んでいたら、暮らしは今とは違う形になっていたかもしれない。"
        base += _JA_UNCHOSEN_HEDGES[seed % len(_JA_UNCHOSEN_HEDGES)]
        base += " あり得た人生のひとつではあるが、実現しなかった完成品として扱うことはできない。"
        return base
    base = f"Had {subject} been chosen, daily life may have taken a different shape."
    base += _EN_UNCHOSEN_HEDGES[seed % len(_EN_UNCHOSEN_HEDGES)]
    base += " It remains one possible life, not an unlived finished product."
    return base


# --- Lost / Protected ---------------------------------------------------------
#
# Each item carries a ``concept`` tag alongside its text. The pool is
# constructed so every concept appears exactly once — this is the primary
# deduplication mechanism (editorial-quality pass, "reduce Lost/Protected
# duplication"). ``_dedupe_semantically`` below is a second, runtime safety
# net that also catches overlap introduced by a user-provided clarification
# answer (``clar.lost`` / ``clar.protected``), which is free-form text.
# Counts are asymmetric by design: Lost and Protected are picked with
# different seeds and (within a depth) a variable target count, so they are
# never forced into a mechanically mirrored 1:1 shape.


@dataclass(frozen=True)
class _Item:
    concept: str
    text: str


# Category-specific pools so Lost / Protected stay branch-grounded
# (education must not inherit "starting a life in {topic}" from a place
# template; creativity must not inherit "belonging to that place").
_LOST_POOLS_JA: dict[str, tuple[_Item, ...]] = {
    "place": (
        _Item("opportunity_window", "その時期にしか開かれていなかった{topic}への入口"),
        _Item("shared_life_time", "誰かと別の土地で生活を始めていたかもしれない時間"),
        _Item("mobility", "身軽に移動し続ける自分"),
        _Item("different_rhythm", "いまの場所とは異なる時間の流れ"),
        _Item("alt_self", "その土地で育っていたかもしれない自分"),
        _Item("belonging_place", "その場所に属しているという感覚"),
        _Item("future_outline", "そのまま居続けていたら見えていたはずの暮らしの輪郭"),
        _Item("continuing_bet", "{topic}に居続けるという道そのもの"),
    ),
    "education": (
        _Item("opportunity_window", "その時期にしか開かれていなかった進学の入口"),
        _Item("peer_circle", "そこで出会っていたかもしれない友人や先輩"),
        _Item("subject_depth", "そこで深く学べていたかもしれない科目や分野"),
        _Item("campus_rhythm", "キャンパスの時間の流れのなかで過ごしていた日々"),
        _Item("alt_self", "その進学先で育っていたかもしれない自分"),
        _Item("future_outline", "その先に続いていたかもしれない進路の輪郭"),
        _Item("continuing_bet", "第一志望に賭け続けるという道そのもの"),
    ),
    # Used when education_polarity == "admitted" — never implies rejection.
    "education_admitted": (
        _Item("pre_exam_self", "受験期特有の緊張のなかにいた自分"),
        _Item("other_path", "進学しなかった側に残っていたかもしれない生活"),
        _Item("uncommitted_time", "進路がまだ開かれていたころの身軽さ"),
        _Item("alt_city_life", "別の街で学生生活を始めていたかもしれない時間"),
        _Item("gap_year_self", "進学を一度置いていたら見えていたかもしれない別の輪郭"),
        _Item("narrower_before", "合格前に持っていた、より広い進路の想像"),
    ),
    "work": (
        _Item("opportunity_window", "その時期にしか開かれていなかった仕事への入口"),
        _Item("skill_path", "そこで積み上がっていたかもしれない専門性"),
        _Item("role_identity", "その役割のなかで形づくられていたかもしれない自分"),
        _Item("colleague_circle", "そこで出会っていたかもしれない同僚や師"),
        _Item("future_outline", "そのまま続けていたら見えていたはずの仕事の輪郭"),
        _Item("different_rhythm", "いまとは違う働き方のリズム"),
        _Item("continuing_bet", "その仕事に賭け続けるという道そのもの"),
    ),
    "relationship": (
        _Item("shared_life_time", "共に生活を始めていたかもしれない時間"),
        _Item("intimacy_form", "その関係がつくっていた親密さの形"),
        _Item("alt_self", "その関係のなかで育っていたかもしれない自分"),
        _Item("shared_future", "二人で見ていたかもしれない未来の輪郭"),
        _Item("daily_presence", "日常のなかに誰かがいたかもしれない感触"),
        _Item("opportunity_window", "その時期にしか開かれていなかった関係の入口"),
    ),
    "creativity": (
        _Item("practice_continuity", "途切れずに続けていたかもしれない創作の時間"),
        _Item("body_of_work", "積み上がっていたかもしれない小さな作品の群"),
        _Item("alt_self", "創り続ける側に立っていたかもしれない自分"),
        _Item("audience_thread", "誰かに届いていたかもしれない作品の行方"),
        _Item("different_rhythm", "創作を中心に回っていた日々のリズム"),
        _Item("opportunity_window", "その時期にしか開けていなかった表現の入口"),
    ),
    "care": (
        _Item("personal_time", "自分だけに使えていたかもしれない時間"),
        _Item("unbound_self", "役割から離れていたときの自分"),
        _Item("mobility", "身軽に動き続けられる日々"),
        _Item("alt_self", "その役割を選ばなかった側の自分"),
        _Item("future_outline", "自分の計画だけで形づくられていたかもしれない生活の輪郭"),
        _Item("opportunity_window", "その時期にしか開かれていなかった別の道への入口"),
    ),
    "default": (
        _Item("opportunity_window", "その時期にしか開かれていなかった{topic}への入口"),
        _Item("alt_self", "その道を選んでいたら、なっていたかもしれない自分"),
        _Item("different_rhythm", "いまとは違う時間の流れ"),
        _Item("future_outline", "そのまま続けていたら見えていたはずの暮らしの輪郭"),
        _Item("shared_life_time", "誰かとその道で過ごしていたかもしれない時間"),
        _Item("continuing_bet", "{topic}に賭け続けるという道そのもの"),
    ),
}
_PROTECTED_POOLS_JA: dict[str, tuple[_Item, ...]] = {
    "place": (
        _Item("settle_base_here", "いまの場所で仕事と住まいを整える余地"),
        _Item("relationship_continuity", "家族や既存の人間関係との連続性"),
        _Item("no_rush", "次の選択を急がずに済む時間"),
        _Item("independent_base", "移動だけに依存しない暮らしの土台"),
        _Item("work_continuity", "積み重ねてきた仕事とのつながり"),
        _Item("risk_distance", "大きな移動がもたらす不確かさからの距離"),
        _Item("language_home", "言葉や習慣をそのまま使える日常"),
        _Item("self_reliance", "自分の力で日々を成り立たせている実感"),
    ),
    "education": (
        _Item("actual_learning", "進んだ先で実際に得た学びや経験"),
        _Item("peer_found", "そこで出会えた人とのつながり"),
        _Item("work_entry", "その後の仕事や進路につながった接点"),
        _Item("no_rush", "次の選択を急がずに済む時間"),
        _Item("self_reliance", "いまの場所で自分の道を立て直してきた実感"),
        _Item("risk_distance", "未確定の進学先に賭け続ける不確かさからの距離"),
        _Item("relationship_continuity", "家族や既存の人間関係との連続性"),
    ),
    "education_admitted": (
        _Item("admission_itself", "第一志望への合格という事実"),
        _Item("actual_learning", "その進学先で実際に得た学びや経験"),
        _Item("peer_found", "そこで出会えた人とのつながり"),
        _Item("work_entry", "その後の仕事や進路につながった接点"),
        _Item("no_rush", "次の選択を急がずに済む時間"),
        _Item("relationship_continuity", "家族や既存の人間関係との連続性"),
        _Item("chosen_campus", "選んだ学びの場に身を置けること"),
    ),
    "work": (
        _Item("income_base", "生活を支える収入の見通し"),
        _Item("skill_kept", "いまの役割のなかで積み上がっている技能"),
        _Item("colleague_present", "いま一緒に働いている人との関係"),
        _Item("no_rush", "次の選択を急がずに済む時間"),
        _Item("risk_distance", "大きな転職がもたらす不確かさからの距離"),
        _Item("self_reliance", "自分の力で日々を成り立たせている実感"),
        _Item("relationship_continuity", "仕事以外の人間関係との連続性"),
    ),
    "relationship": (
        _Item("self_space", "自分一人の生活を保つ余地"),
        _Item("no_rush", "次の関係を急がずに済む時間"),
        _Item("independent_base", "関係だけに依存しない生活の土台"),
        _Item("friend_circle", "友人や家族との既存のつながり"),
        _Item("self_reliance", "自分の日々を自分で整えられる実感"),
        _Item("risk_distance", "関係の不確かさがもたらす揺らぎからの距離"),
    ),
    "creativity": (
        _Item("income_base", "創作以外で生活を支える基盤"),
        _Item("no_rush", "創作を再開するかどうかを急がずに済む時間"),
        _Item("skill_kept", "仕事のなかで残っている表現や観察の力"),
        _Item("risk_distance", "生活を創作だけに賭ける不確かさからの距離"),
        _Item("relationship_continuity", "家族や既存の人間関係との連続性"),
        _Item("self_reliance", "いまの生活を自分で成り立たせている実感"),
    ),
    "care": (
        _Item("bond_kept", "その選択によって保たれた関係や絆"),
        _Item("lived_meaning", "担ってきたことのなかで得た意味"),
        _Item("no_rush", "自分の次の一歩を急がずに済む時間"),
        _Item("self_space_small", "短い時間でも自分のために使える隙間"),
        _Item("relationship_continuity", "家族や身近な人との連続性"),
        _Item("risk_distance", "すべてを手放す決断を迫られないこと"),
    ),
    "default": (
        _Item("settle_base_here", "いまの場所で仕事と住まいを整える余地"),
        _Item("relationship_continuity", "家族や既存の人間関係との連続性"),
        _Item("no_rush", "次の選択を急がずに済む時間"),
        _Item("independent_base", "{topic}に依存しない暮らしの土台"),
        _Item("work_continuity", "積み重ねてきた仕事とのつながり"),
        _Item("risk_distance", "大きな変化がもたらすリスクからの距離"),
        _Item("self_reliance", "自分の力で日々を成り立たせている実感"),
    ),
}
_LOST_POOLS_EN: dict[str, tuple[_Item, ...]] = {
    "place": (
        _Item("opportunity_window", "the entry into {topic} that was only open then"),
        _Item("shared_life_time", "time that might have gone into starting a life with someone elsewhere"),
        _Item("mobility", "a self that kept moving lightly from place to place"),
        _Item("different_rhythm", "a rhythm of time different from the one lived here"),
        _Item("alt_self", "a version of self that might have formed in that place"),
        _Item("belonging_place", "a sense of belonging to that place"),
        _Item("future_outline", "the outline of a life that staying there might have revealed"),
        _Item("continuing_bet", "the path of remaining in {topic} at all"),
    ),
    "education": (
        _Item("opportunity_window", "the entrance to that school or course that was only open then"),
        _Item("peer_circle", "friends and seniors who might have been met there"),
        _Item("subject_depth", "a subject or field that might have been studied more deeply there"),
        _Item("campus_rhythm", "days lived inside that campus rhythm"),
        _Item("alt_self", "a version of self that might have formed on that campus"),
        _Item("future_outline", "the outline of a career path that might have followed from there"),
        _Item("continuing_bet", "the path of continuing to bet on the first-choice school"),
    ),
    "education_admitted": (
        _Item("pre_exam_self", "the self that lived inside the tension of the exam years"),
        _Item("other_path", "a life that might have remained on the side that did not enter"),
        _Item("uncommitted_time", "the lightness of a time when the path was still open"),
        _Item("alt_city_life", "time that might have gone into student life in another city"),
        _Item("gap_year_self", "an outline that might have appeared if enrollment had been set aside"),
        _Item("narrower_before", "a wider imagination of paths held before admission"),
    ),
    "work": (
        _Item("opportunity_window", "the entry into that work that was only open then"),
        _Item("skill_path", "expertise that might have accumulated along that path"),
        _Item("role_identity", "a self that might have formed inside that role"),
        _Item("colleague_circle", "colleagues or mentors who might have been met there"),
        _Item("future_outline", "the outline of a career that continuing might have revealed"),
        _Item("different_rhythm", "a different rhythm of working than the one lived now"),
        _Item("continuing_bet", "the path of continuing to bet on that work"),
    ),
    "relationship": (
        _Item("shared_life_time", "time that might have gone into a shared life"),
        _Item("intimacy_form", "the form of closeness that relationship was building"),
        _Item("alt_self", "a version of self that might have formed inside that bond"),
        _Item("shared_future", "the outline of a future imagined together"),
        _Item("daily_presence", "the felt presence of someone in ordinary days"),
        _Item("opportunity_window", "the entrance to that relationship that was only open then"),
    ),
    "creativity": (
        _Item("practice_continuity", "unbroken hours that might have gone into the practice"),
        _Item("body_of_work", "a small body of work that might have accumulated"),
        _Item("alt_self", "a self that might have stayed on the making side"),
        _Item("audience_thread", "the chance that a piece of work might have reached someone"),
        _Item("different_rhythm", "days organized around making rather than around a job"),
        _Item("opportunity_window", "the entrance into that practice that was only open then"),
    ),
    "care": (
        _Item("personal_time", "hours that might have belonged only to oneself"),
        _Item("unbound_self", "a self less defined by that role"),
        _Item("mobility", "days that could keep moving lightly"),
        _Item("alt_self", "a version of self on the side that did not take that role"),
        _Item("future_outline", "a life shaped mostly by one's own plans"),
        _Item("opportunity_window", "another path that was only open then"),
    ),
    "default": (
        _Item("opportunity_window", "the entry into {topic} that was only open then"),
        _Item("alt_self", "a version of self that might have formed on that path"),
        _Item("different_rhythm", "a different rhythm of time than the one lived now"),
        _Item("future_outline", "the outline of a life that continuing might have revealed"),
        _Item("shared_life_time", "time that might have been spent with someone on that path"),
        _Item("continuing_bet", "the path of continuing to bet on {topic}"),
    ),
}
_PROTECTED_POOLS_EN: dict[str, tuple[_Item, ...]] = {
    "place": (
        _Item("settle_base_here", "room to settle work and a home in the current place"),
        _Item("relationship_continuity", "continuity with family and existing relationships"),
        _Item("no_rush", "time to make the next decision without rushing"),
        _Item("independent_base", "a foundation for daily life that does not depend on moving"),
        _Item("work_continuity", "continuity with work already built up"),
        _Item("risk_distance", "distance from the uncertainty a large move would have carried"),
        _Item("language_home", "ordinary days that can still use familiar language and habits"),
        _Item("self_reliance", "the felt sense of holding one's own days together"),
    ),
    "education": (
        _Item("actual_learning", "learning and experience actually gained on the path taken"),
        _Item("peer_found", "connections with people met along the way"),
        _Item("work_entry", "contacts that later opened into work or a next step"),
        _Item("no_rush", "time to make the next decision without rushing"),
        _Item("self_reliance", "the sense of rebuilding a path in the place actually reached"),
        _Item("risk_distance", "distance from the uncertainty of continuing to bet on the first choice"),
        _Item("relationship_continuity", "continuity with family and existing relationships"),
    ),
    "education_admitted": (
        _Item("admission_itself", "the fact of admission to the first-choice school"),
        _Item("actual_learning", "learning and experience actually gained there"),
        _Item("peer_found", "connections with people met there"),
        _Item("work_entry", "contacts that later opened into work or a next step"),
        _Item("no_rush", "time to make the next decision without rushing"),
        _Item("relationship_continuity", "continuity with family and existing relationships"),
        _Item("chosen_campus", "being able to place oneself in the chosen place of study"),
    ),
    "work": (
        _Item("income_base", "a foreseeable income that holds daily life together"),
        _Item("skill_kept", "skills still accumulating inside the current role"),
        _Item("colleague_present", "relationships with people worked with now"),
        _Item("no_rush", "time to make the next decision without rushing"),
        _Item("risk_distance", "distance from the uncertainty a large career change would carry"),
        _Item("self_reliance", "the felt sense of holding one's own days together"),
        _Item("relationship_continuity", "continuity with relationships outside work"),
    ),
    "relationship": (
        _Item("self_space", "room to keep a life that is one's own"),
        _Item("no_rush", "time before the next relationship, without rushing"),
        _Item("independent_base", "a foundation for daily life that does not rest only on a bond"),
        _Item("friend_circle", "existing ties with friends and family"),
        _Item("self_reliance", "the felt sense of arranging one's own days"),
        _Item("risk_distance", "distance from the instability a fragile relationship can bring"),
    ),
    "creativity": (
        _Item("income_base", "a living not dependent on the creative work alone"),
        _Item("no_rush", "time to decide whether to resume, without rushing"),
        _Item("skill_kept", "powers of observation or expression still used inside the job"),
        _Item("risk_distance", "distance from staking a whole life on the practice alone"),
        _Item("relationship_continuity", "continuity with family and existing relationships"),
        _Item("self_reliance", "the felt sense of holding the current life together"),
    ),
    "care": (
        _Item("bond_kept", "bonds and relationships the choice helped keep intact"),
        _Item("lived_meaning", "meaning found inside what was carried"),
        _Item("no_rush", "time before the next personal step, without rushing"),
        _Item("self_space_small", "even a short interval that can still belong to oneself"),
        _Item("relationship_continuity", "continuity with family and people nearby"),
        _Item("risk_distance", "not being forced into a decision to let everything go"),
    ),
    "default": (
        _Item("settle_base_here", "room to settle work and a home in the current place"),
        _Item("relationship_continuity", "continuity with family and existing relationships"),
        _Item("no_rush", "time to make the next decision without rushing"),
        _Item("independent_base", "a foundation for daily life that does not depend on {topic}"),
        _Item("work_continuity", "continuity with work already built up"),
        _Item("risk_distance", "distance from the risk a large change would have carried"),
        _Item("self_reliance", "the felt sense of holding one's own days together"),
    ),
}

# Backward-compatible aliases used by a few unit tests that still import the
# flat pool names; they point at the default category.
_LOST_JA = _LOST_POOLS_JA["default"]
_PROTECTED_JA = _PROTECTED_POOLS_JA["default"]
_LOST_EN = _LOST_POOLS_EN["default"]
_PROTECTED_EN = _PROTECTED_POOLS_EN["default"]

# Concept clusters used to catch overlap that the fixed-pool design cannot —
# in particular, a free-form clarification answer (``clar.lost`` /
# ``clar.protected``) that happens to restate a concept already covered by a
# pool item (e.g. "選択肢を残す" / "将来の可能性を残す" / "次の道を選べる余地" all
# express the same idea, editorial-quality pass example).
_JA_CONCEPT_CLUSTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("keep_options", ("選択肢を残", "可能性を残", "道を選べる余地", "選び続けられる", "次の道を選べ")),
    (
        "life_base",
        (
            "生活基盤",
            "生活の基盤",
            "生活を成立",
            "安定した暮らし",
            "生活の土台",
            "暮らしの土台",
            "日々を成り立たせ",
        ),
    ),
    ("overseas_possibility", ("海外へ進む可能", "海外で暮らす可能", "海外に居続ける", "別の土地で生きる")),
    ("alt_future", ("選ばなかった可能", "別の生活へ進んでいた時間", "見えていたはずの未来")),
)
_EN_CONCEPT_CLUSTERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "keep_options",
        ("keep future options", "keep choosing", "ability to choose", "room to choose", "keep options open"),
    ),
    (
        "life_base",
        (
            "foundation for daily life",
            "stable footing",
            "hold one's own life",
            "hold one's own days",
            "holding the current life together",
        ),
    ),
    (
        "overseas_possibility",
        ("chance to go abroad", "living abroad", "staying overseas", "life in another country"),
    ),
)

# Soft concentration audit: these key nouns may appear, but should not dominate
# a single Lost or Protected list (editorial-quality pass round 2).
_JA_KEY_NOUNS = ("選択", "可能性", "生活", "感覚", "自分", "未来", "基盤")
_EN_KEY_NOUNS = ("possibility", "choice", "future", "life", "stability", "sense", "path")


def _concept_signature(text: str, clusters: tuple[tuple[str, tuple[str, ...]], ...]) -> frozenset[str]:
    lowered = text.lower()
    hits = {name for name, keywords in clusters if any(kw.lower() in lowered for kw in keywords)}
    return frozenset(hits)


def _dedupe_semantically(items: list[str], ja: bool) -> list[str]:
    """Drop items that express a concept already covered by an earlier item.

    Keeps the earlier (usually more concrete, user-provided-first) item and
    silently removes a later one whose concept-cluster signature overlaps.
    Items outside any known cluster are always kept — this only catches the
    specific overlap patterns editors flagged, not general similarity.
    """
    clusters = _JA_CONCEPT_CLUSTERS if ja else _EN_CONCEPT_CLUSTERS
    kept: list[str] = []
    seen: list[frozenset[str]] = []
    for item in items:
        sig = _concept_signature(item, clusters)
        if sig and any(sig & s for s in seen):
            continue
        kept.append(item)
        seen.append(sig)
    return _thin_key_noun_concentration(kept, ja)


def _thin_key_noun_concentration(items: list[str], ja: bool, max_per_noun: int = 2) -> list[str]:
    """Drop later items that reuse a key noun already used twice in the list.

    Does not ban the nouns; only prevents the mechanical concentration that
    makes Lost/Protected feel template-generated.
    """
    nouns = _JA_KEY_NOUNS if ja else _EN_KEY_NOUNS
    counts: dict[str, int] = {n: 0 for n in nouns}
    kept: list[str] = []
    for item in items:
        probe = item if ja else item.lower()
        hits = [n for n in nouns if n in probe]
        if hits and all(counts[n] >= max_per_noun for n in hits):
            continue
        for n in hits:
            counts[n] += 1
        kept.append(item)
    return kept


def _pick_items(pool: tuple[_Item, ...], seed: int, count: int, topic: str) -> list[str]:
    n = len(pool)
    idxs: list[int] = []
    i = seed % n
    while len(idxs) < min(count, n):
        if i not in idxs:
            idxs.append(i)
        i = (i + 1) % n
    return [pool[j].text.format(topic=topic) for j in idxs]


def _target_count(depth: str, seed: int) -> int:
    """A variable, depth-scaled item count (max-oriented guideline, not a
    fixed quota): 3-4 for standard, 4-5 for deep."""
    lo, hi = (4, 5) if depth == "deep" else (3, 4)
    return lo + (seed % (hi - lo + 1))


def _lost_and_protected(
    topic: str,
    clar: ParallelLifeClarifications,
    ja: bool,
    seed: int,
    depth: str,
    category: str = "default",
    facts: ParallelLifeFacts | None = None,
) -> tuple[list[str], list[str]]:
    lost_pools = _LOST_POOLS_JA if ja else _LOST_POOLS_EN
    protected_pools = _PROTECTED_POOLS_JA if ja else _PROTECTED_POOLS_EN
    pool_key = category
    if facts and facts.education_polarity == "admitted" and category == "education":
        pool_key = "education_admitted"
    lost_pool = lost_pools.get(pool_key, lost_pools.get(category, lost_pools["default"]))
    protected_pool = protected_pools.get(
        pool_key, protected_pools.get(category, protected_pools["default"])
    )

    # Different seeds for count *and* selection so Lost and Protected are
    # never a mechanically mirrored pair (same length, same ordering logic).
    lost_count = _target_count(depth, seed)
    protected_count = _target_count(depth, seed + 11)

    lost = _pick_items(lost_pool, seed, lost_count, topic)
    protected = _pick_items(protected_pool, seed + 7, protected_count, topic)

    if clar.lost:
        stated = _clean_line(clar.lost)
        lost = [stated] + [item for item in lost if item != stated][: lost_count - 1]
    if clar.protected:
        stated = _clean_line(clar.protected)
        protected = [stated] + [item for item in protected if item != stated][: protected_count - 1]

    lost = _dedupe_semantically(lost, ja)
    protected = _dedupe_semantically(protected, ja)

    # If dedup dropped an item below the 3-item floor, backfill from the pool
    # with a concept not already represented, rather than leaving the list
    # too short to be useful.
    lost = _backfill_to_minimum(lost, lost_pool, ja, topic, minimum=3)
    protected = _backfill_to_minimum(protected, protected_pool, ja, topic, minimum=3)

    return lost[:6], protected[:6]


def _backfill_to_minimum(
    items: list[str], pool: tuple[_Item, ...], ja: bool, topic: str, minimum: int
) -> list[str]:
    if len(items) >= minimum:
        return items
    existing = set(items)
    for entry in pool:
        if len(items) >= minimum:
            break
        candidate = entry.text.format(topic=topic)
        if candidate in existing:
            continue
        merged = _dedupe_semantically(items + [candidate], ja)
        if len(merged) > len(items):
            items = merged
            existing.add(candidate)
    return items


# --- Residue -------------------------------------------------------------------

_RESIDUE_TENSION_JA: dict[str, str] = {
    "intimacy": "親密さと自律のあいだ",
    "market-signals": "安定と可能性のあいだ",
    "city": "帰属と移動のあいだ",
    "book": "仕事と創造性のあいだ",
    "education-employment": "継続と再出発のあいだ",
    "work": "責任と欲望のあいだ",
    "body": "ケアと自分の時間のあいだ",
    "clean-society": "期待に応えることと自分の願いのあいだ",
    "after-success": "達成と、その後の生活のあいだ",
    "protocol-publishing": "個人的な記憶と、社会的なパターンのあいだ",
    "old-web": "そのころの自分と、いまの自分のあいだ",
    "contact-data": "見えることと、見えないままでいることのあいだ",
    "meaning-layer": "当時の意味と、いま振り返ってつける意味のあいだ",
    "sound": "記憶に残る音と、いまの静けさのあいだ",
    "image": "覚えている像と、実際に残った記録のあいだ",
    "style": "そのころの自分と、いまの自分の見た目のあいだ",
}
_RESIDUE_TENSION_EN: dict[str, str] = {
    "intimacy": "intimacy and autonomy",
    "market-signals": "stability and possibility",
    "city": "belonging and movement",
    "book": "work and creativity",
    "education-employment": "continuity and reinvention",
    "work": "responsibility and desire",
    "body": "care and one's own time",
    "clean-society": "meeting expectations and one's own wishes",
    "after-success": "achievement and the life that follows it",
    "protocol-publishing": "a private memory and a social pattern",
    "old-web": "who that self was and who this self is now",
    "contact-data": "being visible and staying unseen",
    "meaning-layer": "the meaning it held then and the meaning it holds now",
    "sound": "a remembered sound and the present quiet",
    "image": "a remembered image and what was actually kept",
    "style": "who that self looked like and who this self looks like now",
}


def _residue(topic: _Topic, lenses: list[str], ja: bool) -> str:
    default_key = "market-signals"
    key = next((lid for lid in lenses if lid in (_RESIDUE_TENSION_JA if ja else _RESIDUE_TENSION_EN)), default_key)
    tension = (_RESIDUE_TENSION_JA if ja else _RESIDUE_TENSION_EN)[key]
    if ja:
        return (
            f"この分岐がいまも戻ってくるのは、{tension}に、まだ閉じていない問いがあるからかもしれない。"
            f"それは{topic.prose}そのものを恋しがっているというより、そのころ持てていた生き方の質を、"
            "いまの生活のなかでもう一度確かめたいという気持ちに近いように見える。"
            "戻りたいのが人や場所そのものなのか、その質なのか、あるいは構造そのものへの問いなのかは、"
            "ここでは区別されたままにしておく必要がある。"
        )
    return (
        f"This branch may still return because a question between {tension} has not closed. "
        f"It may be less about missing {topic.prose} itself than about wanting to confirm, once more in "
        "the present, a quality of life that existed then. "
        "Whether what is missed is the actual person or place, a quality of living, or the "
        "structural tension itself needs to stay distinguished rather than collapsed into one."
    )


# --- Observatory layer bodies (heuristic) ------------------------------------
#
# Bodies read the branch's topic directly and never quote or paraphrase the
# raw source text back to the user (no "という出来事のなかには…", no "The event
# inside \"...\""). Each body also names at least one concrete condition
# (rent, graduation timing, a narrative form, comparison axes — per the
# editorial-quality pass, §11) rather than the generic "institutional,
# market, place-based, and historical conditions intersected" placeholder.


def _lens_body_ja(lens_id: str, topic: str) -> str:
    bodies = {
        "education-employment": (
            f"{topic}をめぐる分岐は、教育から就労へ移る制度のなかで起きている。"
            "卒業の時期、最初の就職先、そこに伴う転居、資格や学歴の構造、地域ごとの機会の違いが、"
            "仕事だけでなく、住む場所や人との関係、大人としての独立が始まるタイミングまで、"
            "同時に決めてしまうことが多い。自由な選択に見えても、実際には制度的な条件のなかでの"
            "選択だった可能性がある。"
        ),
        "market-signals": (
            f"{topic}に関わる生活を続けるには、家賃、収入、仕事の安定、地域の労働市場、"
            "世帯を持つための条件、そして移動のしやすさや家族からの支えが必要だった。"
            "愛情だけでは共有した生活は成立しない。当時のこうした経済的な条件が、その分岐の"
            "形を決めていた可能性がある。"
        ),
        "book": (
            f"{topic}のなかには、物語の芯になりうる要素がある。誰の視点から語るか、"
            "くり返し立ち返るイメージは何か、そしてどんな形が適しているか — 私小説的な断片か、"
            "距離を置いた観察記録か。これは特定の人を失う物語ではなく、共に生きる生活を"
            "成立させる条件についての物語かもしれない。"
        ),
        "protocol-publishing": (
            "この分岐を、似た年齢・地域・就労の形・時代の条件を持つ他の匿名の記録と並べてみると、"
            "個人の選択の背後にある社会的なパターンが見えてくることがある。実名や特定できる詳細は"
            "含めず、比較の軸だけを残すことで、誰と生活を築けたかだけでなく、どのような制度のもとで"
            "それが可能だったかが見えてくる。"
        ),
        "work": (
            "組織にとどまるか、離れるかという選択は、労働の条件と自己像を同時に形づくる。"
            "続けることは、積み重ねと役割を守ることでもあり、同時に何かを差し出すことでもある。"
        ),
        "city": (
            f"{topic}という場所は、単なる背景ではなく、帰属と移動の記憶そのものだった。"
            "そこに残る、あるいは離れるという選択は、その後の生活の輪郭を決めていく。"
        ),
        "intimacy": (
            "親密さは、それだけで生活の形を決めるわけではない。共に生きることと、"
            "自分自身の自律を保つことの間には、いつも小さな緊張がある。"
        ),
        "body": (
            "この分岐は、頭で考えた選択であるだけでなく、身体で経験された時間でもあった。"
            "疲れや回復、ケアの感覚が、選択の重さに影響していた可能性がある。"
        ),
        "clean-society": (
            "「普通はこうするものだ」という当時の規範は、選択の範囲を静かに狭めていたかもしれない。"
            "誰がリスクを引き受け、誰が見えないままでいたかを考える価値がある。"
        ),
        "after-success": (
            "何かを達成したあとに残る問いは、達成の前の問いとは違う形をしている。"
            "評価が得られたとしても、それとは別に、まだ閉じていない生活の問いが残ることがある。"
        ),
        "old-web": (
            "当時のインターネットの文化やつながりも、その分岐の一部だった可能性がある。"
            "オンラインでの人格や関係は、いまでは戻れない場所として記憶に残ることがある。"
        ),
        "contact-data": (
            "個人的な出来事であっても、それがどこかに記録され、可視化される条件のもとにあったかもしれない。"
        ),
        "meaning-layer": (
            f"{topic}に与えていた意味は、時間とともに変わってきたはずだ。"
            "当時つけた意味と、いま振り返ってつける意味は、同じではない。"
        ),
        "sound": (
            "覚えている声や音が、その時期の記憶を場所よりも強く保っていることがある。"
        ),
        "image": (
            "写真として残らなかった場面ほど、想像のなかで何度も描き直されることがある。"
        ),
        "style": (
            "身にまとっていたものや見た目の変化も、そのころ生きていた自分の記録の一部だった。"
        ),
    }
    return bodies.get(
        lens_id,
        f"{topic}という個人的な出来事も、その背後にある社会的な条件から完全に自由ではなかった。",
    )


def _lens_body_en(lens_id: str, topic: str) -> str:
    bodies = {
        "education-employment": (
            f"The branch around {topic} sits within the structure that moves a person from "
            "education into employment: graduation timing, a first job, the relocation it may "
            "have required, the shape of the credential involved, and regional differences in "
            "opportunity. This transition often fixes not only work, but where to live, which "
            "relationships continue, and the timing of adult independence, all at once. What "
            "looked like a free choice may have been a choice made within institutional terms."
        ),
        "market-signals": (
            f"Continuing a life built around {topic} required housing, income, a stable regional "
            "job market, and often family support or the ability to relocate. Love alone does not "
            "create a shared life; rent, job stability, and household formation are the material "
            "conditions that shaped this branch."
        ),
        "book": (
            f"There is a narrative center hidden inside the branch around {topic} — a point of "
            "view, a recurring image, a form that would suit it (a personal essay, a distanced "
            "observation). This may not be a story about losing a particular person — it may be a "
            "story about the conditions required to turn closeness into a shared life."
        ),
        "protocol-publishing": (
            "Placed beside other anonymous records with a similar age, region, employment form, "
            "and era — with no names or identifying detail kept, only the axes of comparison — "
            "this branch may reveal a pattern that sits above any single life: not only who people "
            "were able to build a life with, but under what conditions that was possible at all."
        ),
        "work": (
            "Staying in or leaving an organization shapes labor conditions and self-image at the "
            "same time. Continuing can mean protecting continuity and a role, and it can also mean "
            "giving something away."
        ),
        "city": (
            f"{topic} was not only a backdrop — it was itself a memory of belonging and movement. "
            "Staying in, or leaving, that place quietly shapes the outline of the life that follows."
        ),
        "intimacy": (
            "Closeness alone does not decide the shape of a life. There is usually a small, "
            "ongoing tension between building something shared and keeping one's own autonomy."
        ),
        "body": (
            "This branch was not only a decision made in thought — it was also time lived in the "
            "body. Fatigue, recovery, and care may have shaped how heavy the choice felt."
        ),
        "clean-society": (
            'What an era treated as "the normal thing to do" may have quietly narrowed the range '
            "of choices available. It is worth asking who was asked to absorb the risk, and who "
            "remained visible."
        ),
        "after-success": (
            "What remains after an achievement takes a different shape from what came before it. "
            "Recognition does not necessarily close the unresolved questions of daily life."
        ),
        "old-web": (
            "The internet culture of that time may also have been part of this branch. Online "
            "identities and connections are sometimes remembered as places that cannot be returned to."
        ),
        "contact-data": (
            "Even a personal event may have existed within conditions of visibility and record-keeping "
            "that were never fully chosen."
        ),
        "meaning-layer": (
            f"The meaning given to {topic} has likely changed over time. The meaning given then and "
            "the meaning given in hindsight are not the same."
        ),
        "sound": ("A remembered voice or sound can hold a period more strongly than any place can."),
        "image": (
            "A scene that was never photographed is often the one redrawn most often in imagination."
        ),
        "style": (
            "What was worn, and how appearance changed, was also part of the record of who was "
            "being lived at the time."
        ),
    }
    return bodies.get(
        lens_id,
        f"This personal event around {topic} was not entirely free from the social conditions behind it.",
    )


def _observatory_layers(topic: _Topic, lens_ids: list[str], ja: bool) -> list[ObservatoryLayer]:
    """Build the Observatory Layer readings.

    ``title`` is always the official English lens name (e.g. "Market
    Signals") in both languages — it is never translated or transliterated
    inconsistently (editorial-quality pass §10). ``descriptor`` is a short
    phrase in the response language shown directly beneath it.
    """
    layers = []
    for lid in lens_ids:
        lens_def = OBSERVATORY_LENSES[lid]
        body = _lens_body_ja(lid, topic.prose) if ja else _lens_body_en(lid, topic.prose)
        layers.append(
            ObservatoryLayer(
                id=lid,
                title=lens_def.name_en,
                descriptor=lens_def.descriptor_ja if ja else lens_def.descriptor_en,
                body=body,
            )
        )
    return layers


# Cross-lens synthesis must read like an editorial essay, not a research
# summary (editorial-quality pass round 2): name the apparent personal
# choice, ground it in the *concrete domain* behind each selected lens
# (rather than leading with the branded lens names), and close on one new
# conclusion not already stated verbatim in Branch Point / Chosen Path /
# Residue / the individual lens bodies. Lens names may still appear, but the
# domain phrase is what carries the sentence.
_LENS_DOMAIN_PHRASE_JA: dict[str, str] = {
    "education-employment": "卒業から就職へ移る時期",
    "market-signals": "生活を成り立たせる経済条件",
    "book": "いまも残る物語としての形",
    "protocol-publishing": "同じ条件下にいた人たちの記録",
    "work": "仕事を続けるか離れるかという条件",
    "city": "住む場所と移動のしやすさ",
    "intimacy": "親密な関係の形",
    "body": "身体で感じていた疲れや回復",
    "clean-society": "当時「普通」とされていた基準",
    "after-success": "達成のあとに残る生活の問い",
    "old-web": "そのころのオンラインでのつながり",
    "contact-data": "見える形で記録されていた条件",
    "meaning-layer": "当時とは違う、いま与えている意味",
    "sound": "記憶に残る音",
    "image": "記憶のなかの光景",
    "style": "そのころの見た目や身なり",
}
_LENS_DOMAIN_PHRASE_EN: dict[str, str] = {
    "education-employment": "the timing of graduating into a first job",
    "market-signals": "the economic conditions that make a life sustainable",
    "book": "the shape a story about it would take",
    "protocol-publishing": "records from others who lived under similar conditions",
    "work": "the terms of staying in or leaving the work itself",
    "city": "where to live and how easily one could move",
    "intimacy": "the shape a close relationship could take",
    "body": "the fatigue and recovery carried in the body",
    "clean-society": "what counted as normal at the time",
    "after-success": "the questions that remain after any achievement",
    "old-web": "the online connections of that period",
    "contact-data": "the conditions under which it was visible or recorded",
    "meaning-layer": "the different meaning it holds now",
    "sound": "a sound that still marks the memory",
    "image": "an image that still marks the memory",
    "style": "how appearance itself changed",
}

_JA_SYNTHESIS_OPENERS = [
    "{topic}をめぐる決断の背後には、{phrases}が重なっていた。",
    "{phrases}を同時に見ると、{topic}をめぐる分岐は、勇気の有無だけでは説明できない。",
    "それぞれを別々に見ると個人的な迷いに見える。しかし{phrases}を一緒に読むと、輪郭が変わってくる。",
]
_EN_SYNTHESIS_OPENERS = [
    "Behind the decision around {topic} were {phrases}, already pressing on one another.",
    "Read together — {phrases} — the branch around {topic} was never only a question of courage.",
    "Taken one by one, each looks like a private hesitation. Read side by side, {phrases} change the outline.",
]

# Conclusions add the one insight the synthesis is required to contribute
# (editorial-quality pass §12): what was personal, what was structurally
# shaped, and why the branch still matters now. Varying the closing
# observation keeps every result from converging on the same sentence.
_JA_SYNTHESIS_CONCLUSIONS = [
    "この分岐は一人の意思だけでなく、生活を成立させる条件によっても形づくられていた。"
    "いま問うべきなのは、当時どれが正しかったかよりも、何が当時しか選べなかったかを見ることだ。",
    "個人的な決断に見えても、同じ時期・同じ地域にいた人たちにも、似た押し引きが働いていたはずだ。"
    "だからこの経験は、一人だけの物語には収まらない。",
    "特別な失敗でも特別な成功でもない。同じ押し引きのなかにいた多くの人に共有されている経験だからこそ、"
    "いまも静かに残り続けている。",
]
_EN_SYNTHESIS_CONCLUSIONS = [
    "The branch was shaped not only by one will, but by what it took to keep a life standing. "
    "What matters now is less which choice was right than what could barely be chosen then.",
    "It looks personal, and it was — but people living in the same years and places were under "
    "similar pressure. This is not only one person's story.",
    "Neither a special failure nor a special success. It remains because many people lived under "
    "the same push and pull, and still carry a version of this question.",
]
_JA_SYNTHESIS_PRESENT_BRIDGE = (
    "いま似た分岐を考えるなら、当時と同じ押し引きが、いまもそのまま残っているとは限らない。"
)
_EN_SYNTHESIS_PRESENT_BRIDGE = (
    "If a similar branch is being weighed now, the same pressures may no longer be arranged the same way."
)


def _synthesis_domain_phrases(lens_ids: list[str], ja: bool) -> str:
    table = _LENS_DOMAIN_PHRASE_JA if ja else _LENS_DOMAIN_PHRASE_EN
    phrases = [table.get(lid, OBSERVATORY_LENSES[lid].name_en) for lid in lens_ids]
    if ja:
        if len(phrases) <= 1:
            return phrases[0] if phrases else ""
        return "、".join(phrases[:-1]) + "、そして" + phrases[-1]
    if len(phrases) <= 1:
        return phrases[0] if phrases else ""
    if len(phrases) == 2:
        return f"{phrases[0]} and {phrases[1]}"
    return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"


def _cross_lens_synthesis(
    topic: _Topic, lens_ids: list[str], seed: int, ja: bool, depth: str = "standard"
) -> str:
    phrases = _synthesis_domain_phrases(lens_ids, ja)
    if ja:
        opener = _JA_SYNTHESIS_OPENERS[seed % len(_JA_SYNTHESIS_OPENERS)].format(
            topic=topic.prose, phrases=phrases
        )
        conclusion = _JA_SYNTHESIS_CONCLUSIONS[seed % len(_JA_SYNTHESIS_CONCLUSIONS)].format(
            topic=topic.prose
        )
        text = f"{opener}{conclusion}"
        if depth == "deep":
            text += f" {_JA_SYNTHESIS_PRESENT_BRIDGE}"
        return text
    opener = _EN_SYNTHESIS_OPENERS[seed % len(_EN_SYNTHESIS_OPENERS)].format(
        topic=topic.prose, phrases=phrases
    )
    conclusion = _EN_SYNTHESIS_CONCLUSIONS[seed % len(_EN_SYNTHESIS_CONCLUSIONS)].format(
        topic=topic.prose
    )
    text = f"{opener} {conclusion}"
    if depth == "deep":
        text += f" {_EN_SYNTHESIS_PRESENT_BRIDGE}"
    return text


# --- Rebranch / Closing ------------------------------------------------------
#
# Every item is a single, concrete, present-tense action the person can
# imagine doing this week — never a reversal of the past (contacting an ex,
# quitting a job, moving immediately, ending a relationship, a major
# financial decision). Pools are branch-category-specific (editorial-quality
# pass round 2, §3) so "what to do" reads as connected to the actual branch
# rather than generic self-help language. ``_DEFAULT`` covers any branch
# whose topic did not match a specific category.

_REBRANCH_EDUCATION_JA = [
    "選ばなかった大学と進んだ大学が、それぞれ何を象徴していたかを書き比べる。",
    "大学そのものではなく、当時ひかれていた科目や分野を一つ選び、いま読み直す。",
    "選んだ道で実際に得られたものを、三つだけ書き出す。",
    "その分野に関する本や講座を一つ選び、今週30分だけ触れてみる。",
    "当時受けたかった授業に近いオンライン講座を一つ探してみる。",
]
_REBRANCH_EDUCATION_ADMITTED_JA = [
    "合格した進学先で実際に得られたものを、三つだけ書き出す。",
    "当時ひかれていた科目や分野を一つ選び、いま読み直す。",
    "その分野に関する本や講座を一つ選び、今週30分だけ触れてみる。",
    "進学が開いた人間関係のうち、いまも残っているものを一つ挙げる。",
    "合格前に想像していた学生生活と、実際の日々を二列に分けて書く。",
]
_REBRANCH_WORK_JA = [
    "当時得意だった仕事のやり方を、いまの役割のなかで一つ試す。",
    "その仕事に近い分野で、小さな実験を一つ始めてみる。",
    "選ばなかった仕事が何を意味していたかを、一段落で書く。",
    "同じ業界の人と、今月中に一度話す機会をつくる。",
    "当時の求人や業界の情報をいま眺めて、何が変わったかを書き留める。",
]
_REBRANCH_WORK_STAYED_JA = [
    "いまの役割のなかで続けてきたことを、三つ書き出す。",
    "当時得意だった仕事のやり方を、いまの役割のなかで一つ試す。",
    "残ることを選んだ理由を、一段落で書く。",
    "同じ業界の人と、今月中に一度話す機会をつくる。",
    "いまの仕事で守りたかったものを、一語で書いてみる。",
]
_REBRANCH_WORK_RESIGNED_JA = [
    "仕事を離れたあとに得られたものを、三つ書き出す。",
    "その仕事に近い分野で、小さな実験を一つ始めてみる。",
    "辞めることを選んだ理由を、一段落で書く。",
    "同じ業界の人と、今月中に一度話す機会をつくる。",
    "当時の求人や業界の情報をいま眺めて、何が変わったかを書き留める。",
]
_REBRANCH_RELATIONSHIP_JA = [
    "その人自身と、その人が象徴していた生き方を、別々に書き分ける。",
    "共に生きていたかもしれない生活を、送らない手紙として書いてみる。",
    "いまの生活のなかで、どんな親密さが大切かを一つ選んで書く。",
    "その関係が大事にしていた価値を一つ、今週の生活に取り入れる。",
    "自分にとっての親密さの理想を、三つの言葉で書いてみる。",
]
_REBRANCH_PLACE_JA = [
    "そこで暮らすことの、いちばん惹かれていた部分を一語で書く。",
    "その場所の音楽や料理、言葉のどれか一つを、今週の生活に取り入れる。",
    "移動することと、逃げることの違いを、二つの文で書き分ける。",
    "短い旅程でその場所を訪ねる計画を、実行しない前提で一度立ててみる。",
    "その土地の気候や季節感を、今日の暮らしにひとつだけ取り入れる。",
]
_REBRANCH_CREATIVITY_JA = [
    "当時やめた創作を、今週30分だけ再開してみる。",
    "小さな作品を一つだけ、仕上げずに作ってみる。",
    "当時のノートやアイデアを一つ、引っ張り出して読み直す。",
    "月に一度など、続けやすい頻度で創作の時間を予定に入れる。",
    "その創作について、なぜやめたのかを一段落で書く。",
]
_REBRANCH_CARE_JA = [
    "その選択によって可能になったことを、三つ書き出す。",
    "責任として担っていることと、自分自身であることを、別の欄に分けて書く。",
    "誰にも邪魔されない時間を、週に30分だけ確保する。",
    "その役割のなかで、いちばん大切にしてきたことを一つ挙げる。",
    "同じ立場にいる人に、今週一度連絡をとってみる。",
]
_REBRANCH_DEFAULT_JA = [
    "選ばなかった人生を、短いフィクションとして書いてみる。",
    "失ったものと守られたものを、同じ紙に並べて書く。",
    "送らない手紙を、そのときの自分に向けて書いてみる。",
    "いまの生活のなかに、当時と似た感覚を得られる小さな習慣を一つつくる。",
    "その分岐について、いちばん覚えていることを一段落で書く。",
]

_REBRANCH_EDUCATION_EN = [
    "Compare, in writing, what each school or course actually represented at the time.",
    "Revisit one subject that interested you then, rather than the institution itself.",
    "Write down three concrete things the chosen path actually gave you.",
    "Spend 30 minutes this week reading one book or course in that field.",
    "Look for one online course close to a class you wished you'd taken then.",
]
_REBRANCH_EDUCATION_ADMITTED_EN = [
    "Write down three concrete things admission to that school actually gave you.",
    "Revisit one subject that interested you then, rather than the institution itself.",
    "Spend 30 minutes this week reading one book or course in that field.",
    "Name one relationship opened by that enrollment that still remains.",
    "Write, in two columns, the student life imagined before admission and the days actually lived.",
]
_REBRANCH_WORK_EN = [
    "Try, once, a way of working you were good at back then, inside your current role.",
    "Start one small experiment in a field close to that job.",
    "Write one paragraph about what the unchosen job actually represented.",
    "Arrange to talk with someone in that field once this month.",
    "Look at job postings in that field and note what has changed since then.",
]
_REBRANCH_WORK_STAYED_EN = [
    "Write down three things you have continued to build inside the current role.",
    "Try, once, a way of working you were good at back then, inside your current role.",
    "Write one paragraph about why staying was chosen.",
    "Arrange to talk with someone in that field once this month.",
    "Name, in one word, what you most wanted to protect by staying.",
]
_REBRANCH_WORK_RESIGNED_EN = [
    "Write down three things that became possible after leaving that work.",
    "Start one small experiment in a field close to that job.",
    "Write one paragraph about why leaving was chosen.",
    "Arrange to talk with someone in that field once this month.",
    "Look at job postings in that field and note what has changed since then.",
]
_REBRANCH_RELATIONSHIP_EN = [
    "Write separately about the person and the life they seemed to represent.",
    "Write, but do not send, a letter describing the shared life that might have been.",
    "Name one form of closeness that still matters in your life now.",
    "Bring one value that relationship held into this week's life, in a small way.",
    "Describe your own ideal of closeness in three words.",
]
_REBRANCH_PLACE_EN = [
    "Write, in one word, what you found most appealing about living there.",
    "Bring one piece of that place's music, food, or language into this week.",
    "Write two sentences distinguishing moving there from leaving here.",
    "Sketch a short, non-committal plan for a brief visit to that place.",
    "Bring one detail of that place's climate or season into today.",
]
_REBRANCH_CREATIVITY_EN = [
    "Resume that creative practice for 30 minutes this week, nothing more.",
    "Make one small piece without finishing it.",
    "Pull out one old notebook or idea and read through it again.",
    "Schedule a modest, repeatable slot for that practice, such as once a month.",
    "Write one paragraph about why that practice was set aside.",
]
_REBRANCH_CARE_EN = [
    "Write down three things that choice actually made possible.",
    "List, in separate columns, what is responsibility and what is simply you.",
    "Reserve 30 minutes a week that belongs only to you.",
    "Name one thing you have valued most in that role.",
    "Reach out once this week to someone in a similar situation.",
]
_REBRANCH_DEFAULT_EN = [
    "Write the unchosen life as a short piece of fiction.",
    "Write down what was lost and what was protected on the same page.",
    "Write a letter to that earlier self that will never be sent.",
    "Build one small habit into the current life that recovers a similar feeling.",
    "Write one paragraph about what you remember most clearly about that branch.",
]

_REBRANCH_POOLS_JA: dict[str, list[str]] = {
    "education": _REBRANCH_EDUCATION_JA,
    "education_admitted": _REBRANCH_EDUCATION_ADMITTED_JA,
    "work": _REBRANCH_WORK_JA,
    "work_stayed": _REBRANCH_WORK_STAYED_JA,
    "work_resigned": _REBRANCH_WORK_RESIGNED_JA,
    "relationship": _REBRANCH_RELATIONSHIP_JA,
    "place": _REBRANCH_PLACE_JA,
    "creativity": _REBRANCH_CREATIVITY_JA,
    "care": _REBRANCH_CARE_JA,
    "default": _REBRANCH_DEFAULT_JA,
}
_REBRANCH_POOLS_EN: dict[str, list[str]] = {
    "education": _REBRANCH_EDUCATION_EN,
    "education_admitted": _REBRANCH_EDUCATION_ADMITTED_EN,
    "work": _REBRANCH_WORK_EN,
    "work_stayed": _REBRANCH_WORK_STAYED_EN,
    "work_resigned": _REBRANCH_WORK_RESIGNED_EN,
    "relationship": _REBRANCH_RELATIONSHIP_EN,
    "place": _REBRANCH_PLACE_EN,
    "creativity": _REBRANCH_CREATIVITY_EN,
    "care": _REBRANCH_CARE_EN,
    "default": _REBRANCH_DEFAULT_EN,
}


def _rebranch_indices(seed: int, count: int, pool_size: int) -> list[int]:
    idxs: list[int] = []
    i = seed % pool_size
    while len(idxs) < min(count, pool_size):
        if i not in idxs:
            idxs.append(i)
        i = (i + 1) % pool_size
    return idxs


def _rebranch_items(seed: int, depth: str, ja: bool, category: str = "default") -> list[str]:
    """3-5 concrete, branch-category-specific Re-branch actions (max-oriented
    guideline: 3-4 for standard, 4-5 for deep)."""
    pools = _REBRANCH_POOLS_JA if ja else _REBRANCH_POOLS_EN
    pool = pools.get(category, pools["default"])
    count = _target_count(depth, seed + 3)
    idxs = _rebranch_indices(seed, count, len(pool))
    return [pool[i] for i in idxs]


# The Closing must not repeat the same fallback conclusion in every result
# (editorial-quality pass §13). Each variant still holds three things without
# giving advice: the chosen life, the unchosen possibility, and the value
# that remains available now.
_JA_CLOSING_POOL = [
    "その分岐そのものは、もう閉じている。しかし、それが浮かび上がらせた願いや価値は、"
    "まだ閉じていないのかもしれない。どちらの人生が正しかったかを決める必要はなく、"
    "いま持っているものと、あのとき手放したものを、同時に見つめておくことはできる。",
    "選ばなかった道は、もう歩けない。それでも、その道が示していた何かを、"
    "いまの生活のなかで小さく持ち続けることはできる。どちらが正しかったかではなく、"
    "両方がここにあったという事実だけが残る。",
    "あの分岐は閉じられたが、そこにあった問いまでもが消えたわけではない。"
    "いま生きている生活と、あのとき手放した生活を、比べずに並べて置いておくことができる。",
]
_EN_CLOSING_POOL = [
    "The branch itself is closed now. But the value or wish it revealed may not be. "
    "There is no need to decide which life was correct — it is possible to hold what is here "
    "now and what was released then, at the same time.",
    "The unchosen road can no longer be walked. What it once pointed toward can still be kept, "
    "in a small way, inside the life that is actually here. The question is not which path was "
    "right, but that both were once real.",
    "The branch has closed, but the question it raised has not disappeared with it. "
    "The life being lived now and the life set aside then can sit side by side, without "
    "needing to be compared.",
]


def _closing(seed: int, ja: bool) -> str:
    pool = _JA_CLOSING_POOL if ja else _EN_CLOSING_POOL
    return pool[seed % len(pool)]


# --- Heuristic orchestrator ---------------------------------------------------


def _family_formation_branch_point(grounded, age: str | None, clar, ja: bool) -> str:
    if not ja:
        text = f"At the center is {grounded.primary_event}."
        if grounded.secondary_branches:
            text += f" Afterward, {grounded.secondary_branches[0]} became visible."
        if grounded.present_question:
            text += f" What remains now is {grounded.present_question}."
        return text
    text = (
        f"この読みの中心にあるのは、{grounded.primary_event}という出来事である。"
        " 家族形成をめぐる分岐である。"
    )
    if age:
        text += f" それは{age}のころのことだった。"
    if grounded.chosen_path:
        text += f" 実際に選ばれたのは、{grounded.chosen_path}という生活だった。"
    if grounded.secondary_branches:
        text += f" そのあとで、{grounded.secondary_branches[0]}が見えてきた。"
    if grounded.present_question:
        text += f" いま残っているのは、{grounded.present_question}である。"
    return text


def _family_formation_chosen(grounded, clar, ja: bool) -> str:
    chosen = grounded.chosen_path or (clar.chosen_path if clar else None)
    if ja:
        return (
            f"実際に選ばれたのは、{chosen or '妻と子どもとの家族の生活'}だった。"
            " 親としての役割が始まり、時間、仕事、住まい、ケアの配分が組み直された。"
            " 授かったあとに続く日々は、正しさの証明ではなく、いまも更新され続けている生活である。"
        )
    return (
        f"What was chosen was {chosen or 'a family life with spouse and child'}. "
        "Parenthood reorganized time, work, housing, and care."
    )


def _family_formation_unchosen(grounded, clar, ja: bool) -> str:
    unchosen = grounded.unchosen_path or (clar.unchosen_path if clar else None)
    if ja:
        text = (
            f"選ばなかった側には、まず{unchosen or '不妊治療を諦めること'}がある。"
            " それは完成した別の幸福ではなく、別の負担と不確かさを伴う可能性だった。"
        )
        if grounded.secondary_branches:
            text += (
                f" それとは別に、{grounded.secondary_branches[0]}も、"
                "同じ生活のなかで開いている。"
            )
        return text
    return (
        f"On the unchosen side there is {unchosen or 'stopping fertility treatment'}. "
        "It cannot be treated as a finished happier life."
    )


def _topic_locked_to_grounded(source_text: str, grounded, ja: bool) -> _Topic:
    """Force topic category from grounded primary domain — facts outrank keywords."""
    from app.parallel_life_domain import DOMAIN_TO_TOPIC_CATEGORY

    matched = _match_topic(source_text, ja)
    cat = DOMAIN_TO_TOPIC_CATEGORY.get(grounded.primary_domain, matched.category)
    if grounded.primary_domain == "family-formation":
        if ja:
            return _Topic((), "家族形成", "家族形成", category="family_formation")
        return _Topic((), "family formation", "Family Formation", category="family_formation")
    if cat != matched.category and grounded.primary_domain != "other":
        if ja:
            return _Topic(
                (),
                grounded.primary_event[:20] or "その道",
                grounded.primary_event[:12] or "分岐",
                category=cat,
            )
        return _Topic((), grounded.primary_event[:40] or "that path", "Path", category=cat)
    if matched.category == cat:
        return matched
    return _Topic(matched.keywords, matched.prose, matched.title, category=cat)


def _heuristic_parallel_life(request: ParallelLifeRequest) -> ParallelLifeResult:
    from app.parallel_life_domain import (
        extract_grounded_primary_branch,
        seed_domains_for,
        validate_domain_consistency,
    )

    ja = _is_ja(request.language, request.source_text)
    clar = request.clarifications
    depth = request.depth if request.depth in ("standard", "deep") else "standard"

    # Fact extraction + primary-event lock MUST precede title/section generation.
    facts = extract_parallel_life_facts(request.source_text, clar, ja=ja)
    grounded = extract_grounded_primary_branch(request.source_text, clar, None, ja=ja)
    topic = _topic_locked_to_grounded(request.source_text, grounded, ja)
    age = _format_age(clar.age or grounded.age or facts.age, ja)
    seed = _seed(request.source_text, request.language, depth)

    title, subtitle = _title_and_subtitle(topic, age, ja, seed, facts, grounded=grounded)
    if grounded.primary_domain == "family-formation" and ja:
        branch_point = _family_formation_branch_point(grounded, age, clar, ja)
        chosen = _family_formation_chosen(grounded, clar, ja)
        unchosen = _family_formation_unchosen(grounded, clar, ja)
    else:
        branch_point = _branch_point(topic, age, clar, ja, facts)
        chosen = _chosen_path(topic, clar, ja, seed, facts)
        unchosen = _unchosen_life(topic, clar, ja, seed, facts)

    lost_category = "care" if topic.category == "family_formation" else topic.category
    lost, protected = _lost_and_protected(
        topic.prose, clar, ja, seed, depth, category=lost_category, facts=facts
    )

    extra_text = " ".join(
        v for v in (clar.constraints, clar.lost, clar.protected, clar.what_remains) if v
    )
    lens_ids = select_observatory_lenses(request.source_text, extra_text, depth)
    if grounded.primary_domain == "family-formation":
        # Prefer family-relevant lenses; never let creativity seeds steer selection.
        preferred = ["intimacy", "body", "education-employment", "protocol-publishing", "book"]
        merged: list[str] = []
        for lid in preferred + list(lens_ids):
            if lid not in merged:
                merged.append(lid)
            if len(merged) >= (3 if depth == "standard" else 4):
                break
        lens_ids = merged
    residue = _residue(topic, lens_ids, ja)
    if grounded.primary_domain == "family-formation" and ja:
        residue = (
            f"{grounded.present_question or '家族の連続性をめぐる問い'}が、いまも形を変えて残っている。"
            " 授かったあとに続く家族の生活のなかで、叶った願いと未決の可能性が同じ場所にある。"
        )
    layers = _observatory_layers(topic, lens_ids, ja)
    synthesis = _cross_lens_synthesis(topic, lens_ids, seed, ja, depth)
    if facts.education_polarity == "admitted" and topic.category == "education":
        rebranch_category = "education_admitted"
    elif facts.work_polarity == "stayed":
        rebranch_category = "work_stayed"
    elif facts.work_polarity == "resigned":
        rebranch_category = "work_resigned"
    elif topic.category == "family_formation":
        rebranch_category = "care"
    else:
        rebranch_category = topic.category
    rebranch = _rebranch_items(seed, depth, ja, rebranch_category)
    closing = _closing(seed, ja)
    if grounded.primary_domain == "family-formation" and ja:
        closing = (
            f"いまここにあるのは、{grounded.chosen_path or grounded.primary_event}である。"
            " 選ばなかった可能性を消す必要はないが、いまの家族を別の主題で読み替える必要もない。"
        )

    allowed_seeds = seed_domains_for(grounded.primary_domain)
    if depth == "deep":
        seed_domain = "return" if "city" in lens_ids else "possibility"
        seed_line = seed_line_for_domain(
            request.language, seed_domain, seed, allowed_domains=allowed_seeds
        )
        if seed_line:
            residue = residue + (f" {seed_line}" if ja else f" {seed_line}")
        recovery = seed_line_for_domain(
            request.language, "recovery-vs-reversal", seed, allowed_domains=allowed_seeds
        )
        if recovery:
            closing = closing + f" {recovery}"

    result = ParallelLifeResult(
        title=title,
        subtitle=subtitle,
        branch_point=branch_point,
        chosen_path=chosen,
        unchosen_life=unchosen,
        lost=lost,
        protected=protected,
        residue=residue,
        observatory_layers=layers,
        cross_lens_synthesis=synthesis,
        rebranch=rebranch,
        closing=closing,
        generation_mode="heuristic",
        language="ja" if ja else "en",
        depth=depth,
    )
    validate_factual_consistency(request.source_text, result, facts, ja=ja)
    validate_domain_consistency(result, grounded, ja=ja)
    return result


# --- LLM generation with strict structured validation -------------------------


def _build_llm_prompt(request: ParallelLifeRequest) -> tuple[str, str]:
    ja = _is_ja(request.language, request.source_text)
    clar = request.clarifications
    depth = request.depth
    n_lenses = "3から4" if depth == "deep" else "2から3"
    valid_ids = ", ".join(OBSERVATORY_LENSES.keys())
    facts = extract_parallel_life_facts(request.source_text, clar, ja=ja)
    facts_block = facts_prompt_block(facts, ja=ja)

    clar_lines = []
    for label, value in (
        ("age", clar.age),
        ("chosen_path", clar.chosen_path),
        ("unchosen_path", clar.unchosen_path),
        ("what_remains", clar.what_remains),
        ("constraints", clar.constraints),
        ("lost", clar.lost),
        ("protected", clar.protected),
    ):
        if value:
            clar_lines.append(f"{label}: {value}")
    clar_block = "\n".join(clar_lines) if clar_lines else "(none)"

    if ja:
        system_prompt = f"""あなたは Parallel Life（Kosuke Protocol）です。ユーザーが書いた人生の分岐を、
私的なエッセイのような一つの文書として読みます。守ること：
- 断定的な予言、診断、他人の実名や識別情報を書かない
- 「選ばなかった人生」は可能性としてのみ語り、確定した事実のように書かない（かもしれない・可能性がある、を使う）
- 選んだ人生を失敗や妥協として扱わない
- Lost と Protected のどちらが優れているとも述べない
- Observatory Layer（社会との接続）は次のIDのうちから{n_lenses}個だけ選ぶ（重複不可）：{valid_ids}
- すべて日本語で書く
- 助言・スローガン・「すべては意味がある」のような表現は使わない
事実の保持（最重要）：
{facts_block}
- 明示された事実の polarity を反転してはならない（合格→不合格、受かった→落ちた、選んだ→選ばなかった、
  進学した→進学しなかった、続けた→やめた、残った→離れた、結婚した→結婚しなかった、など）
- 固有名（例：早稲田大学、第一文学部）の意味を変えてはならない。省略はよいが、別の大学へ進んだ等に置き換えない
- polarity が不明なときは推測せず、「その時、進学をめぐる大きな分岐があった。」のような中立表現を使う
- タイトルは事実抽出のあとで書く。合格なのに「戻らなかった進学先」「選ばなかった進学先」など失敗前提の題を付けない
- 明示された出来事（出産・不妊治療・家族形成など）を、創作・執筆・作品制作など別主題へ置き換えてはならない
- 例文があれば文体の参考のみ。例の主題・人物・場所・行為を事実として使わない
文体について（重要）：
- 「という入力の中には」「ユーザーが書いた」「本文には」のように、入力されたテキストをテキストとして
  説明してはならない。ユーザーの言葉をそのまま引用符で囲んで再掲してもならない。分岐そのものを、
  完成した読み物として直接書くこと（例：合格が明示されているなら「第一志望に届かなかった」と書かず、
  「第一志望への合格が、その後の学びや仕事を静かに開いていった」のように、事実に沿って書く）
- 日本語は英語からの翻訳のような構文（二重否定、持って回った名詞化）を避け、具体的な主語と述語を持つ、
  もとから日本語で書かれた文章にする。「可能性」「選択」「分岐」「構造」「かもしれない」を同じ文の中で
  繰り返さない
- タイトルは3〜12語の、文法的に完全な句にする。テンプレートの断片（{{}}など）や、"The that ..." の
  ような重複した限定詞を含めない
- 文中に "…" や "...." のような省略記号を使わない
Lost と Protected について：
- 標準では3〜4個、深く読むでは4〜5個を目安にする（固定数ではない）。Lost と Protected の個数を
  そろえる必要はない
- 同じ概念を言い換えただけの項目を並べない（例：「選択肢を残せること」「将来の可能性を残せること」
  「次の道を選べる余地」はすべて同じ概念であり、1項目に統合する）。各項目は一つの概念だけを表し、
  できるだけ具体的な名詞句にする
- Lost と Protected を機械的に対にしない（例えば常に「自由」対「安定」のような単純な鏡像にしない）
Cross-Lens Synthesis（レンズを重ねると見えること）について：
- 選んだレンズの名前を並べる書き出し（「Education–Employment、Intimacy、Bookを重ねてみると……」）を
  避ける。レンズ名を使ってもよいが、それが文章を支配してはならない。代わりに、そのレンズが指す
  具体的な領域（卒業と就職の時期、家賃や収入の条件、住む場所、親密な関係の形、など）を主語にする
- 「制度・市場・場所・時代の条件が交差する場所で生まれていた」「個人的な経験でありながら、それは
  個人だけによってつくられたものではない」のような硬い言い回しをそのまま使わない
- 分岐点・選んだ人生・今に残っているもの・各レンズの本文で、すでに述べたのと同じ結論をそのまま
  くり返さない。新しい一つの結論を必ず加える
- 標準では120〜260字程度、深く読むでは220〜450字程度の、1〜2段落の自然な日本語にする
Re-branch（これからの小さな再分岐）について：
- 各項目は、今すぐ想像できる、小さく具体的な一つの行動にする（「書く」「分ける」「比べる」「読む」
  「訪ねる」「再開する」「試す」「記録する」など、具体的な動詞で終える）
- 過去を巻き戻すような提案（元恋人への連絡、退職、即座の引っ越し、いまの関係を終わらせる、大きな
  金銭的決断、選ばなかった人生をそのまま再現すること）は書かない
- 「本当の自分」「癒やす」「手放す」「向き合う」「可能性を取り戻す」のような抽象的な言葉は、具体的な
  行動の説明なしに使わない
- 可能であれば、分岐の種類（進学・仕事・恋愛・場所や海外・創作・介護や家族など）に合わせた具体的な
  行動にする
Observatory Layer の title には、上記IDに対応する公式の英語名（例："Market Signals"）だけを入れ、
翻訳や音訳をしないこと。body の中で日本語の説明を書くことは問題ない。
次のJSONスキーマだけで、他の文章を含めずに答える：
{{"title": str, "subtitle": str, "branch_point": str, "chosen_path": str, "unchosen_life": str,
"lost": [str, ...3~6個], "protected": [str, ...3~6個], "residue": str,
"observatory_layers": [{{"id": str, "title": str, "body": str}}, ...],
"cross_lens_synthesis": str, "rebranch": [str, ...3~6個], "closing": str}}"""
        user_prompt = (
            f"書かれた分岐:\n{request.source_text}\n\n追加情報:\n{clar_block}\n\n"
            f"{facts_block}\n\n深さ: {depth}"
        )
    else:
        system_prompt = f"""You are Parallel Life (Kosuke Protocol). You read a life branch the user has
written as a single document, in the register of a private essay. Rules:
- No deterministic predictions, no diagnosis, no identifying details about third parties
- Describe the unchosen life only as a possibility (use "may have", "might have", "it is possible")
- Do not treat the chosen life as failure or compromise
- Do not treat Lost or Protected as morally superior to each other
- The Observatory Layer must select {n_lenses} lens IDs only from this set (no duplicates): {valid_ids}
- Respond in English only
- No advice, slogans, or "everything happens for a reason" language
Factual grounding (critical):
{facts_block}
- Never invert explicit polarity (accepted→rejected, stayed→left, quit→kept the job,
  married→did not marry, chose→did not choose, continued→stopped)
- Named institutions may be omitted for style, but their meaning must not be altered
  (do not replace admission to a named school with "went to another university")
- If polarity is unclear, do not invent a direction; use neutral language such as
  "At that time there was a major branch around education."
- Generate the title only after respecting these facts; never use a rejection-framed title
  for an admission fact
Style (important):
- Never describe the input as text ("the user wrote", "the input says", "the text says", "this
  sentence suggests"). Never re-quote the user's exact words in quotation marks. Write the branch
  directly as a finished document, consistent with the explicit facts (if admission is stated,
  do not narrate rejection; if rejection is stated, do not narrate admission).
- Avoid generic filler that could apply to any branch ("it cannot be known", "one possible life",
  "institutional, market, place-based, and historical conditions intersected", repeated in nearly
  identical form). Ground each section in at least one concrete element from the branch (age,
  place, relationship, work, education) when the information is available; do not invent facts.
- The title must be a grammatically complete phrase of 3-12 words, in natural title case, with no
  template fragments, no duplicated adjacent determiners (e.g. never "The that branch"), and no
  truncated words.
- Never use an ellipsis ("…" or "....") anywhere in the output.
Lost and Protected:
- Aim for 3-4 items in Standard depth and 4-5 in Deep depth (a guideline, not a fixed count). Lost
  and Protected do not need to have the same number of items.
- Do not list several items that restate the same underlying concept (e.g. "keeping options open",
  "keeping future possibilities", and "room to choose a different path" are the same concept —
  merge them into one stronger item). Each item should express exactly one concept, preferably as a
  concrete noun phrase.
- Do not mechanically mirror Lost and Protected (e.g. always pairing "freedom" against "stability")
  unless the branch genuinely supports that specific contrast.
Cross-Lens Synthesis:
- Do not open by listing the selected lens names ("Placed together, Education–Employment, Intimacy,
  and Book show..."). Lens names may appear, but the prose should be carried by the concrete domain
  each lens points to (the timing of a first job, the cost of housing, the shape of a close
  relationship, a story's form), not by the brand names.
- Avoid rigid, academic phrasing such as "placed together", "institutional, market, place-based, and
  historical conditions intersected", or "it was personal, but it was never produced by the
  individual alone", used verbatim.
- Add at least one conclusion not already stated in Branch Point, Chosen Path, Residue, or the
  individual Observatory Layer bodies — do not merely summarize the lens cards.
- Write one or two natural paragraphs: roughly 120-260 characters equivalent in Standard depth,
  220-450 in Deep depth (proportionally shorter or longer in English).
Re-branch:
- Each item is one small, concrete action the person can imagine doing now, beginning with a
  concrete verb (write, compare, visit, resume, try, record, name, reserve).
- Never suggest reversing the past: no contacting a former partner, quitting a job, moving
  immediately, ending a current relationship, a major financial decision, or recreating the
  unchosen life.
- Avoid abstract self-help language ("your true self", "heal", "let go", "confront the past",
  "reclaim your potential") unless made concrete by the rest of the sentence.
- Where possible, tailor items to the branch's category (education, work, relationship,
  place/overseas, creativity, care/family) rather than generic advice.
Observatory Layer "title" fields must contain only the official English lens name for that ID
(e.g. "Market Signals") — never translate or transliterate it. Write the explanatory content in
the "body" field.
Respond with ONLY this JSON schema, no other text:
{{"title": str, "subtitle": str, "branch_point": str, "chosen_path": str, "unchosen_life": str,
"lost": [str, ...3-6 items], "protected": [str, ...3-6 items], "residue": str,
"observatory_layers": [{{"id": str, "title": str, "body": str}}, ...],
"cross_lens_synthesis": str, "rebranch": [str, ...3-6 items], "closing": str}}"""
        user_prompt = (
            f"Written branch:\n{request.source_text}\n\nAdditional info:\n{clar_block}\n\n"
            f"{facts_block}\n\nDepth: {depth}"
        )

    return system_prompt, user_prompt


# --- LLM output safety nets: source-text leakage, truncation, title shape ---
#
# The heuristic generator is fully controlled and never produces these
# problems by construction, but the LLM path is freeform text, so it needs
# an explicit safety net. Any hit here raises, which triggers the existing
# retry-then-heuristic-fallback path in ``generate_parallel_life``.

_META_LANGUAGE_BANNED_EN = (
    "the branch appears inside", "the user wrote", "the input says",
    "this sentence suggests", "in the source text", 'the phrase "',
    "the user's statement is", "the user said", "the text says",
    "the user's input", "the input text", "the source text",
)
_META_LANGUAGE_BANNED_JA = (
    "という入力の中には", "入力の中には", "ユーザーが書いた", "本文には",
    "という文章の中には", "ユーザーの発言は", "入力されたテキスト", "ユーザーの入力",
)
_LONG_QUOTE_EN_RE = re.compile(r'"[^"]{18,}"')
_LONG_QUOTE_JA_RE = re.compile(r"「[^」]{18,}」")
_TRUNCATION_MARK_RE = re.compile(r"…|\.\.\.")


def _validate_no_leakage_or_truncation(texts: list[str], ja: bool) -> None:
    """Reject source-text meta-language, long quoted excerpts, and truncation
    markers ("…", "...") anywhere in the public document (editorial-quality
    pass §2, §3)."""
    banned = _META_LANGUAGE_BANNED_JA if ja else _META_LANGUAGE_BANNED_EN
    quote_re = _LONG_QUOTE_JA_RE if ja else _LONG_QUOTE_EN_RE
    for text in texts:
        if not text:
            continue
        lowered = text.lower()
        for phrase in banned:
            if phrase.lower() in lowered:
                raise ValueError(f"Source-text meta-language detected: {phrase!r}")
        if quote_re.search(text):
            raise ValueError("Long quoted excerpt detected in public output")
        if _TRUNCATION_MARK_RE.search(text):
            raise ValueError("Truncation marker detected in public output")


# --- LLM output safety nets: Cross-Lens Synthesis and Re-branch quality -----
#
# These catch the two failure modes an LLM can slip into even when its JSON
# is otherwise valid: a Cross-Lens Synthesis that is just a lens-name list
# wrapped in a stock academic sentence, and a Re-branch item that reverses
# the past or hides behind an abstract, unactionable placeholder.

_SYNTHESIS_RIGID_PHRASES_JA = (
    "制度・市場・場所・時代の条件が交差する場所で生まれていた",
    "個人的な経験でありながら、それは個人だけによってつくられたものではない",
    "制度的",
    "市場的",
    "が可視化される",
    "ということが分かる",
)
_SYNTHESIS_RIGID_PHRASES_EN = (
    "placed together,",
    "institutional, market, place-based, and historical conditions intersected",
    "it was personal, but it was never produced by the individual alone",
    "these lenses reveal",
)


def _validate_cross_lens_synthesis_quality(text: str, lens_names: list[str], ja: bool) -> None:
    """Reject a synthesis that is only a concatenation of lens names and a
    stock academic sentence (editorial-quality pass round 2, §2)."""
    banned = _SYNTHESIS_RIGID_PHRASES_JA if ja else _SYNTHESIS_RIGID_PHRASES_EN
    lowered = text.lower()
    for phrase in banned:
        if phrase.lower() in lowered:
            raise ValueError(f"Cross-Lens Synthesis uses a rigid fallback phrase: {phrase!r}")
    # A synthesis that is barely longer than "Name1, Name2, and Name3" plus
    # punctuation is not adding an insight beyond a lens-name list.
    names_len = sum(len(n) for n in lens_names)
    if len(text.strip()) < names_len + 40:
        raise ValueError("Cross-Lens Synthesis appears to be only a lens-name list")


_REBRANCH_BANNED_ACTIONS_JA = (
    "元恋人に連絡", "元カレに連絡", "元カノに連絡", "仕事を辞める", "退職する",
    "今の関係を終わらせる", "いまの関係を終わらせる", "今すぐ引っ越す", "大きな借金",
    "全財産を投じる", "元パートナーに連絡",
)
_REBRANCH_BANNED_ACTIONS_EN = (
    "contact your ex", "contact your former partner", "reach out to your ex",
    "quit your job", "end your current relationship", "move immediately",
    "take out a large loan", "invest your savings", "make a major financial decision",
)
_REBRANCH_ABSTRACT_PLACEHOLDER_JA = ("道が象徴していた「質」を、ひとつだけ名づけ",)
_REBRANCH_ABSTRACT_PLACEHOLDER_EN = (
    "the quality that the unchosen path seemed to represent",
    "the quality represented by the path",
)


def _validate_rebranch_items(items: list[str], ja: bool) -> None:
    """Reject Re-branch items that reverse the past or hide behind an
    abstract, unactionable placeholder (editorial-quality pass round 2, §3)."""
    banned_actions = _REBRANCH_BANNED_ACTIONS_JA if ja else _REBRANCH_BANNED_ACTIONS_EN
    placeholders = _REBRANCH_ABSTRACT_PLACEHOLDER_JA if ja else _REBRANCH_ABSTRACT_PLACEHOLDER_EN
    for item in items:
        lowered = item.lower()
        for phrase in banned_actions:
            if phrase.lower() in lowered:
                raise ValueError(f"Re-branch item suggests a discouraged action: {phrase!r}")
        for phrase in placeholders:
            if phrase.lower() in lowered:
                raise ValueError(f"Re-branch item is an abstract placeholder: {phrase!r}")


def _parse_and_validate_llm_output(
    content: str, request: ParallelLifeRequest
) -> ParallelLifeResult:
    ja = _is_ja(request.language, request.source_text)
    content = content.strip().strip("`")
    if content.lower().startswith("json"):
        content = content[4:].strip()
    data = json.loads(content)

    required = [
        "title",
        "subtitle",
        "branch_point",
        "chosen_path",
        "unchosen_life",
        "lost",
        "protected",
        "residue",
        "observatory_layers",
        "cross_lens_synthesis",
        "rebranch",
        "closing",
    ]
    for key in required:
        if key not in data:
            raise ValueError(f"Missing key in LLM output: {key}")

    lost = [_clean_line(x) for x in data["lost"] if str(x).strip()]
    protected = [_clean_line(x) for x in data["protected"] if str(x).strip()]
    rebranch = [_clean_line(x) for x in data["rebranch"] if str(x).strip()]

    # Semantic deduplication (editorial-quality pass round 2, §1): collapse
    # items that restate the same underlying concept before validating
    # length, so a verbose-but-repetitive LLM response cannot pass by volume
    # alone.
    lost = _dedupe_semantically(lost, ja)
    protected = _dedupe_semantically(protected, ja)

    if not (3 <= len(lost) <= 6):
        raise ValueError("lost must have 3-6 distinct items after deduplication")
    if not (3 <= len(protected) <= 6):
        raise ValueError("protected must have 3-6 distinct items after deduplication")
    if not (3 <= len(rebranch) <= 6):
        raise ValueError("rebranch must have 3-6 items")
    _validate_rebranch_items(rebranch, ja)

    raw_layers = data["observatory_layers"]
    if not isinstance(raw_layers, list) or not raw_layers:
        raise ValueError("observatory_layers must be a non-empty list")

    layer_ids = validate_lens_ids([str(item.get("id", "")) for item in raw_layers])
    if not (2 <= len(layer_ids) <= 4):
        raise ValueError("observatory_layers must resolve to 2-4 valid, unique lens ids")

    # Observatory Layer titles are always the official English lens name
    # (never translated or transliterated, editorial-quality pass §10) —
    # this is enforced here rather than trusted from the LLM's own "title"
    # field, so naming stays consistent regardless of what the model wrote.
    layers: list[ObservatoryLayer] = []
    for item in raw_layers:
        lid = str(item.get("id", ""))
        if lid not in layer_ids:
            continue
        lens_def = OBSERVATORY_LENSES[lid]
        body = _clean_line(str(item.get("body", "")))
        if not body:
            raise ValueError("observatory layer body must not be empty")
        layers.append(
            ObservatoryLayer(
                id=lid,
                title=lens_def.name_en,
                descriptor=lens_def.descriptor_ja if ja else lens_def.descriptor_en,
                body=body,
            )
        )

    for text_field in (
        data["title"],
        data["subtitle"],
        data["branch_point"],
        data["chosen_path"],
        data["unchosen_life"],
        data["residue"],
        data["cross_lens_synthesis"],
        data["closing"],
    ):
        if not str(text_field).strip():
            raise ValueError("empty required text field in LLM output")

    title = _clean_line(data["title"])
    title_valid = _is_valid_japanese_title(title) if ja else _is_valid_english_title(title)
    if not title_valid:
        raise ValueError(f"Generated title failed validation: {title!r}")

    result = ParallelLifeResult(
        title=title,
        subtitle=_clean_line(data["subtitle"]),
        branch_point=_clean_line(data["branch_point"]),
        chosen_path=_clean_line(data["chosen_path"]),
        unchosen_life=_clean_line(data["unchosen_life"]),
        lost=lost[:6],
        protected=protected[:6],
        residue=_clean_line(data["residue"]),
        observatory_layers=layers,
        cross_lens_synthesis=_clean_line(data["cross_lens_synthesis"]),
        rebranch=rebranch[:6],
        closing=_clean_line(data["closing"]),
        generation_mode="llm",
        language="ja" if ja else "en",
        depth=request.depth,
    )

    # Cross-Lens Synthesis quality safety net (editorial-quality pass round 2, §2).
    _validate_cross_lens_synthesis_quality(
        result.cross_lens_synthesis, [layer.title for layer in layers], ja
    )

    # Source-text leakage / truncation safety net (editorial-quality pass §2, §3).
    _validate_no_leakage_or_truncation(
        [
            result.title,
            result.subtitle,
            result.branch_point,
            result.chosen_path,
            result.unchosen_life,
            result.residue,
            result.cross_lens_synthesis,
            result.closing,
            *result.lost,
            *result.protected,
            *result.rebranch,
            *(layer.body for layer in result.observatory_layers),
        ],
        ja,
    )

    # Factual polarity / contradiction safety net — reject outputs that invert
    # explicit source facts (e.g. 受かった → 落ちた).
    from app.parallel_life_domain import (
        extract_grounded_primary_branch,
        validate_domain_consistency,
    )

    facts = extract_parallel_life_facts(request.source_text, request.clarifications, ja=ja)
    validate_factual_consistency(request.source_text, result, facts, ja=ja)
    grounded = extract_grounded_primary_branch(
        request.source_text, request.clarifications, None, ja=ja
    )
    validate_domain_consistency(result, grounded, ja=ja)

    # Language safeguard: never let an off-language LLM result through.
    all_text = " ".join(
        [
            result.title,
            result.subtitle,
            result.branch_point,
            result.chosen_path,
            result.unchosen_life,
            result.residue,
            result.cross_lens_synthesis,
            result.closing,
            *result.lost,
            *result.protected,
            *result.rebranch,
            *(layer.body for layer in result.observatory_layers),
        ]
    )
    if ja and not _has_cjk(all_text):
        raise ValueError("Expected Japanese output but found none")
    if not ja and _has_cjk(all_text):
        raise ValueError("Unexpected Japanese characters in English output")

    return result


async def _llm_parallel_life(request: ParallelLifeRequest, api_key: str) -> ParallelLifeResult:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    system_prompt, user_prompt = _build_llm_prompt(request)

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=2200 if request.depth == "deep" else 1200,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    return _parse_and_validate_llm_output(content, request)


async def generate_parallel_life(request: ParallelLifeRequest) -> ParallelLifeResult:
    """Generate a Parallel Life reading.

    Standard depth uses the existing Standard generator. Depth values
    ``editorial`` and legacy ``deep`` are routed to the Editorial Edition
    generator (a separate mode, not a longer Standard template).
    """
    from app.models import EditorialContext, ParallelLifeEditorialRequest
    from app.parallel_life_editorial import generate_editorial_parallel_life, normalize_depth

    if normalize_depth(request.depth) == "editorial":
        editorial_req = ParallelLifeEditorialRequest(
            source_text=request.source_text,
            clarifications=request.clarifications,
            editorial_context=EditorialContext(),
            language=request.language,
        )
        response = await generate_editorial_parallel_life(editorial_req)
        return response.result

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        for _ in range(2):
            try:
                return await _llm_parallel_life(request, api_key)
            except Exception:
                continue
    return _heuristic_parallel_life(request)


# --- Markdown export -----------------------------------------------------------


def export_parallel_life_markdown(result: ParallelLifeResult, created_at: str | None) -> str:
    """Export a Parallel Life reading as clean, publishable Markdown.

    Contains no system prompts, technical scores, provenance, or model names.
    """
    ja = result.language == "ja"
    lines: list[str] = []
    lines.append(f"# {result.title}")
    lines.append("")
    lines.append(f"## {result.subtitle}")
    lines.append("")
    if created_at:
        label = "日付" if ja else "Date"
        lines.append(f"*{label}: {created_at}*  ")
    from app.parallel_life_editorial import normalize_depth

    depth_norm = normalize_depth(result.depth)
    if ja:
        depth_label = (
            "編集版" if depth_norm == "editorial" else "標準"
        )
    else:
        depth_label = "Editorial" if depth_norm == "editorial" else "Standard"
    lines.append(f"*{'レンズ' if ja else 'Lens'}: Parallel Life*  ")
    lines.append(f"*{'深さ' if ja else 'Depth'}: {depth_label}*  ")
    lines.append(f"*{'言語' if ja else 'Language'}: {'日本語' if ja else 'English'}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append(f"## {'分岐点' if ja else 'Branch Point'}")
    lines.append("")
    lines.append(result.branch_point)
    lines.append("")

    lines.append(f"## {'選んだ人生' if ja else 'Chosen Path'}")
    lines.append("")
    lines.append(result.chosen_path)
    lines.append("")

    lines.append(f"## {'選ばなかった人生' if ja else 'Unchosen Life'}")
    lines.append("")
    lines.append(result.unchosen_life)
    lines.append("")

    lines.append(f"## {'失ったもの' if ja else 'Lost'}")
    lines.append("")
    for item in result.lost:
        lines.append(f"- {item}")
    lines.append("")

    lines.append(f"## {'守られたもの' if ja else 'Protected'}")
    lines.append("")
    for item in result.protected:
        lines.append(f"- {item}")
    lines.append("")

    lines.append(f"## {'今に残っているもの' if ja else 'Residue'}")
    lines.append("")
    lines.append(result.residue)
    lines.append("")

    lines.append(f"## {'社会との接続' if ja else 'Observatory Layer'}")
    lines.append("")
    for layer in result.observatory_layers:
        lines.append(f"### {layer.title}")
        lines.append("")
        if layer.descriptor:
            lines.append(f"*{layer.descriptor}*")
            lines.append("")
        lines.append(layer.body)
        lines.append("")

    lines.append(f"## {'レンズを重ねると見えること' if ja else 'What becomes visible across the lenses'}")
    lines.append("")
    lines.append(result.cross_lens_synthesis)
    lines.append("")

    lines.append(f"## {'これからの小さな再分岐' if ja else 'A Small Re-branch'}")
    lines.append("")
    for item in result.rebranch:
        lines.append(f"- {item}")
    lines.append("")

    lines.append(f"## {'結び' if ja else 'Closing'}")
    lines.append("")
    lines.append(result.closing)
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Parallel Life — Powered by Kosuke Protocol*")

    return "\n".join(lines)
