"""v1.1.1-exp Relevant Context Selection + Meaning Compression + resume_density.

Contextual path only. Production Strict / v1.0.2 ignores this module.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.parallel_life_deep_reading.context_pack import (
    ContextPack,
    ContextPackCategory,
    PAST_CATEGORIES,
    PRESENT_CATEGORIES,
    approved_fact_items,
    approved_items,
)
from app.parallel_life_deep_reading.models import (
    Call1Result,
    CentralThesis,
    ContextRelevanceClassification,
    EditorialOutline,
    GroundedInput,
    MeaningCompression,
    RelevantContextSelection,
)
from app.parallel_life_deep_reading.section_contracts import (
    CALL_1_PROMPT_VERSION_V113,
    CALL_1_PROMPT_VERSION_V114,
    CALL_1_PROMPT_VERSION_V115,
    CALL_1_PROMPT_VERSION_V116,
    CALL_1_PROMPT_VERSION_V117,
    CALL_1_PROMPT_VERSION_V118,
    CALL_1_PROMPT_VERSION_V119,
    CALL_1_PROMPT_VERSION_V1110,
    CALL_1_PROMPT_VERSION_V1111,
    RUNTIME_VERSION_V113_EXP,
    RUNTIME_VERSION_V114_EXP,
    RUNTIME_VERSION_V115_EXP,
    RUNTIME_VERSION_V116_EXP,
    RUNTIME_VERSION_V117_EXP,
    RUNTIME_VERSION_V118_EXP,
    RUNTIME_VERSION_V119_EXP,
    RUNTIME_VERSION_V1110_EXP,
    RUNTIME_VERSION_V1111_EXP,
)

# Historical pins for A/B arms.
CALL_1_PROMPT_VERSION_V112 = "parallel-life-call-1-v1.1.2-exp"
RUNTIME_VERSION_V112_EXP = "parallel-life-runtime-v1.1.2-exp"
CALL_1_PROMPT_VERSION_V111 = "parallel-life-call-1-v1.1.1"
RUNTIME_VERSION_V111_EXP = "parallel-life-runtime-v1.1.1-exp"
CALL_1_PROMPT_VERSION_V110 = "parallel-life-call-1-v1.1.0"
RUNTIME_VERSION_V110_EXP = "parallel-life-runtime-v1.1.0-exp"

MAX_MANUSCRIPT_LOGIC_IDS = 5
RESUME_DENSITY_COMPRESSION_THRESHOLD = 6.0

Relevance = Literal["essential", "supporting", "irrelevant_for_this_branch"]

CATEGORY_PRIORITY = {
    ContextPackCategory.career_history.value: 10,
    ContextPackCategory.major_life_events.value: 20,
    ContextPackCategory.current_work.value: 30,
    ContextPackCategory.current_projects.value: 40,
    ContextPackCategory.current_creative_activity.value: 50,
    ContextPackCategory.family_context.value: 60,
    ContextPackCategory.relevant_domains.value: 70,
    ContextPackCategory.relevant_social_context.value: 80,
    ContextPackCategory.current_values.value: 90,
    ContextPackCategory.user_self_definitions.value: 100,
}

ORG_RE = re.compile(
    r"(?:NTT|外資|半導体|大学|株式会社|有限会社|Inc\.?|Corp\.?|Protocol|SHIRO)",
    re.I,
)
INDUSTRY_RE = re.compile(r"(?:業界|産業|半導体|通信|金融|広告|製造)")
PROJECT_RE = re.compile(r"(?:プロジェクト|観測|Protocol|プロトコル|サイト)")
CHRONO_RE = re.compile(r"(?:その後|次いで|続いて|転職した|入社|退職|勤務した)")
INVENTORY_LOST_RE = re.compile(
    r"(?:給与|年収|年金|肩書|役職名|同僚|社内人脈|タイトル一覧)"
)
SUCCESS_THESIS_RE = re.compile(
    r"(?:成功した|正しい選択|おかげで|多彩なキャリアを得た|現在の成功)"
)
RESUME_THESIS_RE = re.compile(
    r"(?:転職したことで|複数の企業で働き|経歴は次の通り|キャリアパスは)"
)
CAUSAL_THESIS_RE = re.compile(
    r"(?:影響を与え|につながっ|に繋がっ|を形成し|が形成され|のおかげで|結果として今)"
)


class ResumeDensityReport(BaseModel):
    resume_density: float = 0.0
    resume_density_flags: list[str] = Field(default_factory=list)
    compression_required: bool = False


def _pack_id_set(pack: ContextPack | None) -> set[str]:
    return {i.id for i in approved_items(pack) if i.id}


def _category_for_id(pack: ContextPack | None, item_id: str) -> str:
    if not pack:
        return ""
    for item in pack.items:
        if item.id == item_id:
            return item.category.value if hasattr(item.category, "value") else str(item.category)
    return ""


def _chronology_for_id(pack: ContextPack | None, item_id: str) -> int:
    if not pack:
        return 999
    for item in pack.items:
        if item.id == item_id:
            return int(item.chronology_rank)
    return 999


def default_selection_from_pack(pack: ContextPack | None) -> RelevantContextSelection:
    """Deterministic fallback when model omits selection."""
    items = approved_fact_items(pack)
    if not items:
        return RelevantContextSelection()
    classifications: list[ContextRelevanceClassification] = []
    seen_cats: dict[str, int] = {}
    logic: list[str] = []
    past_vals = {c.value for c in PAST_CATEGORIES}
    present_vals = {c.value for c in PRESENT_CATEGORIES} | {"family_context"}
    for item in sorted(
        items, key=lambda i: (CATEGORY_PRIORITY.get(i.category.value, 50), i.chronology_rank)
    ):
        cat = item.category.value
        count = seen_cats.get(cat, 0)
        relevance: Relevance
        if cat in past_vals:
            if count == 0:
                relevance = "essential"
            elif count == 1:
                relevance = "supporting"
            else:
                relevance = "irrelevant_for_this_branch"
        elif cat in present_vals:
            if count == 0:
                relevance = "essential"
            elif count == 1:
                relevance = "supporting"
            else:
                relevance = "irrelevant_for_this_branch"
        else:
            relevance = "supporting" if count == 0 else "irrelevant_for_this_branch"
        seen_cats[cat] = count + 1
        classifications.append(
            ContextRelevanceClassification(
                id=item.id,
                relevance=relevance,
                reason="deterministic_default_selection",
            )
        )
        if relevance in {"essential", "supporting"}:
            logic.append(item.id)
    logic = _trim_manuscript_logic_ids(logic, pack)
    selected = list(logic)
    withheld = [c.id for c in classifications if c.id not in selected]
    return RelevantContextSelection(
        selected_ids=selected,
        classifications=classifications,
        manuscript_logic_ids=logic,
        withheld_ids=withheld,
    )


def _trim_manuscript_logic_ids(
    ids: list[str], pack: ContextPack | None
) -> list[str]:
    if len(ids) <= MAX_MANUSCRIPT_LOGIC_IDS:
        return list(dict.fromkeys([x for x in ids if x]))

    def sort_key(iid: str) -> tuple[int, int]:
        cat = _category_for_id(pack, iid)
        return (CATEGORY_PRIORITY.get(cat, 50), _chronology_for_id(pack, iid))

    # Preserve essential-looking past/present first via category priority
    ordered = sorted(dict.fromkeys(ids), key=sort_key)
    trimmed = ordered[:MAX_MANUSCRIPT_LOGIC_IDS]
    # Cap org-heavy career lines: keep at most 2 career_history
    career = [i for i in trimmed if _category_for_id(pack, i) == "career_history"]
    if len(career) > 2:
        drop = set(career[2:])
        trimmed = [i for i in trimmed if i not in drop]
        for iid in ordered:
            if iid not in trimmed and len(trimmed) < MAX_MANUSCRIPT_LOGIC_IDS:
                if iid not in drop:
                    trimmed.append(iid)
    return trimmed[:MAX_MANUSCRIPT_LOGIC_IDS]


def normalize_relevant_context_selection(
    raw: RelevantContextSelection | dict[str, Any] | None,
    pack: ContextPack | None,
) -> RelevantContextSelection:
    pack_ids = _pack_id_set(pack)
    if raw is None:
        return default_selection_from_pack(pack)
    if isinstance(raw, dict):
        try:
            sel = RelevantContextSelection.model_validate(raw)
        except Exception:
            return default_selection_from_pack(pack)
    else:
        sel = raw

    if not pack_ids:
        return RelevantContextSelection()

    # Ensure every approved pack item is classified
    by_id = {c.id: c for c in sel.classifications if c.id}
    for iid in sorted(pack_ids):
        if iid not in by_id:
            by_id[iid] = ContextRelevanceClassification(
                id=iid,
                relevance="supporting",
                reason="runtime_backfill_unclassified",
            )
    # Drop unknown IDs
    classifications = [c for c in by_id.values() if c.id in pack_ids]

    logic = [
        x
        for x in (sel.manuscript_logic_ids or sel.selected_ids or [])
        if x in pack_ids
    ]
    if not logic:
        logic = [
            c.id
            for c in classifications
            if c.relevance in {"essential", "supporting"}
        ]
    # Prefer keeping essentials when trimming
    essentials = [c.id for c in classifications if c.relevance == "essential" and c.id in pack_ids]
    merged_logic = list(dict.fromkeys([*essentials, *logic]))
    logic = _trim_manuscript_logic_ids(merged_logic, pack)
    logic_set = set(logic)

    fixed_class: list[ContextRelevanceClassification] = []
    for c in classifications:
        if c.id in logic_set:
            rel: Relevance = (
                c.relevance if c.relevance != "irrelevant_for_this_branch" else "supporting"
            )
            fixed_class.append(c.model_copy(update={"relevance": rel}))
        else:
            fixed_class.append(
                c.model_copy(
                    update={
                        "relevance": "irrelevant_for_this_branch",
                        "reason": (c.reason or "runtime_normalize")
                        + (";runtime_withheld_over_cap" if c.relevance != "irrelevant_for_this_branch" else ""),
                    }
                )
            )

    withheld = [c.id for c in fixed_class if c.id not in logic_set]
    return RelevantContextSelection(
        selected_ids=list(logic),
        classifications=fixed_class,
        manuscript_logic_ids=list(logic),
        withheld_ids=withheld,
    )


def normalize_meaning_compression(
    raw: MeaningCompression | dict[str, Any] | None,
    *,
    selection: RelevantContextSelection,
    branch_support_ids: list[str],
) -> MeaningCompression:
    if raw is None:
        mc = MeaningCompression()
    elif isinstance(raw, dict):
        try:
            mc = MeaningCompression.model_validate(raw)
        except Exception:
            mc = MeaningCompression()
    else:
        mc = raw

    allowed = set(selection.manuscript_logic_ids) | set(branch_support_ids)
    support = [x for x in (mc.support_ids or []) if x in allowed]
    if not support:
        support = list(dict.fromkeys([*branch_support_ids[:3], *selection.manuscript_logic_ids[:3]]))

    def scrub(text: str) -> str:
        t = (text or "").strip()
        # Drop long inventory-looking compression
        if len(re.findall(ORG_RE, t)) >= 3:
            return re.sub(ORG_RE, "組織", t)
        return t

    status = mc.validation_status or "pending"
    filled = any(
        [
            mc.past_structure,
            mc.alternative_structure,
            mc.present_structure,
            mc.tension,
            mc.central_question,
            mc.personal_tension,
            mc.social_institutional_parallel,
            mc.unresolved_question,
        ]
    )
    if not filled:
        status = "deferred_empty"

    return mc.model_copy(
        update={
            "past_structure": scrub(mc.past_structure),
            "alternative_structure": scrub(mc.alternative_structure),
            "present_structure": scrub(mc.present_structure),
            "tension": scrub(mc.tension),
            "continuity": scrub(mc.continuity),
            "transformation": scrub(mc.transformation),
            "central_question": scrub(mc.central_question),
            "personal_tension": scrub(mc.personal_tension),
            "social_institutional_parallel": scrub(mc.social_institutional_parallel),
            "present_life_connection": scrub(mc.present_life_connection),
            "unresolved_question": scrub(mc.unresolved_question),
            "cross_lens_relation_ids": list(mc.cross_lens_relation_ids or []),
            "support_ids": support,
            "validation_status": status,
        }
    )


def compute_resume_density(text: str) -> ResumeDensityReport:
    blob = text or ""
    flags: list[str] = []
    score = 0.0
    org_hits = len(set(ORG_RE.findall(blob)))
    if org_hits >= 3:
        score += 3
        flags.append("org_enumeration")
    elif org_hits == 2:
        score += 1.5
        flags.append("org_names_present")
    ind = len(INDUSTRY_RE.findall(blob))
    if ind >= 3:
        score += 2
        flags.append("industry_enumeration")
    proj = len(PROJECT_RE.findall(blob))
    if proj >= 3:
        score += 2
        flags.append("project_enumeration")
    chrono = len(CHRONO_RE.findall(blob))
    if chrono >= 4:
        score += 2.5
        flags.append("chronology_stack")
    elif chrono >= 2:
        score += 1
    # Fact stacking without interpretive connectors
    interpret = len(re.findall(r"(?:並べて|読み直|問い|構造|緊張|余白|持ち運)", blob))
    factsish = len(re.findall(r"(?:勤務|転職|経営|経験した|制作を行)", blob))
    if factsish >= 4 and interpret <= 1:
        score += 2
        flags.append("facts_without_interpretation")
    score = min(10.0, round(score, 1))
    return ResumeDensityReport(
        resume_density=score,
        resume_density_flags=flags,
        compression_required=score >= RESUME_DENSITY_COMPRESSION_THRESHOLD,
    )


def thesis_soft_gate(
    thesis: CentralThesis,
    *,
    selection: RelevantContextSelection,
    compression: MeaningCompression,
    branch_support_ids: list[str],
) -> tuple[CentralThesis, list[str]]:
    notes: list[str] = []
    statement = (thesis.statement or "").strip()
    if thesis.validation_status.startswith("deferred"):
        return thesis, notes
    if not statement:
        notes.append("thesis_gate:empty_statement")
        return thesis.model_copy(update={"validation_status": "failed_empty"}), notes
    if SUCCESS_THESIS_RE.search(statement):
        notes.append("thesis_gate:moral_success_narrative")
        return thesis.model_copy(update={"validation_status": "failed_success_narrative"}), notes
    if RESUME_THESIS_RE.search(statement) and not compression.tension:
        notes.append("thesis_gate:resume_summary_without_tension")
        return thesis.model_copy(update={"validation_status": "failed_resume_summary"}), notes
    if CAUSAL_THESIS_RE.search(statement):
        notes.append("thesis_gate:unsupported_causal_framing")
        # Soft fail — runtime may repair from compression tension
        return thesis.model_copy(update={"validation_status": "failed_causal_framing"}), notes

    allowed = set(selection.manuscript_logic_ids) | set(branch_support_ids)
    supported = [x for x in (thesis.supported_by or []) if x in allowed]
    if not supported and allowed:
        supported = list(selection.manuscript_logic_ids[:2]) + list(branch_support_ids[:2])
        notes.append("thesis_gate:supported_by_backfilled")
    status = "passed"
    # Prefer tension/central_question echo
    if compression.tension and not any(
        tok in statement for tok in re.findall(r"[\u4e00-\u9fff]{2,}", compression.tension)[:3]
    ):
        if compression.central_question and any(
            tok in statement
            for tok in re.findall(r"[\u4e00-\u9fff]{2,}", compression.central_question)[:3]
        ):
            pass
        else:
            notes.append("thesis_gate:weak_link_to_compression")
            status = "passed_weak_compression_link"

    return thesis.model_copy(
        update={"supported_by": supported, "validation_status": status}
    ), notes


def strip_outline_to_logic_ids(
    outline: EditorialOutline,
    *,
    logic_ids: set[str],
    branch_ids: set[str],
) -> EditorialOutline:
    allowed = logic_ids | branch_ids
    sections = []
    for sec in outline.sections or []:
        reserved = [x for x in (sec.reserved_fact_ids or []) if x in allowed]
        sections.append(sec.model_copy(update={"reserved_fact_ids": reserved}))
    return outline.model_copy(update={"sections": sections})


def selected_pack_corpus_text(
    pack: ContextPack | None, selection: RelevantContextSelection | None
) -> str:
    if pack is None or selection is None:
        return ""
    logic = set(selection.manuscript_logic_ids or [])
    lines = []
    for item in approved_items(pack):
        if item.id in logic and (item.content or "").strip():
            lines.append(item.content.strip())
    return "\n".join(lines)


def filter_grounded_pack_facts_for_draft(
    grounded: GroundedInput, selection: RelevantContextSelection | None
) -> GroundedInput:
    """Keep branch facts; keep only selected pack facts for Call2 ledger."""
    if selection is None:
        return grounded
    logic = set(selection.manuscript_logic_ids or [])
    facts = []
    for f in grounded.facts:
        if (f.source_field or "") == "context_pack" or "context_pack" in (f.tags or []):
            if f.id in logic:
                facts.append(f)
        else:
            facts.append(f)
    return grounded.model_copy(update={"facts": facts})


def compression_text_blob(compression: MeaningCompression) -> str:
    return "\n".join(
        [
            compression.past_structure,
            compression.alternative_structure,
            compression.present_structure,
            compression.tension,
            compression.continuity,
            compression.transformation,
            compression.central_question,
            compression.personal_tension,
            compression.social_institutional_parallel,
            compression.present_life_connection,
            compression.unresolved_question,
        ]
    )


def enrich_compression_from_relations(
    compression: MeaningCompression,
    relations: list[Any],
) -> MeaningCompression:
    """Fill v1.1.2 compression slots from CrossLensRelations when LLM left them empty."""
    if not relations:
        return compression
    rel_dicts = []
    for r in relations:
        if hasattr(r, "model_dump"):
            rel_dicts.append(r.model_dump(mode="json"))
        elif isinstance(r, dict):
            rel_dicts.append(r)
    if not rel_dicts:
        return compression
    primary = rel_dicts[0]
    ids = [str(r.get("id") or "") for r in rel_dicts if r.get("id")]
    update: dict[str, Any] = {
        "cross_lens_relation_ids": ids or list(compression.cross_lens_relation_ids or []),
    }
    if not (compression.personal_tension or "").strip():
        update["personal_tension"] = str(primary.get("personal_structure") or "")
    if not (compression.social_institutional_parallel or "").strip():
        update["social_institutional_parallel"] = str(primary.get("social_structure") or "")
    if not (compression.tension or "").strip():
        update["tension"] = str(primary.get("interpretation") or "")[:200]
    if not (compression.unresolved_question or "").strip() and not (
        compression.central_question or ""
    ).strip():
        update["unresolved_question"] = (
            "この分岐を、いまどう読み直すかがまだ開いている"
        )
    if not (compression.central_question or "").strip() and update.get(
        "unresolved_question"
    ):
        update["central_question"] = update["unresolved_question"]
    return compression.model_copy(update=update)


def lost_looks_like_inventory(text: str) -> bool:
    return bool(INVENTORY_LOST_RE.search(text or "")) or (
        len(re.findall(r"[、,]", text or "")) >= 3 and len(text or "") < 80
    )


def apply_selection_compression_gates(
    result: Call1Result,
    *,
    pack: ContextPack | None,
) -> tuple[Call1Result, dict[str, Any]]:
    """Normalize selection/compression and attach diagnostics (Contextual only)."""
    branch_ids = list(result.branch_structure.primary_branch.supporting_fact_ids or [])
    for f in result.grounded_input.facts:
        if f.id and (f.source_field or "") != "context_pack":
            if f.id not in branch_ids:
                branch_ids.append(f.id)

    raw_sel = getattr(result, "relevant_context_selection", None)
    raw_mc = getattr(result, "meaning_compression", None)
    selection = normalize_relevant_context_selection(raw_sel, pack)
    compression = normalize_meaning_compression(
        raw_mc, selection=selection, branch_support_ids=branch_ids
    )
    thesis, thesis_notes = thesis_soft_gate(
        result.central_thesis,
        selection=selection,
        compression=compression,
        branch_support_ids=branch_ids,
    )
    outline = strip_outline_to_logic_ids(
        result.editorial_outline,
        logic_ids=set(selection.manuscript_logic_ids),
        branch_ids=set(branch_ids),
    )

    # Résumé density over thesis + compression + confirmation preview
    density_blob = "\n".join(
        [
            thesis.statement,
            compression_text_blob(compression),
            result.user_confirmation_view.central_thesis_preview,
            " ".join(selection.manuscript_logic_ids),
        ]
    )
    # Include selected pack contents
    density_blob += "\n" + selected_pack_corpus_text(pack, selection)
    resume = compute_resume_density(density_blob)

    lost_notes = []
    lost_items = []
    for item in result.lost_structure.items or []:
        if lost_looks_like_inventory(item.content):
            lost_notes.append("lost_inventory_rejected")
            continue
        lost_items.append(item)

    diag = {
        "relevant_context_selection": selection.model_dump(mode="json"),
        "meaning_compression": compression.model_dump(mode="json"),
        "resume_density": resume.model_dump(mode="json"),
        "thesis_gate_notes": thesis_notes,
        "lost_notes": lost_notes,
        "runtime_pin": RUNTIME_VERSION_V1111_EXP,
        "prompt_pin": CALL_1_PROMPT_VERSION_V1111,
    }

    view = result.user_confirmation_view.model_copy(
        update={"central_thesis_preview": thesis.statement or result.user_confirmation_view.central_thesis_preview}
    )
    notes = list(result.validation.notes or [])
    notes.extend([f"selection:{n}" for n in thesis_notes])
    if resume.compression_required:
        notes.append("resume_density:compression_required")
    notes.append(f"runtime:{RUNTIME_VERSION_V1111_EXP}")

    updated = result.model_copy(
        update={
            "relevant_context_selection": selection,
            "meaning_compression": compression,
            "central_thesis": thesis,
            "editorial_outline": outline,
            "lost_structure": result.lost_structure.model_copy(update={"items": lost_items}),
            "user_confirmation_view": view,
            "validation": result.validation.model_copy(update={"notes": notes}),
            "resume_density_report": resume.model_dump(mode="json"),
        }
    )
    return updated, diag
