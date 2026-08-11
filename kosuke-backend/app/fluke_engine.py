"""Fluke Engine - the core of Kosuke Protocol.

Generates unexpected but meaningful conceptual connections between fragments.

FlukeScore = 0.35 * Distance + 0.30 * CoreResonance + 0.20 * Tension + 0.15 * ContextFit

Upgrade: Domain-crossing prioritization, serendipity (20% random pairing),
and slow mode for deeper reflection.
"""

import math
import os
import random
from typing import Optional

from app.fragment_store import FragmentStore
from app.models import Fragment, FlukeResult, SlowModeConfig, SlowModeStatus
from app.sampling_engine import SamplingEngine

# Serendipity rate: 20% of flukes use random pairing
SERENDIPITY_RATE = 0.20

# Core concepts that define the Kosuke Protocol's thematic universe
CORE_TAGS = [
    "boundary",
    "uncertainty",
    "sampling",
    "body",
    "city",
    "death",
    "eros",
    "publicness",
    "fragility",
    "meaning",
]

# Productive tension pairs - concepts that generate insight when juxtaposed
TENSION_PAIRS = [
    ("AI", "body"),
    ("optimization", "uncertainty"),
    ("technology", "fragility"),
    ("market", "publicness"),
    ("algorithm", "intuition"),
    ("digital", "embodied"),
    ("efficiency", "meaning"),
    ("automation", "reflection"),
    ("data", "experience"),
    ("speed", "slowness"),
    ("system", "chaos"),
    ("control", "freedom"),
    ("machine", "human"),
    ("logic", "emotion"),
    ("global", "local"),
]


def _compute_distance(store: FragmentStore, frag_a: Fragment, frag_b: Fragment) -> float:
    """Compute semantic distance between two fragments (0-1 scale)."""
    embeddings = store.get_embeddings([frag_a.id, frag_b.id])
    if frag_a.id not in embeddings or frag_b.id not in embeddings:
        return 0.5  # default moderate distance

    emb_a = embeddings[frag_a.id]
    emb_b = embeddings[frag_b.id]

    dot = sum(x * y for x, y in zip(emb_a, emb_b))
    norm_a = math.sqrt(sum(x * x for x in emb_a))
    norm_b = math.sqrt(sum(x * x for x in emb_b))

    if norm_a == 0 or norm_b == 0:
        return 1.0

    similarity = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, 1.0 - similarity))


def _compute_core_resonance(frag_a: Fragment, frag_b: Fragment) -> float:
    """Measure how much the fragment pair resonates with core Kosuke concepts."""
    combined_text = (frag_a.text + " " + frag_b.text).lower()
    combined_tags = set(frag_a.tags + frag_b.tags)

    score = 0.0
    matches = 0

    for tag in CORE_TAGS:
        if tag in combined_text or tag in combined_tags:
            matches += 1

    # Normalize: ideal is 2-4 core resonances, not too many (oversaturated)
    if matches == 0:
        score = 0.1
    elif matches <= 2:
        score = 0.5 + (matches * 0.15)
    elif matches <= 4:
        score = 0.8 + ((matches - 2) * 0.05)
    else:
        score = 0.9  # cap to avoid oversaturation

    return min(1.0, score)


def _compute_tension_score(frag_a: Fragment, frag_b: Fragment) -> float:
    """Measure productive contradiction potential between fragments."""
    text_a = frag_a.text.lower()
    text_b = frag_b.text.lower()

    tension_count = 0
    for concept_x, concept_y in TENSION_PAIRS:
        cx = concept_x.lower()
        cy = concept_y.lower()
        # Check if one concept appears in A and the other in B (or vice versa)
        if (cx in text_a and cy in text_b) or (cy in text_a and cx in text_b):
            tension_count += 1

    # Also check tag-based tension
    tags_a = set(t.lower() for t in frag_a.tags)
    tags_b = set(t.lower() for t in frag_b.tags)
    for concept_x, concept_y in TENSION_PAIRS:
        cx = concept_x.lower()
        cy = concept_y.lower()
        if (cx in tags_a and cy in tags_b) or (cy in tags_a and cx in tags_b):
            tension_count += 1

    if tension_count == 0:
        return 0.2  # base tension from any juxtaposition
    elif tension_count == 1:
        return 0.6
    elif tension_count == 2:
        return 0.8
    else:
        return 0.95


