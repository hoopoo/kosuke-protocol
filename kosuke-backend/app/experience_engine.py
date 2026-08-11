"""Experience Engine - meaning-generation helpers for the Protocol Experience.

This module contains the generation logic that is specific to the guided
``/experience`` flow:

- ``generate_fragments``: turn a user's raw input into 4-7 minimal thought units
  (explicit / inferred / theme), using an LLM when available and falling back to
  language-aware heuristics.
- ``generate_meaning``: distill a concise, one-line emergent meaning from a full
  session without overriding the user's own reflection.
- ``SEED_FRAGMENTS``: a small curated corpus used only as a sampling fallback
  when the ecosystem does not yet contain enough fragments.

It intentionally avoids importing the ChromaDB-backed stores so the heuristics
can be imported and unit-tested without the vector database.
"""

from __future__ import annotations

import os
import re
import uuid

from app.lenses import Lens, get_lens
from app.models import ExperienceFragment
from app.text_chunker import _split_sentences


# --- Theme lexicon (bilingual, lightweight) ---
# Maps a theme label to trigger keywords. Used only for heuristic fallback.
_THEME_LEXICON: dict[str, list[str]] = {
    "time": ["time", "past", "future", "again", "still", "yet", "時間", "過去", "未来", "まだ", "いつも"],
    "place": ["place", "home", "city", "room", "street", "場所", "街", "部屋", "故郷", "町"],
    "change": ["change", "changed", "different", "new", "leave", "変わ", "変化", "新しい", "離れ"],
    "freedom": ["free", "freedom", "choose", "escape", "自由", "選", "逃"],
    "uncertainty": ["maybe", "perhaps", "unsure", "question", "wonder", "かも", "だろう", "問い", "わからない"],
    "memory": ["remember", "memory", "forget", "recall", "覚え", "記憶", "忘れ", "思い出"],
    "connection": ["someone", "person", "together", "with", "us", "誰か", "人", "一緒", "つながり"],
    "loss": ["lost", "gone", "miss", "end", "失", "喪失", "終わ", "いなく"],
    "identity": ["myself", "who", "self", "become", "自分", "誰", "なりたい"],
    "choice": ["decision", "decide", "choice", "or", "選択", "決断", "決め"],
}

# Theme display text per language (concise noun phrases for "theme" fragments).
_THEME_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "time": "the weight of time",
        "place": "a place that stays",
        "change": "something changing",
        "freedom": "the shape of freedom",
        "uncertainty": "living with not-knowing",
        "memory": "what memory keeps",
        "connection": "the pull of another",
        "loss": "the shape of absence",
        "identity": "who you are becoming",
        "choice": "a choice not yet made",
        "meaning": "the search for meaning",
    },
    "ja": {
        "time": "時間の重さ",
        "place": "残りつづける場所",
        "change": "変わりつつある何か",
        "freedom": "自由のかたち",
        "uncertainty": "分からないままでいること",
        "memory": "記憶が手放さないもの",
        "connection": "だれかへの引力",
        "loss": "不在のかたち",
        "identity": "なりつつある自分",
        "choice": "まだ下していない選択",
        "meaning": "意味への問い",
    },
}

# Concise conceptual phrases for "inferred" fragments (what the words point to).
# Kept as short noun phrases rather than verbose sentences.
_INFERRED_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "time": "time left unfinished",
        "place": "a place you can't return to",
        "change": "something that changed",
        "freedom": "the weight of freedom",
        "uncertainty": "what stays undecided",
        "memory": "a memory you can't release",
        "connection": "someone's absence",
        "loss": "the shape of what's lost",
        "identity": "who you wanted to be",
        "choice": "the path not taken",
        "meaning": "something not yet named",
    },
    "ja": {
        "time": "終わっていない時間",
        "place": "帰れない場所",
        "change": "変わってしまった何か",
        "freedom": "自由の重さ",
        "uncertainty": "決められないこと",
        "memory": "手放せない記憶",
        "connection": "だれかの不在",
        "loss": "失ったものの形",
        "identity": "なりたかった自分",
        "choice": "選ばなかった可能性",
        "meaning": "言葉になっていないもの",
    },
}


def _is_japanese(language: str, text: str) -> bool:
    if language and language.lower().startswith("ja"):
        return True
    # Detect CJK characters as a fallback.
    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text))


