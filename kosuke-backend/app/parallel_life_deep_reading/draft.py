"""Call 2: single-manuscript draft generation (fact-bounded)."""

from __future__ import annotations

import re
from typing import Any

from app.parallel_life_deep_reading.call1_schema import (
    call1_rebranch_directions,
    call1_residue_items,
    call1_selected_lenses,
)
from app.parallel_life_deep_reading.llm import DeepReadingGenerationError, chat_json
from app.parallel_life_deep_reading.production_models import CALL_2_MODEL
from app.parallel_life_deep_reading.models import (
    Call1Result,
    Call2Draft,
    DraftSectionMeta,
    ParagraphSupport,
    RebranchDirection,
)
from app.parallel_life_deep_reading.prompts import (
    CALL_2_VERSION,
    call2_system_prompt,
    call2_system_prompt_v113,
    call2_system_prompt_v114,
    call2_system_prompt_v115,
    call2_system_prompt_v116,
    call2_system_prompt_v117,
    call2_user_prompt,
    call2_user_prompt_v113,
    call2_user_prompt_v114,
    call2_user_prompt_v115,
    call2_user_prompt_v116,
    call2_user_prompt_v117,
)
from app.parallel_life_deep_reading.runtime_validation import (
    detect_schema_leakage_prose,
    detect_unsupported_affect,
    detect_unsupported_causal_frame,
    detect_unsupported_causality,
    detect_unsupported_personal_details,
    detect_unsupported_role_behavior,
    detect_unsupported_scenes,
    filter_publishable_rebranch,
)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def build_evidence_ledger(call1: Call1Result) -> dict[str, Any]:
    from app.parallel_life_deep_reading.context_selection import (
        filter_grounded_pack_facts_for_draft,
    )

    selection = getattr(call1, "relevant_context_selection", None)
    g = filter_grounded_pack_facts_for_draft(call1.grounded_input, selection)
    compression = getattr(call1, "meaning_compression", None)
    logic_ids = list(getattr(selection, "manuscript_logic_ids", None) or [])
    return {
        "explicit_facts": [
            {"id": f.id, "content": f.content} for f in g.facts if f.content.strip()
        ],
        "user_feelings": [
            {"id": f.id, "content": f.content} for f in g.feelings if f.content.strip()
        ],
        "user_questions": [
            {"id": q.id, "content": q.content, "mark": "question_not_answer"}
            for q in g.questions
            if q.content.strip()
        ],
        "user_hypotheses": [
            {"id": h.id, "content": h.content, "mark": "hypothesis_not_fact"}
            for h in g.hypotheses
            if h.content.strip()
        ],
        "validated_residue": [
            {
                "residue_statement": r.statement(),
                "past_anchor_ids": r.past_anchor_ids,
                "present_anchor_ids": r.present_anchor_ids,
                "inference_distance": r.inference_distance,
            }
            for r in call1_residue_items(call1)
        ],
        "branch_structure": call1.branch_structure.model_dump(mode="json"),
        "current_context": list(g.current_context),
        "central_thesis": call1.central_thesis.statement,
        # v1.1.1-exp: selected pack only (full approved pack withheld from draft corpus)
        "manuscript_logic_ids": logic_ids,
        "meaning_compression": (
            compression.model_dump(mode="json") if compression is not None else {}
        ),
        "cross_lens_relations": list(
            getattr(call1, "cross_lens_relations", None) or []
        ),
        "editorial_constraints": {
            "anti_resume": True,
            "max_org_names_in_body": 2,
            "prefer_structure_over_chronology": True,
            "title_from_tension_not_employer_list": True,
            "do_not_advertise_lens_names": True,
            "observatory_section_only_if_new_meaning": True,
        },
    }


def _parse_rebranch(raw: dict[str, Any]) -> RebranchDirection:
    score = raw.get("genericity_score", 2)
    try:
        score_i = int(score)
    except (TypeError, ValueError):
        score_i = 2
    if score_i not in (0, 1, 2, 3):
        score_i = 2
    return RebranchDirection(
        id=str(raw.get("id") or ""),
        source_meaning=str(raw.get("source_meaning") or ""),
        current_receiver=str(raw.get("current_receiver") or ""),
        branch_specific_form=str(raw.get("branch_specific_form") or ""),
        support_ids=[
            str(x)
            for x in _as_list(raw.get("support_ids") or raw.get("factual_support_ids"))
        ],
        genericity_score=score_i,  # type: ignore[arg-type]
        invented_scene_used=bool(raw.get("invented_scene_used", False)),
        risks=[str(x) for x in _as_list(raw.get("risks"))],
        publishable=bool(raw.get("publishable", False)),
        selected_for_manuscript=bool(raw.get("selected_for_manuscript", False)),
    )