def _compute_context_fit(
    frag_a: Fragment, frag_b: Fragment, query: str | None
) -> float:
    """Measure relevance to user's current exploration context."""
    if not query:
        return 0.5  # neutral when no context

    query_lower = query.lower()
    text_a = frag_a.text.lower()
    text_b = frag_b.text.lower()

    # Simple word overlap as context fit proxy
    query_words = set(query_lower.split())
    text_words_a = set(text_a.split())
    text_words_b = set(text_b.split())

    overlap_a = len(query_words & text_words_a)
    overlap_b = len(query_words & text_words_b)

    total_overlap = overlap_a + overlap_b
    max_possible = len(query_words) * 2

    if max_possible == 0:
        return 0.5

    return min(1.0, total_overlap / max_possible)


def _compute_domain_crossing(frag_a: Fragment, frag_b: Fragment) -> float:
    """Compute domain crossing bonus.

    Returns 1.0 if fragments are from different domains,
    0.5 if one has a domain and the other doesn't,
    0.0 if same domain or neither has a domain.
    """
    domain_a = frag_a.domain
    domain_b = frag_b.domain

    if domain_a and domain_b:
        return 1.0 if domain_a != domain_b else 0.0
    if domain_a or domain_b:
        return 0.5  # one has domain, one doesn't
    return 0.0  # neither has a domain


def compute_fluke_score(
    store: FragmentStore,
    frag_a: Fragment,
    frag_b: Fragment,
    query: str | None = None,
) -> dict[str, float]:
    """Compute the full fluke score for a fragment pair.

    FlukeScore = 0.35 * Distance + 0.30 * CoreResonance + 0.20 * Tension + 0.15 * ContextFit
    Domain crossing is tracked separately as a bonus indicator.
    """
    distance = _compute_distance(store, frag_a, frag_b)
    core_resonance = _compute_core_resonance(frag_a, frag_b)
    tension = _compute_tension_score(frag_a, frag_b)
    context_fit = _compute_context_fit(frag_a, frag_b, query)
    domain_crossing = _compute_domain_crossing(frag_a, frag_b)

    fluke_score = (
        0.35 * distance
        + 0.30 * core_resonance
        + 0.20 * tension
        + 0.15 * context_fit
    )

    return {
        "distance": round(distance, 4),
        "core_resonance": round(core_resonance, 4),
        "tension_score": round(tension, 4),
        "context_fit": round(context_fit, 4),
        "domain_crossing": round(domain_crossing, 4),
        "fluke_score": round(fluke_score, 4),
    }


def _is_ja(language: str | None) -> bool:
    return bool(language) and language.lower().startswith("ja")


def _has_cjk(text: str) -> bool:
    import re

    return bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", text))


def _snippet(text: str, limit: int = 26) -> str:
    """A short, quotable snippet of a fragment."""
    text = text.strip().strip('"').strip("“”").strip("「」")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