def _clause_split(sentence: str, ja: bool) -> list[str]:
    """Split a sentence into smaller clauses for finer thought units."""
    if ja:
        parts = re.split(r"[、,]", sentence)
    else:
        parts = re.split(r"[,;]|\band\b|\bbut\b", sentence)
    return [p.strip() for p in parts if p and p.strip()]


def _trim(text: str, limit: int = 120) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _detect_themes(text: str, max_themes: int = 2) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for theme, keywords in _THEME_LEXICON.items():
        if any(kw.lower() in lowered for kw in keywords):
            hits.append(theme)
    if not hits:
        hits = ["uncertainty", "meaning"]
    return hits[:max_themes]


def _new_id() -> str:
    return f"ef-{uuid.uuid4().hex[:12]}"


def _heuristic_fragments(text: str, language: str, lens: Lens) -> list[ExperienceFragment]:
    ja = _is_japanese(language, text)
    fragments: list[ExperienceFragment] = []

    # --- Explicit fragments: derived directly from the user's own words ---
    sentences = _split_sentences(text) or [text.strip()]
    explicit_units: list[str] = []
    for sentence in sentences:
        clauses = _clause_split(sentence, ja)
        for clause in clauses:
            if len(clause) >= 4:
                explicit_units.append(_trim(clause))
        if not clauses and sentence.strip():
            explicit_units.append(_trim(sentence))

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for unit in explicit_units:
        if unit not in seen:
            seen.add(unit)
            deduped.append(unit)
    # Keep explicit fragments as the user's own words, but concise.
    explicit_units = [_trim(u, 48) for u in deduped[:3]] if deduped else [_trim(text, 48)]

    for unit in explicit_units:
        fragments.append(ExperienceFragment(id=_new_id(), text=unit, type="explicit"))

    themes = _detect_themes(text)
    inferred_map = _INFERRED_TEXT["ja" if ja else "en"]
    theme_text_map = _THEME_TEXT["ja" if ja else "en"]

    # --- Inferred fragments: concise concepts the words point toward ---
    used: set[str] = {f.text for f in fragments}
    for theme in themes:
        phrase = inferred_map.get(theme, theme)
        if phrase not in used:
            used.add(phrase)
            fragments.append(
                ExperienceFragment(id=_new_id(), text=phrase, type="inferred")
            )

    # --- Theme fragments: the background theme, as a short phrase ---
    for theme in themes:
        phrase = theme_text_map.get(theme, theme)
        if phrase not in used:
            used.add(phrase)
            fragments.append(
                ExperienceFragment(id=_new_id(), text=phrase, type="theme")
            )

    # Ensure at least 4 fragments with a concise fallback theme.
    if len(fragments) < 4:
        fallback = theme_text_map.get("meaning", "meaning")
        if fallback not in used:
            fragments.append(
                ExperienceFragment(id=_new_id(), text=fallback, type="theme")
            )
    return fragments[:7]


async def _llm_fragments(
    text: str, language: str, lens: Lens, api_key: str
) -> list[ExperienceFragment]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    ja = language.lower().startswith("ja")
    lang_instruction = (
        "Respond in Japanese only. Do not include any English."
        if ja
        else "Respond in English only."
    )
    focus = lens.focus_ja if ja else lens.focus_en

    system_prompt = (
        "You are the Fragment stage of Kosuke Protocol, an intelligence ecosystem "
        "for meaning generation. You turn a person's raw input into 4-7 minimal "
        "thought units. Do not interpret heavily or explain. Keep each fragment a "
        "concise noun phrase or a very short statement (not a full explanatory "
        "sentence).\n"
        f"The lens for this session focuses on: {focus}.\n"
        "Classify each fragment as one of:\n"
        "- explicit: taken almost directly from the person's own words\n"
        "- inferred: a quiet concept the words point toward, stated as a short phrase\n"
        "- theme: a single background theme, as a short phrase\n"
        f"{lang_instruction}"
    )
    user_prompt = (
        f'Input:\n"""{text}"""\n\n'
        "Return one fragment per line in exactly this format:\n"
        "TYPE | fragment text\n"
        "where TYPE is explicit, inferred, or theme. Return 4 to 7 lines only."
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=400,
    )
    content = response.choices[0].message.content or ""

    fragments: list[ExperienceFragment] = []
    for line in content.strip().split("\n"):
        line = line.strip().lstrip("-•").strip()
        if "|" not in line:
            continue
        raw_type, _, frag_text = line.partition("|")
        frag_type = raw_type.strip().lower()
        frag_text = frag_text.strip().strip('"').strip("「」")
        if frag_type not in ("explicit", "inferred", "theme"):
            frag_type = "inferred"
        if frag_text:
            fragments.append(
                ExperienceFragment(id=_new_id(), text=_trim(frag_text), type=frag_type)
            )

    if len(fragments) < 3:
        raise ValueError("LLM returned too few fragments")
    return fragments[:7]