def _split_paragraphs(body: str) -> list[str]:
    parts = re.split(r"\n\s*\n", (body or "").strip())
    return [p.strip() for p in parts if p.strip() and not re.match(r"^#+\s", p.strip())]


def _ensure_paragraph_support(
    body: str,
    raw_support: list[Any],
    call1: Call1Result,
) -> list[ParagraphSupport]:
    paragraphs = _split_paragraphs(body)
    by_id: dict[str, ParagraphSupport] = {}
    for i, item in enumerate(raw_support):
        if not isinstance(item, dict):
            continue
        pid = str(item.get("paragraph_id") or f"p{i+1:02d}")
        by_id[pid] = ParagraphSupport(
            paragraph_id=pid,
            support_ids=[str(x) for x in _as_list(item.get("support_ids")) if str(x).strip()],
            contains_inference=bool(item.get("contains_inference", False)),
            text_preview=str(item.get("text_preview") or "")[:120],
        )

    allowed_ids = {
        f.id
        for f in [
            *call1.grounded_input.facts,
            *call1.grounded_input.feelings,
            *call1.grounded_input.questions,
            *call1.grounded_input.hypotheses,
        ]
        if f.id
    }
    for r in call1_residue_items(call1):
        allowed_ids.update(r.past_anchor_ids)
        allowed_ids.update(r.present_anchor_ids)
        allowed_ids.update(r.support_ids)

    out: list[ParagraphSupport] = []
    for i, para in enumerate(paragraphs):
        pid = f"p{i+1:02d}"
        existing = by_id.get(pid)
        support = [s for s in (existing.support_ids if existing else []) if s in allowed_ids]
        # Heuristic fill if model omitted map but paragraph clearly uses known ids' content
        if not support:
            for f in call1.grounded_input.facts:
                if f.id and f.content and f.content[:10] in para:
                    support.append(f.id)
            for q in call1.grounded_input.questions:
                if q.id and q.content and any(
                    t in para for t in re.findall(r"[\u4e00-\u9fff]{3,}", q.content)[:3]
                ):
                    support.append(q.id)
        out.append(
            ParagraphSupport(
                paragraph_id=pid,
                support_ids=list(dict.fromkeys(support)),
                contains_inference=bool(existing.contains_inference) if existing else False,
                text_preview=para[:120],
            )
        )
    return out