async def generate_tension_and_prompt(
    frag_a: Fragment,
    frag_b: Fragment,
    query: str | None = None,
    language: str = "en",
) -> tuple[str, str]:
    """Generate tension analysis and reflection prompt using LLM.

    Falls back to heuristic generation if OpenAI is not available. When the
    language is Japanese, an English LLM result is discarded in favor of the
    Japanese heuristic so no English template ever leaks through.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")

    if api_key:
        try:
            tension, prompt = await _llm_generate(frag_a, frag_b, query, api_key, language)
            # Language safeguard: never return English text in Japanese mode.
            if _is_ja(language) and (not _has_cjk(tension) or not _has_cjk(prompt)):
                return _heuristic_generate(frag_a, frag_b, language)
            return tension, prompt
        except Exception:
            pass

    # Fallback: heuristic generation
    return _heuristic_generate(frag_a, frag_b, language)


async def _llm_generate(
    frag_a: Fragment,
    frag_b: Fragment,
    query: str | None,
    api_key: str,
    language: str = "en",
) -> tuple[str, str]:
    """Generate tension and prompt using OpenAI."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    ja = _is_ja(language)

    if ja:
        context_str = f"\nいま向き合っていること：{query}" if query else ""
        system_prompt = """あなたは Kosuke Protocol の一部として、二つの断片のあいだにある静かな緊張を見つけ、問いを立てます。
守ること：
- 二つの断片に固有の、具体的な緊張を書く
- 自然で落ち着いた日本語で書く（翻訳調にしない）
- 「境界」「様式」「交差」「共鳴」などの抽象語や専門用語を使わない
- 励ましやスローガンにしない
- 緊張は1〜3の短い文、問いは1文にする
- すべて日本語で答える"""
        user_prompt = f"""断片A：「{frag_a.text}」

断片B：「{frag_b.text}」
{context_str}

次の形式で、日本語だけで答えてください：
TENSION: （二つの断片のあいだにある緊張。1〜3の短い文）
PROMPT: （そこから生まれる問い。1文）"""
    else:
        context_str = f"\nThe person is exploring: {query}" if query else ""
        system_prompt = """You are part of Kosuke Protocol. You find the quiet tension between two fragments and pose a question.
Rules:
- Write a specific tension particular to these two fragments
- Use plain, calm language; avoid jargon (boundary, mode, intersection, resonance)
- No encouragement or slogans
- Tension: one to three short sentences. Question: one sentence.
- Respond in English only."""
        user_prompt = f"""Fragment A: "{frag_a.text}"

Fragment B: "{frag_b.text}"
{context_str}

Respond in English only, in exactly this format:
TENSION: [the tension between the two fragments, one to three short sentences]
PROMPT: [one question that emerges]"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=220,
    )

    content = response.choices[0].message.content or ""

    tension = ""
    prompt = ""

    for line in content.strip().split("\n"):
        line = line.strip()
        if line.startswith("TENSION:"):
            tension = line[len("TENSION:"):].strip()
        elif line.startswith("PROMPT:"):
            prompt = line[len("PROMPT:"):].strip()

    if not tension or not prompt:
        return _heuristic_generate(frag_a, frag_b, language)

    return tension, prompt


# Native heuristic templates (no word-for-word translation between languages).
_JA_TENSION_PATTERNS = [
    "「{a}」と「{b}」。\nこの二つは、どこかで同じことを指しているのかもしれません。",
    "「{a}」のとなりに「{b}」を置くと、まだ終わっていない何かが浮かびます。",
    "「{a}」と「{b}」は、遠いようでいて、静かにつながっています。",
    "「{a}」を見つめていると、その裏側に「{b}」があることに気づきます。",
]
_JA_PROMPT_POOL = [
    "この二つを結んでいるものは、何だと思いますか。",
    "片方だけを見ていたときには、気づかなかったことはありますか。",
    "あなたにとって、どちらがより本当のことですか。",
    "この二つが同じものだとしたら、それは何でしょうか。",
    "いま、ここから動かせるものはありますか。",
]
_EN_TENSION_PATTERNS = [
    "“{a}” and “{b}”.\nThe two may be pointing at the same unfinished thing.",
    "Placing “{a}” beside “{b}”, something not yet resolved comes into view.",
    "“{a}” and “{b}” feel far apart, yet they quietly hold together.",
    "Looking at “{a}”, you notice “{b}” waiting behind it.",
]
_EN_PROMPT_POOL = [
    "What do you think connects these two?",
    "Is there something you missed while looking at only one of them?",
    "Which of the two feels more true to you?",
    "If these two were the same thing, what would it be?",
    "Is there anything here you can move, right now?",
]


def _heuristic_generate(
    frag_a: Fragment, frag_b: Fragment, language: str = "en"
) -> tuple[str, str]:
    """Generate tension and prompt without an LLM, natively per language."""
    import hashlib

    ja = _is_ja(language)
    snippet_a = _snippet(frag_a.text)
    snippet_b = _snippet(frag_b.text)

    hash_val = int(hashlib.md5((frag_a.id + frag_b.id).encode()).hexdigest(), 16)

    if ja:
        tension = _JA_TENSION_PATTERNS[hash_val % len(_JA_TENSION_PATTERNS)].format(
            a=snippet_a, b=snippet_b
        )
        prompt = _JA_PROMPT_POOL[(hash_val // 7) % len(_JA_PROMPT_POOL)]
    else:
        tension = _EN_TENSION_PATTERNS[hash_val % len(_EN_TENSION_PATTERNS)].format(
            a=snippet_a, b=snippet_b
        )
        prompt = _EN_PROMPT_POOL[(hash_val // 7) % len(_EN_PROMPT_POOL)]

    return tension, prompt


class SlowModeTracker:
    """Tracks fluke generation per session for slow mode."""

    def __init__(self, config: SlowModeConfig | None = None) -> None:
        self.config = config or SlowModeConfig()
        self._session_counts: dict[str, int] = {}

    def can_generate(self, session_id: str) -> bool:
        """Check if the session can generate more flukes."""
        if not self.config.enabled:
            return True
        count = self._session_counts.get(session_id, 0)
        return count < self.config.max_flukes_per_session

    def record_generation(self, session_id: str) -> None:
        """Record a fluke generation for the session."""
        self._session_counts[session_id] = self._session_counts.get(session_id, 0) + 1

    def get_status(self, session_id: str) -> SlowModeStatus:
        """Get the slow mode status for a session."""
        generated = self._session_counts.get(session_id, 0)
        remaining = max(0, self.config.max_flukes_per_session - generated)
        cooldown = remaining == 0 and self.config.enabled

        return SlowModeStatus(
            enabled=self.config.enabled,
            flukes_remaining=remaining,
            flukes_generated=generated,
            max_flukes=self.config.max_flukes_per_session,
            cooldown_active=cooldown,
            message=self.config.cooldown_message if cooldown else None,
        )

    def reset_session(self, session_id: str) -> None:
        """Reset the fluke count for a session."""
        self._session_counts.pop(session_id, None)

    def update_config(self, config: SlowModeConfig) -> None:
        """Update the slow mode configuration."""
        self.config = config


async def generate_fluke(
    store: FragmentStore,
    sampling_engine: SamplingEngine,
    query: str | None = None,
    n_candidates: int = 10,
    language: str = "en",
) -> FlukeResult | None:
    """Generate a single fluke - the core operation of Kosuke Protocol.

    Pairing strategy:
    - 20% serendipity: completely random pair (encourages unexpected connections)
    - 80% domain-crossing: prioritize pairs from different domains,
      falling back to distant pair sampling if domains aren't available
    """
    if store.count() < 2:
        return None

    # Determine generation method
    roll = random.random()
    generation_method = "standard"

    if roll < SERENDIPITY_RATE:
        # Serendipity: random pair
        generation_method = "serendipity"
        pair = sampling_engine.sample_random_pair()
    else:
        # Domain-crossing: prioritize cross-domain pairs
        generation_method = "domain_cross"
        pair = sampling_engine.sample_domain_crossing_pair(n_candidates)

    # Fallback to distant pair if needed
    if not pair:
        generation_method = "standard"
        pair = sampling_engine.sample_distant_pair(n_candidates)

    if not pair:
        return None

    frag_a, frag_b = pair

    # Compute fluke score
    scores = compute_fluke_score(store, frag_a, frag_b, query)

    # Generate tension and reflection prompt
    tension, reflection_prompt = await generate_tension_and_prompt(
        frag_a, frag_b, query, language
    )

    return FlukeResult(
        fragment_a=frag_a,
        fragment_b=frag_b,
        distance=scores["distance"],
        core_resonance=scores["core_resonance"],
        tension_score=scores["tension_score"],
        context_fit=scores["context_fit"],
        domain_crossing=scores["domain_crossing"],
        fluke_score=scores["fluke_score"],
        tension=tension,
        reflection_prompt=reflection_prompt,
        generation_method=generation_method,
    )