async def generate_fragments(
    text: str, language: str = "en", lens_id: str | None = None
) -> list[ExperienceFragment]:
    """Generate 4-7 experience fragments from raw user input.

    Uses an LLM when ``OPENAI_API_KEY`` is set, otherwise falls back to
    language-aware heuristics. Always returns at least the heuristic result.
    """
    lens = get_lens(lens_id)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            return await _llm_fragments(text, language, lens, api_key)
        except Exception:
            pass
    return _heuristic_fragments(text, language, lens)


# --- Meaning generation ---


def _last_sentence(text: str) -> str:
    sentences = _split_sentences(text)
    if sentences:
        return sentences[-1].strip()
    return text.strip()


def _heuristic_meaning(
    reflection: str,
    tension: str,
    language: str,
    lens: Lens,
) -> str:
    """Distill a concise emergent meaning, echoing the user's own reflection.

    The heuristic never contradicts the reflection: it surfaces the user's own
    concluding line, or a neutral, open statement when no reflection exists.
    """
    reflection = (reflection or "").strip()
    # Respect the active language explicitly (do not guess from content alone).
    ja = language.lower().startswith("ja") or _is_japanese(language, reflection or tension)

    if reflection:
        candidate = _last_sentence(reflection)
        candidate = candidate.strip().strip('"').strip("「」")
        # In Japanese mode, only echo the reflection if it is actually Japanese;
        # otherwise fall through to a Japanese line so nothing English leaks.
        if candidate and not (ja and not _is_japanese("ja", candidate)):
            return _trim(candidate, 60)

    # No usable reflection: stay open rather than inventing meaning.
    return "意味は、まだ形になりつつある。" if ja else "The meaning is still forming."


async def _llm_meaning(
    source_text: str,
    original_text: str,
    sampled_text: str,
    tension: str,
    reflection: str,
    language: str,
    lens: Lens,
    api_key: str,
) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    ja = language.lower().startswith("ja")

    if ja:
        system_prompt = (
            "あなたは Kosuke Protocol の「意味」の段階です。省察から、立ちあらわれた"
            "意味をたった一行で書きます。守ること：\n"
            "- 一文だけ。できれば10〜40文字ほどの短さ。\n"
            "- その人自身の省察に根ざす。要約・助言・診断・スローガンにしない。\n"
            "- 二文にしない。かぎ括弧や引用符を使わない。\n"
            "- 日本語だけで書く。"
        )
        user_prompt = (
            f"書いたこと：{source_text}\n"
            f"断片A：{original_text}\n"
            f"断片B：{sampled_text}\n"
            f"緊張：{tension}\n"
            f"その人の省察：{reflection}\n\n"
            "立ちあらわれた意味（一行）："
        )
    else:
        system_prompt = (
            "You are the Meaning stage of Kosuke Protocol. You distill a single, "
            "concise line of emergent meaning from a reflection session. Rules:\n"
            "- Output exactly one short line (aphoristic, one sentence).\n"
            "- Build on the person's own reflection; never contradict or override it.\n"
            "- No summary, advice, diagnosis, or slogan.\n"
            "- Do not add a second sentence, do not use quotation marks.\n"
            "- Respond in English only."
        )
        user_prompt = (
            f"Source: {source_text}\n"
            f"Fragment A: {original_text}\n"
            f"Fragment B: {sampled_text}\n"
            f"Tension: {tension}\n"
            f"The person's reflection: {reflection}\n\n"
            "Emergent meaning (one line):"
        )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=60,
    )
    content = (response.choices[0].message.content or "").strip()
    content = content.splitlines()[0] if content else ""
    content = content.strip().strip('"').strip("“”").strip("「」")
    if not content:
        raise ValueError("LLM returned empty meaning")
    return _trim(content, 80)


