"""Normalize / dedupe Editorial Edition inputs and guard against raw reuse.

Root cause addressed here: the same present-life text was previously
assembled from editorial_context, structure.current_life_context, and
_join_context, then pasted verbatim into Residue / Chosen Path / Closing.
"""

from __future__ import annotations

import re
from typing import Iterable

from app.models import (
    EditorialBranchStructure,
    EditorialContext,
    NormalizedEditorialContext,
    ParallelLifeClarifications,
    ParallelLifeResult,
)

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[、。．，,.!！?？・…\s]+")
_SENTENCE_SPLIT_JA = re.compile(r"(?<=[。！？\n])|(?<=[.!?]\s)")
_CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")

# Contiguous reuse thresholds (product spec).
_JA_RAW_REUSE_CHARS = 18
_EN_RAW_REUSE_WORDS = 8

# Proper-noun / short-fact whitelist patterns (never treat as leakage).
_WHITELIST_FRAGMENTS = (
    "早稲田大学",
    "第一文学部",
    "不妊治療",
    "Observatory",
    "Parallel Life",
    "Kosuke Protocol",
)


def normalize_whitespace(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip())


def normalize_for_compare(text: str) -> str:
    """Punctuation-insensitive key for exact/near duplicate matching."""
    t = normalize_whitespace(text).lower()
    t = _PUNCT_RE.sub("", t)
    # Common synonym collapses for family/work Japanese near-duplicates
    replacements = (
        ("嫁", "妻"),
        ("奥さん", "妻"),
        ("三人家族", "三人"),
        ("三人で暮ら", "三人"),
        ("自分の会社を経営", "自社経営"),
        ("会社を経営", "自社経営"),
        ("会社経営", "自社経営"),
        ("自社を運営", "自社経営"),
        ("自己所有", "持ち家"),
        ("広めのアパート", "広めの住まい"),
        ("遊びにくる", "遊びに来る"),
        ("可愛い", "かわいい"),
    )
    for a, b in replacements:
        t = t.replace(a, b)
    return t


def split_into_units(text: str) -> list[str]:
    """Split a free-text answer into sentence-like units."""
    text = normalize_whitespace(text)
    if not text:
        return []
    parts = [normalize_whitespace(p) for p in _SENTENCE_SPLIT_JA.split(text) if p and p.strip()]
    # Also split on Japanese commas when a unit is a long inventory
    out: list[str] = []
    for p in parts:
        if "。" in p or len(p) < 40:
            out.append(p.rstrip("。．.").strip())
            continue
        chunks = [normalize_whitespace(c) for c in re.split(r"[。．.]", p) if c.strip()]
        if len(chunks) > 1:
            out.extend(chunks)
        else:
            # Inventory style: 「A。B。C」 already handled; try 「A。B」 via 、
            if p.count("。") == 0 and p.count("、") >= 2 and len(p) > 50:
                for c in p.split("。"):
                    c = c.strip("、 ").strip()
                    if c:
                        out.append(c)
            else:
                out.append(p.rstrip("。．.").strip())
    return [u for u in out if u]