def parse_call2_payload(data: dict[str, Any], call1: Call1Result) -> Call2Draft:
    body = str(data.get("body_markdown") or data.get("manuscript") or "").strip()
    if not body:
        raise DeepReadingGenerationError("Call 2 returned empty manuscript.")

    raw_rb = _as_list(data.get("rebranch_candidates") or data.get("rebranch_design"))
    candidates = [_parse_rebranch(x) for x in raw_rb if isinstance(x, dict)]
    if not candidates:
        candidates = list(call1_rebranch_directions(call1))

    validated, publishable = filter_publishable_rebranch(
        candidates, grounded=call1.grounded_input
    )
    omit_reason = data.get("rebranch_omitted_reason")
    if not publishable and not omit_reason:
        omit_reason = "no_publishable_rebranch_candidates"

    observatory_omitted = len(call1_selected_lenses(call1)) == 0

    sections = []
    for item in _as_list(data.get("sections")):
        if not isinstance(item, dict):
            continue
        heading = str(item.get("public_heading") or "")
        internal = str(item.get("internal_id") or "")
        included = bool(item.get("included", True))
        if observatory_omitted and internal.lower() in {
            "observatory",
            "cross_lens_synthesis",
            "cross-lens",
        }:
            included = False
        if not publishable and internal.lower() in {"rebranch", "re-branch"}:
            included = False
        sections.append(
            DraftSectionMeta(
                internal_id=internal,
                public_heading=heading,
                included=included,
                char_count=int(item.get("char_count") or 0),
            )
        )

    titles = [str(x) for x in _as_list(data.get("title_candidates")) if str(x).strip()]
    paragraph_support = _ensure_paragraph_support(
        body, _as_list(data.get("paragraph_support")), call1
    )

    personal = detect_unsupported_personal_details(body, call1.grounded_input)
    scenes = detect_unsupported_scenes(body, call1.grounded_input)
    causality = detect_unsupported_causality(body, call1.grounded_input)
    causal_frames = detect_unsupported_causal_frame(body, call1.grounded_input)
    schema_leakage = detect_schema_leakage_prose(body)
    affect = detect_unsupported_affect(body, call1.grounded_input)
    roles = detect_unsupported_role_behavior(body, call1.grounded_input)
    unsupported_bio_paras = [
        p.paragraph_id
        for p in paragraph_support
        if not p.support_ids
        and len(p.text_preview) > 40
        and detect_unsupported_personal_details(p.text_preview, call1.grounded_input)
    ]

    return Call2Draft(
        body_markdown=body if body.endswith("\n") else body + "\n",
        title_candidates=titles[:5],
        subtitle_candidates=[
            str(x) for x in _as_list(data.get("subtitle_candidates")) if str(x).strip()
        ][:5],
        sections=sections,
        rebranch_candidates=publishable,
        rebranch_omitted_reason=str(omit_reason) if omit_reason else None,
        observatory_omitted=observatory_omitted,
        paragraph_support=paragraph_support,
        diagnostics={
            "rebranch_validated": [c.model_dump() for c in validated],
            "selected_lens_count": len(call1_selected_lenses(call1)),
            "unsupported_personal_details": [d.model_dump() for d in personal],
            "unsupported_scenes": [s.model_dump() for s in scenes],
            "unsupported_causality": [c.model_dump() for c in causality],
            "unsupported_causal_frame": [c.model_dump() for c in causal_frames],
            "schema_leakage_prose": [s.model_dump() for s in schema_leakage],
            "unsupported_affect": [a.model_dump() for a in affect],
            "unsupported_role_behavior": [r.model_dump() for r in roles],
            "unsupported_bio_paragraphs": unsupported_bio_paras,
            "paragraph_support_coverage": sum(1 for p in paragraph_support if p.support_ids)
            / max(1, len(paragraph_support)),
        },
        prompt_version=CALL_2_VERSION,
        character_count=len(body),
    )


def _use_section_contract_writing_pack(call1: Call1Result) -> bool:
    pv = (getattr(call1, "prompt_version", None) or "").strip()
    schema_v = (getattr(call1, "schema_version", None) or "").strip()
    if "v1.1.11" in schema_v or "v1.1.11" in pv:
        return True
    if "v1.1.10" in schema_v or "v1.1.10" in pv:
        return True
    if any(
        v in pv
        for v in (
            "v1.1.3",
            "v1.1.4",
            "v1.1.5",
            "v1.1.6",
            "v1.1.7",
            "v1.1.8",
            "v1.1.9",
        )
    ):
        return True
    sc = getattr(call1, "section_contracts", None)
    return isinstance(sc, dict) and bool(sc.get("contracts"))


