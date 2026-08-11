"""Deep Reading v1.1-exp Context Pack (experimental).

Production v1.0.2 Strict path ignores this module unless Contextual mode is
explicitly enabled and an approved pack is supplied.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.parallel_life_deep_reading.models import (
    FactBoundaryType,
    GroundedFact,
    GroundedInput,
)

# Active Contextual pins — v1.1.0-rc1 freeze (Contextual beta not production-public).
CALL_1_PROMPT_VERSION_V11 = "parallel-life-call-1-v1.1.9"
RUNTIME_VERSION_V11_EXP = "parallel-life-runtime-v1.1.11"
CALL_1_PROMPT_VERSION_V119 = "parallel-life-call-1-v1.1.9-exp"
RUNTIME_VERSION_V119_EXP = "parallel-life-runtime-v1.1.9-exp"
CALL_1_PROMPT_VERSION_V1110 = "parallel-life-call-1-v1.1.9-exp"
RUNTIME_VERSION_V1110_EXP = "parallel-life-runtime-v1.1.10-exp"
CALL_1_PROMPT_VERSION_V1111 = "parallel-life-call-1-v1.1.9"
RUNTIME_VERSION_V1111_EXP = "parallel-life-runtime-v1.1.11"
# Prior Contextual baselines (kept for A/B artifact comparison labels).
CALL_1_PROMPT_VERSION_V11_BASELINE = "parallel-life-call-1-v1.1.0"
RUNTIME_VERSION_V11_BASELINE = "parallel-life-runtime-v1.1.0-exp"
CALL_1_PROMPT_VERSION_V111 = "parallel-life-call-1-v1.1.1"
RUNTIME_VERSION_V111_EXP = "parallel-life-runtime-v1.1.1-exp"
CALL_1_PROMPT_VERSION_V112 = "parallel-life-call-1-v1.1.2-exp"
RUNTIME_VERSION_V112_EXP = "parallel-life-runtime-v1.1.2-exp"
CALL_1_PROMPT_VERSION_V113 = "parallel-life-call-1-v1.1.3-exp"
RUNTIME_VERSION_V113_EXP = "parallel-life-runtime-v1.1.3-exp"
CALL_1_PROMPT_VERSION_V114 = "parallel-life-call-1-v1.1.4-exp"
RUNTIME_VERSION_V114_EXP = "parallel-life-runtime-v1.1.4-exp"
CALL_1_PROMPT_VERSION_V115 = "parallel-life-call-1-v1.1.5-exp"
RUNTIME_VERSION_V115_EXP = "parallel-life-runtime-v1.1.5-exp"
CALL_1_PROMPT_VERSION_V116 = "parallel-life-call-1-v1.1.6-exp"
RUNTIME_VERSION_V116_EXP = "parallel-life-runtime-v1.1.6-exp"
CALL_1_PROMPT_VERSION_V117 = "parallel-life-call-1-v1.1.7-exp"
RUNTIME_VERSION_V117_EXP = "parallel-life-runtime-v1.1.7-exp"
CALL_1_PROMPT_VERSION_V118 = "parallel-life-call-1-v1.1.8-exp"
RUNTIME_VERSION_V118_EXP = "parallel-life-runtime-v1.1.8-exp"


class DeepReadingMode(str, Enum):
    strict = "strict"
    contextual = "contextual"


class ContextPackCategory(str, Enum):
    career_history = "career_history"
    family_context = "family_context"
    current_work = "current_work"
    current_projects = "current_projects"
    current_creative_activity = "current_creative_activity"
    current_values = "current_values"
    major_life_events = "major_life_events"
    relevant_domains = "relevant_domains"
    user_self_definitions = "user_self_definitions"
    relevant_social_context = "relevant_social_context"


class ContextPackItemSource(str, Enum):
    user_typed = "user_typed"
    user_pasted = "user_pasted"
    seeded_from_same_session_text = "seeded_from_same_session_text"
    user_edited_seed = "user_edited_seed"


class ContextPackTimeSpan(BaseModel):
    start: str = ""
    end: str = ""
    precision: Literal["year", "period", "unknown"] = "unknown"


class ContextPackItem(BaseModel):
    id: str = ""
    content: str = ""
    category: ContextPackCategory = ContextPackCategory.current_work
    source: ContextPackItemSource = ContextPackItemSource.user_typed
    confidence: float = 1.0
    approved: bool = False
    allowed_for_fact: bool = True
    allowed_for_interpretation: bool = True
    time_span: ContextPackTimeSpan = Field(default_factory=ContextPackTimeSpan)
    chronology_rank: int = 0
    tags: list[str] = Field(default_factory=list)


class ContextPack(BaseModel):
    pack_id: str = ""
    mode_intent: DeepReadingMode = DeepReadingMode.strict
    source: Literal["user_authored", "session_seeded_draft", "imported_paste"] = (
        "user_authored"
    )
    created_at: str = ""
    updated_at: str = ""
    approved_by_user: bool = False
    approved_at: Optional[str] = None
    language: str = "ja"
    items: list[ContextPackItem] = Field(default_factory=list)
    rejected_or_deleted_ids: list[str] = Field(default_factory=list)


INTERPRETATION_ONLY_CATEGORIES = frozenset(
    {
        ContextPackCategory.current_values,
        ContextPackCategory.user_self_definitions,
    }
)

PAST_CATEGORIES = frozenset(
    {
        ContextPackCategory.career_history,
        ContextPackCategory.major_life_events,
    }
)

PRESENT_CATEGORIES = frozenset(
    {
        ContextPackCategory.family_context,
        ContextPackCategory.current_work,
        ContextPackCategory.current_projects,
        ContextPackCategory.current_creative_activity,
        ContextPackCategory.relevant_domains,
        ContextPackCategory.relevant_social_context,
    }
)


def context_pack_feature_enabled() -> bool:
    return os.environ.get("DEEP_READING_CONTEXT_PACK_ENABLED", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_pack_id() -> str:
    return f"pack_{uuid.uuid4().hex[:12]}"


def _new_item_id(category: ContextPackCategory, index: int) -> str:
    return f"pack_{category.value}_{index + 1:03d}"


def default_allowed_for_fact(category: ContextPackCategory) -> bool:
    return category not in INTERPRETATION_ONLY_CATEGORIES


def empty_context_pack(
    *,
    mode_intent: DeepReadingMode = DeepReadingMode.strict,
    language: str = "ja",
) -> ContextPack:
    now = _now_iso()
    return ContextPack(
        pack_id=_new_pack_id(),
        mode_intent=mode_intent,
        source="user_authored",
        created_at=now,
        updated_at=now,
        approved_by_user=False,
        language=language,
        items=[],
    )


def seed_context_pack_from_text(
    text: str,
    *,
    language: str = "ja",
    source: Literal[
        "session_seeded_draft", "imported_paste"
    ] = "session_seeded_draft",
) -> ContextPack:
    """Deterministic extractive split — never invents biography."""
    pack = empty_context_pack(mode_intent=DeepReadingMode.contextual, language=language)
    pack.source = source
    raw = (text or "").strip()
    if not raw:
        return pack

    chunks = [
        c.strip(" 　・-")
        for c in re.split(r"[。．！？\n]+|(?:また、)|(?:そして、)|(?:その後、)", raw)
        if c and c.strip()
    ]
    items: list[ContextPackItem] = []
    for i, chunk in enumerate(chunks):
        if len(chunk) < 4:
            continue
        category = _infer_category(chunk)
        items.append(
            ContextPackItem(
                id=_new_item_id(category, i),
                content=chunk,
                category=category,
                source=ContextPackItemSource.seeded_from_same_session_text
                if source == "session_seeded_draft"
                else ContextPackItemSource.user_pasted,
                confidence=0.6,
                approved=False,
                allowed_for_fact=default_allowed_for_fact(category),
                allowed_for_interpretation=True,
                chronology_rank=_infer_chronology_rank(category, i),
                tags=["seeded"],
            )
        )
    pack.items = items
    pack.updated_at = _now_iso()
    return pack


def _infer_category(text: str) -> ContextPackCategory:
    if re.search(r"NTT|会社|勤務|外資|経営|転職|退職|入社", text):
        if re.search(r"現在|いま|今は|経営している", text):
            return ContextPackCategory.current_work
        return ContextPackCategory.career_history
    if re.search(r"妻|夫|息子|娘|家族|猫|犬", text):
        return ContextPackCategory.family_context
    if re.search(r"観測|出版|Protocol|プロトコル|制作|プロジェクト", text):
        return ContextPackCategory.current_projects
    if re.search(r"創作|文章|書く|作家", text):
        return ContextPackCategory.current_creative_activity
    if re.search(r"価値観|大切|信じ", text):
        return ContextPackCategory.current_values
    if re.search(r"業界|市場|ドメイン", text):
        return ContextPackCategory.relevant_domains
    return ContextPackCategory.major_life_events


def _infer_chronology_rank(category: ContextPackCategory, index: int) -> int:
    if category in PAST_CATEGORIES:
        return 10 + index
    if category in PRESENT_CATEGORIES:
        return 100 + index
    return 50 + index


def approve_context_pack(pack: ContextPack) -> ContextPack:
    """Freeze pack-level approval. Only currently approved items remain usable."""
    now = _now_iso()
    items = []
    for item in pack.items:
        if not (item.content or "").strip():
            continue
        items.append(item)
    return pack.model_copy(
        update={
            "mode_intent": DeepReadingMode.contextual,
            "approved_by_user": True,
            "approved_at": now,
            "updated_at": now,
            "items": items,
        }
    )


def approved_items(pack: ContextPack | None) -> list[ContextPackItem]:
    if pack is None or not pack.approved_by_user:
        return []
    if pack.mode_intent != DeepReadingMode.contextual:
        return []
    return [
        item
        for item in pack.items
        if item.approved and (item.content or "").strip()
    ]


def approved_fact_items(pack: ContextPack | None) -> list[ContextPackItem]:
    return [i for i in approved_items(pack) if i.allowed_for_fact]


def approved_interpretation_items(pack: ContextPack | None) -> list[ContextPackItem]:
    return [i for i in approved_items(pack) if i.allowed_for_interpretation]


def pack_to_grounded_facts(pack: ContextPack | None) -> list[GroundedFact]:
    facts: list[GroundedFact] = []
    for item in approved_fact_items(pack):
        facts.append(
            GroundedFact(
                id=item.id,
                content=item.content.strip(),
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                source_text=item.content.strip(),
                confidence=float(item.confidence),
                allowed_as_fact=True,
                tags=[
                    "context_pack",
                    f"category:{item.category.value}",
                    f"pack_id:{(pack.pack_id if pack else '')}",
                    *list(item.tags or []),
                ],
            )
        )
    return facts


def inject_pack_into_grounded(
    grounded: GroundedInput,
    pack: ContextPack | None,
) -> GroundedInput:
    """Merge approved pack facts without overwriting branch facts."""
    pack_facts = pack_to_grounded_facts(pack)
    if not pack_facts:
        return grounded
    existing_ids = {f.id for f in grounded.facts if f.id}
    existing_text = {re.sub(r"\s+", "", f.content) for f in grounded.facts}
    merged = list(grounded.facts)
    for fact in pack_facts:
        compact = re.sub(r"\s+", "", fact.content)
        if fact.id in existing_ids or compact in existing_text:
            continue
        merged.append(fact)
        existing_ids.add(fact.id)
        existing_text.add(compact)

    # Enrich current_context with present-category pack lines (concrete only).
    ctx = list(grounded.current_context)
    ctx_compact = {re.sub(r"\s+", "", c) for c in ctx}
    for item in approved_fact_items(pack):
        if item.category not in PRESENT_CATEGORIES and item.category != ContextPackCategory.family_context:
            continue
        compact = re.sub(r"\s+", "", item.content)
        if compact in ctx_compact:
            continue
        ctx.append(item.content.strip())
        ctx_compact.add(compact)
    return grounded.model_copy(update={"facts": merged, "current_context": ctx})


def pack_corpus_text(pack: ContextPack | None) -> str:
    return "\n".join(i.content.strip() for i in approved_items(pack) if i.content.strip())


def pack_item_id_set(pack: ContextPack | None, *, facts_only: bool = True) -> set[str]:
    items = approved_fact_items(pack) if facts_only else approved_items(pack)
    return {i.id for i in items if i.id}


def resolve_effective_mode(
    *,
    requested_mode: str | DeepReadingMode | None,
    pack: ContextPack | None,
    feature_enabled: bool | None = None,
) -> DeepReadingMode:
    enabled = context_pack_feature_enabled() if feature_enabled is None else feature_enabled
    if not enabled:
        return DeepReadingMode.strict
    mode = requested_mode
    if isinstance(mode, str):
        mode = mode.strip().lower()
        if mode == DeepReadingMode.contextual.value:
            mode = DeepReadingMode.contextual
        else:
            mode = DeepReadingMode.strict
    if mode != DeepReadingMode.contextual:
        return DeepReadingMode.strict
    if pack is None or not pack.approved_by_user or not approved_fact_items(pack):
        # Empty/unapproved contextual → safe Strict fallback
        return DeepReadingMode.strict
    return DeepReadingMode.contextual


def serialize_pack_for_prompt(pack: ContextPack | None) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "content": item.content,
            "category": item.category.value,
            "allowed_for_fact": item.allowed_for_fact,
            "allowed_for_interpretation": item.allowed_for_interpretation,
            "chronology_rank": item.chronology_rank,
            "time_span": item.time_span.model_dump(mode="json"),
        }
        for item in approved_items(pack)
    ]