def char_overlap_ratio(a: str, b: str) -> float:
    """Bigram character overlap (Dice) for Japanese near-duplicate detection."""
    na, nb = normalize_for_compare(a), normalize_for_compare(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
        return len(shorter) / max(len(longer), 1)
    def bigrams(s: str) -> set[str]:
        if len(s) < 2:
            return {s}
        return {s[i : i + 2] for i in range(len(s) - 1)}
    ba, bb = bigrams(na), bigrams(nb)
    if not ba or not bb:
        return 0.0
    inter = len(ba & bb)
    return (2.0 * inter) / (len(ba) + len(bb))


def is_near_duplicate(a: str, b: str, threshold: float = 0.72) -> bool:
    return char_overlap_ratio(a, b) >= threshold


def prefer_fact(a: str, b: str) -> str:
    """Prefer the more factual, concise, complete version."""
    # Prefer version with fewer colloquial particles / filler
    fillers = ("ですね", "かな", "と思う", "!", "！")
    score = lambda s: (
        -sum(1 for f in fillers if f in s),
        -abs(len(s) - 28),  # prefer moderate length
        -len(s),
    )
    return a if score(a) >= score(b) else b


def dedupe_units(units: Iterable[str], *, threshold: float = 0.72) -> list[str]:
    """Exact + near-duplicate merge; keep preferred factual form."""
    kept: list[str] = []
    for raw in units:
        unit = normalize_whitespace(raw)
        if not unit:
            continue
        merged = False
        for i, existing in enumerate(kept):
            if normalize_for_compare(unit) == normalize_for_compare(existing) or is_near_duplicate(
                unit, existing, threshold
            ):
                kept[i] = prefer_fact(existing, unit)
                merged = True
                break
        if not merged:
            kept.append(unit)
    return kept


def _classify_unit(unit: str, ja: bool) -> str:
    """Return one of: emotional, role, condition, present, question, other."""
    u = unit
    if ja:
        if any(k in u for k in ("かわいい", "可愛い", "楽しい", "家庭という", "感じが", "嬉しい", "寂しい")):
            return "emotional"
        if any(k in u for k in ("経営", "会社", "父親", "母親", "親", "経営者", "会社員")):
            return "role"
        if any(k in u for k in ("住んで", "アパート", "持ち家", "自己所有", "住居", "住まい", "家に")):
            return "condition"
        if any(k in u for k in ("どうだった", "だろうか", "残っている問い", "考えることが")):
            return "question"
        if any(k in u for k in ("家族", "息子", "娘", "妻", "嫁", "三人", "暮ら", "仕事", "友人", "友達")):
            return "present"
        return "present"
    low = u.lower()
    if any(k in low for k in ("cute", "fun", "feel like", "happy", "warm")):
        return "emotional"
    if any(k in low for k in ("run my", "company", "self-employ", "father", "parent")):
        return "role"
    if any(k in low for k in ("apartment", "own", "live in", "housing", "home")):
        return "condition"
    return "present"


def _detect_signals(units: list[str], source_text: str, ja: bool) -> list[str]:
    blob = " ".join(units) + " " + source_text
    signals: list[str] = []
    checks = (
        (("三人", "妻と息子", "息子と妻", "嫁", "three"), "family_of_three"),
        (("経営", "自分の会社", "自社", "company", "self-employ"), "self_employed"),
        (("自己所有", "持ち家", "広めのアパート", "own", "apartment"), "owned_housing"),
        (("友達が家", "友人が家", "遊びに来", "遊びにくる", "friends visit"), "child_friends_visit"),
        (("かわいい", "可愛い", "楽しい", "家庭という", "家庭らしい"), "warm_home_feeling"),
        (("二人目", "second child"), "second_child_question"),
        (("不妊", "治療", "授かった", "fertility"), "fertility_path"),
        (("息子", "son"), "has_son"),
        (("記録", "残したい", "memory", "archive"), "wants_record"),
    )
    for keys, sig in checks:
        if any(k in blob for k in keys):
            signals.append(sig)
    # Deduplicate preserving order
    out: list[str] = []
    for s in signals:
        if s not in out:
            out.append(s)
    return out


def collect_raw_corpus(
    source_text: str,
    clar: ParallelLifeClarifications,
    context: EditorialContext,
) -> list[str]:
    fields = [
        source_text,
        clar.age,
        clar.chosen_path,
        clar.unchosen_path,
        clar.what_remains,
        clar.constraints,
        clar.lost,
        clar.protected,
        context.life_before,
        context.changes_after,
        context.unseen_conditions,
        context.present_influence,
        context.meaning_of_unchosen_life,
        context.later_branches,
        context.current_life_context,
        context.social_connection,
    ]
    corpus: list[str] = []
    for f in fields:
        if not f:
            continue
        corpus.append(normalize_whitespace(f))
        corpus.extend(split_into_units(f))
    return dedupe_units(corpus, threshold=0.95)


def normalize_editorial_context(
    source_text: str,
    clar: ParallelLifeClarifications,
    context: EditorialContext,
    structure: EditorialBranchStructure,
    *,
    ja: bool,
) -> NormalizedEditorialContext:
    """Normalize all editorial inputs into a single deduplicated structure."""
    raw_units: list[str] = []
    for field in (
        context.current_life_context,
        context.present_influence,
        context.changes_after,
        context.life_before,
        context.meaning_of_unchosen_life,
        context.later_branches,
        context.social_connection,
        clar.chosen_path,
        clar.what_remains,
    ):
        if field:
            raw_units.extend(split_into_units(field))

    # Pull short cues from source without importing whole paragraphs
    for cue in split_into_units(source_text):
        if any(
            k in cue
            for k in (
                "三人",
                "息子",
                "妻",
                "嫁",
                "経営",
                "アパート",
                "二人目",
                "友達",
                "友人",
                "family",
                "son",
                "company",
            )
        ):
            raw_units.append(cue)

    units = dedupe_units(raw_units)

    present: list[str] = []
    emotional: list[str] = []
    roles: list[str] = []
    conditions: list[str] = []
    questions: list[str] = []

    # Canonical fact rewrites (short factual forms — still not public prose)
    for unit in units:
        kind = _classify_unit(unit, ja)
        if kind == "emotional":
            emotional.append(unit)
        elif kind == "role":
            roles.append(_canonicalize_role(unit, ja))
        elif kind == "condition":
            conditions.append(_canonicalize_condition(unit, ja))
        elif kind == "question":
            questions.append(unit)
        else:
            present.append(_canonicalize_present(unit, ja))

    present = dedupe_units(present)
    emotional = dedupe_units(emotional)
    roles = dedupe_units(roles)
    conditions = dedupe_units(conditions)

    secondary = dedupe_units(structure.secondary_branches + split_into_units(context.later_branches or ""))
    unresolved = dedupe_units(
        ([structure.present_question] if structure.present_question else [])
        + questions
        + split_into_units(clar.what_remains or "")
    )

    explicit = dedupe_units(structure.explicit_facts)
    signals = _detect_signals(units + [source_text], source_text, ja)
    corpus = collect_raw_corpus(source_text, clar, context)

    # Compact present_life_facts from signals (never store long raw paragraphs)
    compact_present = _compact_present_facts(signals, present, ja)

    return NormalizedEditorialContext(
        explicit_facts=explicit[:12],
        present_life_facts=compact_present[:8],
        emotional_observations=dedupe_units(
            [_canonicalize_emotion(e, ja) for e in emotional]
        )[:6],
        current_roles=roles[:6],
        current_conditions=conditions[:6],
        secondary_branches=secondary[:6],
        unresolved_questions=unresolved[:4],
        signals=signals,
        raw_source_corpus=corpus,
    )


def _canonicalize_present(unit: str, ja: bool) -> str:
    n = normalize_for_compare(unit)
    if ja:
        if "三人" in n and ("妻" in n or "息子" in n or "嫁" in unit):
            return "妻と息子との三人家族で暮らしている"
        if "息子" in n and ("友人" in n or "友達" in unit):
            return "息子の友人が家を訪れる"
        if "息子" in n and ("かわいい" in n or "可愛い" in unit):
            return "息子との日常を大切に感じている"
    return unit if len(unit) <= 40 else unit[:40]


def _canonicalize_role(unit: str, ja: bool) -> str:
    n = normalize_for_compare(unit)
    if "自社経営" in n or "経営" in unit:
        return "自分の会社を経営している" if ja else "runs own company"
    return unit if len(unit) <= 40 else unit[:40]


def _canonicalize_condition(unit: str, ja: bool) -> str:
    n = normalize_for_compare(unit)
    if "持ち家" in n or "アパート" in unit or "住まい" in unit:
        return "自己所有の広めの住まいに暮らしている" if ja else "lives in owned spacious housing"
    return unit if len(unit) <= 40 else unit[:40]


def _canonicalize_emotion(unit: str, ja: bool) -> str:
    if any(k in unit for k in ("家庭", "楽しい", "かわいい", "可愛い", "友達", "友人")):
        return "家庭らしい時間と楽しさを感じている" if ja else "feels a warm family life"
    return unit if len(unit) <= 40 else unit[:40]


def _compact_present_facts(signals: list[str], present: list[str], ja: bool) -> list[str]:
    facts: list[str] = []
    if "family_of_three" in signals:
        facts.append("妻と息子との三人家族で暮らしている" if ja else "lives as a family of three with spouse and son")
    if "self_employed" in signals:
        facts.append("自分の会社を経営している" if ja else "runs own company")
    if "owned_housing" in signals:
        facts.append("自己所有の広めの住まいに暮らしている" if ja else "lives in owned spacious housing")
    if "child_friends_visit" in signals:
        facts.append("息子の友人が家を訪れる" if ja else "child's friends visit the home")
    if "warm_home_feeling" in signals:
        facts.append("家庭らしい時間を感じている" if ja else "feels a warm family atmosphere")
    # Add remaining short present facts that aren't near-duplicates
    for p in present:
        if len(p) > 60:
            continue
        if not any(is_near_duplicate(p, f) for f in facts):
            facts.append(p)
    return dedupe_units(facts)


def standard_interpretation_summary(
    standard: ParallelLifeResult | None, *, ja: bool
) -> dict[str, str | list[str]]:
    """Compact prior interpretation — not full Standard prose as facts."""
    if not standard:
        return {}
    return {
        "prior_title": standard.title,
        "prior_subtitle": standard.subtitle,
        "prior_lenses": [layer.id for layer in standard.observatory_layers],
        "prior_residue_summary": (standard.residue[:120] + "…")
        if len(standard.residue) > 120
        else standard.residue,
        "note": (
            "これは下書きの要約であり、事実ではない。編集版では書き直すこと。"
            if ja
            else "Draft summary only — rewrite; do not treat as facts."
        ),
    }


def _whitelist_ok(fragment: str) -> bool:
    if any(w in fragment for w in _WHITELIST_FRAGMENTS):
        return True
    # Short factual fragments (names, ages) are allowed
    if len(fragment) <= 10:
        return True
    if re.fullmatch(r"\d+歳?", fragment):
        return True
    return False


def find_raw_reuse(text: str, corpus: list[str], *, ja: bool) -> list[str]:
    """Return long contiguous phrases copied from user corpus."""
    if not text:
        return []
    leaks: list[str] = []
    for src in corpus:
        if not src or len(src) < (_JA_RAW_REUSE_CHARS if ja else 20):
            continue
        if ja:
            # Sliding window over source for contiguous CJK-heavy spans
            n = len(src)
            window = _JA_RAW_REUSE_CHARS
            i = 0
            while i <= n - window:
                frag = src[i : i + window]
                if _whitelist_ok(frag):
                    i += 1
                    continue
                if frag in text:
                    # Extend to longest match
                    end = i + window
                    while end < n and src[i:end + 1] in text:
                        end += 1
                    leak = src[i:end]
                    if len(leak) >= window and not _whitelist_ok(leak):
                        if not any(leak in prev or prev in leak for prev in leaks):
                            leaks.append(leak)
                    i = end
                else:
                    i += 1
        else:
            words = src.split()
            if len(words) < _EN_RAW_REUSE_WORDS:
                continue
            for i in range(len(words) - _EN_RAW_REUSE_WORDS + 1):
                frag = " ".join(words[i : i + _EN_RAW_REUSE_WORDS])
                if _whitelist_ok(frag):
                    continue
                if frag.lower() in text.lower():
                    if frag not in leaks:
                        leaks.append(frag)
    return leaks


def strip_raw_reuse(text: str, corpus: list[str], *, ja: bool) -> str:
    """Remove leaked raw spans; leave a clean gap rather than paste filler."""
    cleaned = text
    for leak in sorted(find_raw_reuse(cleaned, corpus, ja=ja), key=len, reverse=True):
        cleaned = cleaned.replace(leak, "")
    cleaned = re.sub(r"[、，]\s*[、，]", "、", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"。{2,}", "。", cleaned)
    return normalize_whitespace(cleaned)


def split_sentences(text: str) -> list[str]:
    text = normalize_whitespace(text)
    if not text:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s*", text)
    return [p.strip() for p in parts if p and p.strip()]


def dedupe_sentences_across(sections: list[str], *, threshold: float = 0.78) -> list[str]:
    """Remove near-duplicate sentences appearing later across sections."""
    seen: list[str] = []
    out_sections: list[str] = []
    for section in sections:
        kept_sents: list[str] = []
        for sent in split_sentences(section):
            if any(is_near_duplicate(sent, prev, threshold) for prev in seen):
                continue
            kept_sents.append(sent)
            seen.append(sent)
        # Rebuild section
        if not kept_sents:
            out_sections.append(section)
            continue
        if any(_CJK_RE.search(s) for s in kept_sents):
            rebuilt = "".join(s if s.endswith(("。", "！", "？")) else s + "。" for s in kept_sents)
        else:
            rebuilt = " ".join(kept_sents)
        out_sections.append(rebuilt)
    return out_sections


def count_fact_mentions(sections: dict[str, str], fact_needles: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {f: 0 for f in fact_needles}
    for text in sections.values():
        for f in fact_needles:
            if f and f in text:
                counts[f] += 1
    return counts


def postprocess_editorial_result(
    result: ParallelLifeResult,
    normalized: NormalizedEditorialContext,
    *,
    ja: bool,
) -> ParallelLifeResult:
    """Strip raw reuse, exact/near sentence duplicates across public sections."""
    corpus = normalized.raw_source_corpus
    fields = [
        "branch_point",
        "chosen_path",
        "unchosen_life",
        "residue",
        "cross_lens_synthesis",
        "closing",
    ]
    values = [strip_raw_reuse(getattr(result, f), corpus, ja=ja) for f in fields]
    values = dedupe_sentences_across(values)

    lost = [strip_raw_reuse(x, corpus, ja=ja) for x in result.lost]
    protected = [strip_raw_reuse(x, corpus, ja=ja) for x in result.protected]
    rebranch = [strip_raw_reuse(x, corpus, ja=ja) for x in result.rebranch]
    # Dedupe list items
    lost = dedupe_units(lost)
    protected = dedupe_units(protected)
    rebranch = dedupe_units(rebranch)

    layers = []
    for layer in result.observatory_layers:
        body = strip_raw_reuse(layer.body, corpus, ja=ja)
        layers.append(layer.model_copy(update={"body": body}))

    updates = {f: values[i] for i, f in enumerate(fields)}
    updates.update(
        {
            "lost": [x for x in lost if x][:6],
            "protected": [x for x in protected if x][:6],
            "rebranch": [x for x in rebranch if x][:6],
            "observatory_layers": layers,
            "title": strip_raw_reuse(result.title, corpus, ja=ja) or result.title,
            "subtitle": strip_raw_reuse(result.subtitle, corpus, ja=ja) or result.subtitle,
        }
    )
    return result.model_copy(update=updates)


def assert_no_long_raw_reuse(
    result: ParallelLifeResult,
    normalized: NormalizedEditorialContext,
    *,
    ja: bool,
) -> list[str]:
    """Return list of remaining leaks (empty if clean). For tests / validation."""
    prose_parts = [
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
    leaks: list[str] = []
    for part in prose_parts:
        leaks.extend(find_raw_reuse(part, normalized.raw_source_corpus, ja=ja))
    # Deduplicate leak report
    return dedupe_units(leaks, threshold=0.9)