async def generate_meaning(
    source_text: str,
    original_text: str,
    sampled_text: str,
    tension: str,
    reflection: str,
    language: str = "en",
    lens_id: str | None = None,
) -> str:
    """Generate a concise, one-line emergent meaning for the session.

    Uses an LLM when available; otherwise echoes the user's own concluding line.
    Never overrides the user's reflection.
    """
    lens = get_lens(lens_id)
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            meaning = await _llm_meaning(
                source_text,
                original_text,
                sampled_text,
                tension,
                reflection,
                language,
                lens,
                api_key,
            )
            # Language safeguard: never return English in Japanese mode.
            if language.lower().startswith("ja") and not _is_japanese("ja", meaning):
                return _heuristic_meaning(reflection, tension, language, lens)
            return meaning
        except Exception:
            pass
    return _heuristic_meaning(reflection, tension, language, lens)


# --- Seed corpus (sampling fallback only) ---
# Used only when the ecosystem has too few fragments in the active language to
# sample a meaningful counterpart. Curated to span domains so flukes stay
# productive, and separated by language so a session never mixes languages.
SEED_FRAGMENTS_EN: list[dict[str, str]] = [
    {"text": "A city breathes differently at night, as if it were another creature.", "domain": "urban"},
    {"text": "The body remembers what the mind has agreed to forget.", "domain": "body"},
    {"text": "Every optimization quietly decides what is allowed to be lost.", "domain": "technology"},
    {"text": "A river does not choose its direction, yet it is never lost.", "domain": "nature"},
    {"text": "Silence is not the absence of sound but the presence of attention.", "domain": "philosophy"},
    {"text": "We build maps to feel less afraid of the territory.", "domain": "psychology"},
    {"text": "A door remembers everyone who hesitated before opening it.", "domain": "literature"},
    {"text": "Freedom without rhythm becomes only another kind of noise.", "domain": "music"},
    {"text": "The market prices everything except the reason we wanted it.", "domain": "economics"},
    {"text": "A photograph keeps the light but loses the weather.", "domain": "art"},
    {"text": "Distance is a form of intimacy we refuse to name.", "domain": "philosophy"},
    {"text": "Machines wait patiently for us to become predictable.", "domain": "technology"},
    {"text": "Grief is love that has nowhere left to arrive.", "domain": "psychology"},
    {"text": "A seed contains a forest it will never see.", "domain": "nature"},
    {"text": "The street knows your name only after you have left it.", "domain": "urban"},
    {"text": "Certainty is a small room with a beautiful view of one wall.", "domain": "philosophy"},
    {"text": "The hand learns the shape of a tool the mind cannot describe.", "domain": "body"},
    {"text": "Every ending rehearses a beginning it cannot remember.", "domain": "literature"},
]

SEED_FRAGMENTS_JA: list[dict[str, str]] = [
    {"text": "夜の街は、昼とは別の生きもののように息をしている。", "domain": "urban"},
    {"text": "頭が忘れたことを、からだは覚えている。", "domain": "body"},
    {"text": "効率は、何を失っていいかを静かに決めている。", "domain": "technology"},
    {"text": "川は行き先を選ばないのに、迷うことがない。", "domain": "nature"},
    {"text": "静けさは、音がないことではなく、注意があることだ。", "domain": "philosophy"},
    {"text": "地図をつくるのは、未知をすこし怖くなくするためだ。", "domain": "psychology"},
    {"text": "扉は、開ける前にためらった人をみな覚えている。", "domain": "literature"},
    {"text": "リズムのない自由は、ただの騒がしさになる。", "domain": "music"},
    {"text": "市場は、欲しかった理由だけには値をつけられない。", "domain": "economics"},
    {"text": "写真は光を残すが、その日の天気は残せない。", "domain": "art"},
    {"text": "距離は、名づけたくない親しさのかたちだ。", "domain": "philosophy"},
    {"text": "機械は、わたしたちが予測可能になるのを待っている。", "domain": "technology"},
    {"text": "悲しみは、届く先を失った愛だ。", "domain": "psychology"},
    {"text": "種のなかには、自分では見られない森がある。", "domain": "nature"},
    {"text": "通りは、あなたが去ってから名前を覚える。", "domain": "urban"},
    {"text": "確信とは、一枚の壁だけが美しく見える小さな部屋だ。", "domain": "philosophy"},
    {"text": "手は、頭では説明できない道具のかたちを覚える。", "domain": "body"},
    {"text": "終わりはいつも、思い出せない始まりをなぞっている。", "domain": "literature"},
]

# Backwards-compatible default (English corpus).
SEED_FRAGMENTS = SEED_FRAGMENTS_EN


def get_seed_fragments(language: str) -> list[dict[str, str]]:
    """Return the seed corpus for the active language."""
    return SEED_FRAGMENTS_JA if (language or "").lower().startswith("ja") else SEED_FRAGMENTS_EN