def _call2_prompt_for_version(call1: Call1Result, writing_pack: dict) -> tuple[str, str, str]:
    from app.parallel_life_deep_reading.prompts import (
        call2_system_prompt_v118,
        call2_system_prompt_v119,
        call2_user_prompt_v118,
        call2_user_prompt_v119,
    )
    from app.parallel_life_deep_reading.section_contracts import (
        CALL_2_PROMPT_VERSION_V113,
        CALL_2_PROMPT_VERSION_V114,
        CALL_2_PROMPT_VERSION_V115,
        CALL_2_PROMPT_VERSION_V116,
        CALL_2_PROMPT_VERSION_V117,
        CALL_2_PROMPT_VERSION_V118,
        CALL_2_PROMPT_VERSION_V119,
        CALL_2_PROMPT_VERSION_V1110,
        CALL_2_PROMPT_VERSION_V1111,
    )

    pv = (getattr(call1, "prompt_version", None) or "").strip()
    schema_v = (getattr(call1, "schema_version", None) or "").strip()
    # v1.1.11 / v1.1.10: same writing prompts as v1.1.9; pin bumps for contract wiring
    if "v1.1.11" in schema_v or "v1.1.11" in pv:
        return (
            call2_system_prompt_v119(),
            call2_user_prompt_v119(writing_pack),
            CALL_2_PROMPT_VERSION_V1111,
        )
    if "v1.1.10" in schema_v or "v1.1.10" in pv:
        return (
            call2_system_prompt_v119(),
            call2_user_prompt_v119(writing_pack),
            CALL_2_PROMPT_VERSION_V1110,
        )
    if "v1.1.9" in pv:
        return (
            call2_system_prompt_v119(),
            call2_user_prompt_v119(writing_pack),
            CALL_2_PROMPT_VERSION_V119,
        )
    if "v1.1.8" in pv:
        return (
            call2_system_prompt_v118(),
            call2_user_prompt_v118(writing_pack),
            CALL_2_PROMPT_VERSION_V118,
        )
    if "v1.1.7" in pv:
        return (
            call2_system_prompt_v117(),
            call2_user_prompt_v117(writing_pack),
            CALL_2_PROMPT_VERSION_V117,
        )
    if "v1.1.6" in pv:
        return (
            call2_system_prompt_v116(),
            call2_user_prompt_v116(writing_pack),
            CALL_2_PROMPT_VERSION_V116,
        )
    if "v1.1.5" in pv:
        return (
            call2_system_prompt_v115(),
            call2_user_prompt_v115(writing_pack),
            CALL_2_PROMPT_VERSION_V115,
        )
    if "v1.1.4" in pv:
        return (
            call2_system_prompt_v114(),
            call2_user_prompt_v114(writing_pack),
            CALL_2_PROMPT_VERSION_V114,
        )
    return (
        call2_system_prompt_v113(),
        call2_user_prompt_v113(writing_pack),
        CALL_2_PROMPT_VERSION_V113,
    )


def run_call2_draft(call1: Call1Result) -> Call2Draft:
    if not call1.grounded_input.confirmed_by_user:
        raise DeepReadingGenerationError(
            "Call 2 rejected: grounded_input.confirmed_by_user must be true."
        )
    if not call1_residue_items(call1):
        raise DeepReadingGenerationError(
            "Call 2 rejected: validated Residue is required before draft generation."
        )

    if _use_section_contract_writing_pack(call1):
        from app.parallel_life_deep_reading.section_contracts import (
            build_call2_writing_pack,
            writing_pack_size_stats,
        )

        writing_pack = build_call2_writing_pack(call1)
        stats = writing_pack_size_stats(writing_pack, call1)
        # Attach diagnostics onto call1 for reports (non-schema LLM field).
        try:
            call1.call2_writing_pack_diagnostics = stats  # type: ignore[attr-defined]
        except Exception:
            pass
        system, user, prompt_version = _call2_prompt_for_version(call1, writing_pack)
        data = chat_json(
            system,
            user,
            max_tokens=7000,
            temperature=0.4,
            model=CALL_2_MODEL,
        )
        draft = parse_call2_payload(data, call1)
        diag = dict(draft.diagnostics or {})
        diag["call2_writing_pack"] = stats
        diag["call2_prompt_version"] = prompt_version
        return draft.model_copy(
            update={
                "diagnostics": diag,
                "prompt_version": prompt_version,
            }
        )

    from app.parallel_life_deep_reading.context_selection import (
        filter_grounded_pack_facts_for_draft,
    )

    # Legacy Contextual / Strict: selected pack facts; validators keep full call1.
    selection = getattr(call1, "relevant_context_selection", None)
    call1_for_llm = call1.model_copy(
        update={
            "grounded_input": filter_grounded_pack_facts_for_draft(
                call1.grounded_input, selection
            )
        }
    )
    call1_json = call1_for_llm.model_dump(mode="json")
    ledger = build_evidence_ledger(call1)
    data = chat_json(
        call2_system_prompt(),
        call2_user_prompt(call1_json, ledger),
        max_tokens=7000,
        temperature=0.4,
        model=CALL_2_MODEL,
    )
    return parse_call2_payload(data, call1)
