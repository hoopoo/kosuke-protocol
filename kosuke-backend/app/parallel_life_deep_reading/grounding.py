"""Call 1: grounding and editorial design (schema v1.0.1)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from pydantic import ValidationError

from app.parallel_life_deep_reading.call1_schema import (
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
    AdditionalQuestions,
    Call1LLMPayload,
    Call1ParseDiagnostics,
    Call1Response,
    Call1SchemaError,
    EditorialOutline,
    LostStructure,
    ObservatoryLensSelection,
    ProtectedStructure,
    RebranchDesign,
    RepetitionMapEntry,
    RepetitionPreventionMap,
    ResidueCandidates,
    SensitiveDomainAnalysis,
    SourceCoverage,
    call1_json_schema,
    openai_response_format,
)
from app.parallel_life_deep_reading.llm import chat_json_schema
from app.parallel_life_deep_reading.models import (
    BranchClassification,
    BranchStructure,
    Call1Validation,
    CentralThesis,
    ConfirmedContinuity,
    EditorialSectionPlan,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    InputSufficiency,
    LostItem,
    ObservatoryLensCandidate,
    PrimaryBranch,
    RebranchDirection,
    ResidueCandidate,
    SecondaryBranch,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.prompts import (
    call1_repair_user_prompt,
    call1_system_prompt,
    call1_system_prompt_v11,
    call1_user_prompt,
    call1_user_prompt_v11,
)
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    build_input_corpus,
)

# Backward-compatible name used by older imports/tests.
Call1Result = Call1Response


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        # Map of id->content or category bags
        if all(isinstance(v, (str, dict)) for v in value.values()):
            items: list[Any] = []
            for k, v in value.items():
                if isinstance(v, dict):
                    items.append(v)
                else:
                    items.append({"id": str(k), "content": str(v)})
            return items
        return [value]
    return [value]


def _as_object(value: Any, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return dict(default or {})


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return str(value).strip()


def _fact_from_any(
    raw: Any,
    default_type: FactBoundaryType,
    *,
    fallback_id: str,
    source_text: str,
) -> GroundedFact | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        content = raw.strip()
        if not content:
            return None
        return GroundedFact(
            id=fallback_id,
            content=content,
            boundary_type=default_type,
            source_text=source_text or content,
            allowed_as_fact=default_type == FactBoundaryType.explicit_fact,
        )
    if not isinstance(raw, dict):
        return None
    content = _safe_str(raw.get("content") or raw.get("text") or raw.get("description"))
    if not content:
        return None
    btype_raw = _safe_str(raw.get("boundary_type") or raw.get("type")) or default_type.value
    try:
        btype = FactBoundaryType(btype_raw)
    except ValueError:
        btype = default_type
    return GroundedFact(
        id=_safe_str(raw.get("id")) or fallback_id,
        content=content,
        boundary_type=btype,
        source_field=_safe_str(raw.get("source_field") or raw.get("source")),
        source_text=_safe_str(raw.get("source_text")) or source_text or content,
        confidence=float(raw["confidence"])
        if isinstance(raw.get("confidence"), (int, float))
        else 0.8,
        allowed_as_fact=bool(
            raw.get("allowed_as_fact", btype == FactBoundaryType.explicit_fact)
        ),
        inference_distance=_safe_str(raw.get("inference_distance")) or "none",
        supported_by=[_safe_str(x) for x in _as_list(raw.get("supported_by")) if _safe_str(x)],
        tags=[_safe_str(x) for x in _as_list(raw.get("tags")) if _safe_str(x)],
    )


def _collect_bucket(gi: dict[str, Any], *keys: str) -> list[Any]:
    out: list[Any] = []
    for key in keys:
        if key in gi:
            out.extend(_as_list(gi.get(key)))
    return out


def normalize_raw_call1_dict(raw: Any, *, source_text: str) -> tuple[dict[str, Any], list[str]]:
    """Coerce known live-failure shapes into canonical dict. Never raises AttributeError."""
    notes: list[str] = []
    if not isinstance(raw, dict):
        notes.append("root_not_object")
        raw = {}

    data = dict(raw)

    # --- grounded_input ---
    gi_raw = data.get("grounded_input")
    if not isinstance(gi_raw, dict):
        notes.append("grounded_input_coerced_from_non_object")
        gi_raw = {}
    gi = dict(gi_raw)

    facts: list[dict[str, Any]] = []
    feelings: list[dict[str, Any]] = []
    questions: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    inferences: list[dict[str, Any]] = []

    def absorb(items: list[Any], default: FactBoundaryType, bucket: list[dict[str, Any]], prefix: str) -> None:
        for i, item in enumerate(items):
            fact = _fact_from_any(
                item, default, fallback_id=f"{prefix}_{i+1:03d}", source_text=source_text
            )
            if fact:
                bucket.append(fact.model_dump(mode="json"))

    absorb(_collect_bucket(gi, "facts", "explicit_facts", "explicit_fact"), FactBoundaryType.explicit_fact, facts, "fact")
    absorb(_collect_bucket(gi, "feelings", "user_feelings", "user_feeling"), FactBoundaryType.user_feeling, feelings, "feeling")
    absorb(_collect_bucket(gi, "questions", "user_questions", "user_question"), FactBoundaryType.user_question, questions, "question")
    absorb(_collect_bucket(gi, "hypotheses", "user_hypotheses", "user_hypothesis"), FactBoundaryType.user_hypothesis, hypotheses, "hypothesis")
    absorb(_collect_bucket(gi, "unknowns", "unknown"), FactBoundaryType.unknown, unknowns, "unknown")
    absorb(_collect_bucket(gi, "model_inferences", "model_inference"), FactBoundaryType.model_inference, inferences, "inference")

    # chosen/unchosen only shape (Case 3 failure)
    if gi.get("chosen_path") and isinstance(gi.get("chosen_path"), str):
        absorb([gi.get("chosen_path")], FactBoundaryType.explicit_fact, facts, "fact_chosen")
        notes.append("normalized_chosen_path_string")
    if gi.get("unchosen_path") and isinstance(gi.get("unchosen_path"), str):
        absorb([gi.get("unchosen_path")], FactBoundaryType.explicit_fact, facts, "fact_unchosen")
        notes.append("normalized_unchosen_path_string")

    current_context = [_safe_str(x) for x in _as_list(gi.get("current_context")) if _safe_str(x)]
    data["grounded_input"] = {
        "facts": facts,
        "feelings": feelings,
        "questions": questions,
        "hypotheses": hypotheses,
        "unknowns": unknowns,
        "model_inferences": inferences,
        "current_context": current_context,
        "sensitive_domains": [_safe_str(x) for x in _as_list(gi.get("sensitive_domains")) if _safe_str(x)],
        "confirmed_by_user": bool(gi.get("confirmed_by_user", False)),
        "requested_corrections": [_safe_str(x) for x in _as_list(gi.get("requested_corrections")) if _safe_str(x)],
    }

    # --- input_sufficiency ---
    suf = data.get("input_sufficiency")
    if not isinstance(suf, dict):
        notes.append("input_sufficiency_coerced_from_non_object")
        if isinstance(suf, bool):
            suf = {
                "required_fields_complete": suf,
                "current_context_requirement_met": suf,
                "missing_fields": [],
                "additional_questions": [],
            }
        else:
            suf = {
                "required_fields_complete": False,
                "current_context_requirement_met": bool(current_context),
                "missing_fields": [],
                "additional_questions": [],
            }
    data["input_sufficiency"] = {
        "required_fields_complete": bool(suf.get("required_fields_complete", False)),
        "current_context_requirement_met": bool(suf.get("current_context_requirement_met", False)),
        "missing_fields": [_safe_str(x) for x in _as_list(suf.get("missing_fields")) if _safe_str(x)],
        "additional_questions": [_safe_str(x) for x in _as_list(suf.get("additional_questions")) if _safe_str(x)],
    }

    # --- user_confirmation_view ---
    view = data.get("user_confirmation_view")
    if not isinstance(view, dict):
        notes.append("user_confirmation_view_coerced_from_non_object")
        view = {}
    # accept legacy keys
    unchosen = view.get("unchosen_path")
    if not unchosen:
        paths = _as_list(view.get("unchosen_paths"))
        unchosen = paths[0] if paths else ""
    data["user_confirmation_view"] = {
        "branch_period": _safe_str(view.get("branch_period")),
        "triggering_event": _safe_str(view.get("triggering_event") or view.get("what_happened")),
        "chosen_path": _safe_str(view.get("chosen_path")),
        "unchosen_path": _safe_str(unchosen),
        "actual_secondary_branches": [_safe_str(x) for x in _as_list(view.get("actual_secondary_branches")) if _safe_str(x)],
        "retrospective_counterfactuals": [_safe_str(x) for x in _as_list(view.get("retrospective_counterfactuals")) if _safe_str(x)],
        "present_questions": [_safe_str(x) for x in _as_list(view.get("present_questions")) if _safe_str(x)],
        "current_context": [_safe_str(x) for x in _as_list(view.get("current_context")) if _safe_str(x)] or current_context,
        "feelings": [_safe_str(x) for x in _as_list(view.get("feelings")) if _safe_str(x)],
        "hypotheses": [_safe_str(x) for x in _as_list(view.get("hypotheses")) if _safe_str(x)],
        "unknowns": [_safe_str(x) for x in _as_list(view.get("unknowns")) if _safe_str(x)],
        "central_thesis_preview": _safe_str(
            view.get("central_thesis_preview") or view.get("central_thesis")
        ),
        "observatory_lens_candidates": [
            _safe_str(x)
            for x in _as_list(view.get("observatory_lens_candidates") or view.get("observatory_candidates"))
            if _safe_str(x)
        ],
        "items_to_confirm": [
            _safe_str(x)
            for x in _as_list(view.get("items_to_confirm") or view.get("points_needing_confirmation"))
            if _safe_str(x)
        ],
    }

    # --- central_thesis ---
    thesis = data.get("central_thesis")
    if isinstance(thesis, str):
        notes.append("central_thesis_coerced_from_string")
        data["central_thesis"] = {
            "thesis_type": "",
            "statement": thesis,
            "pole_a": "",
            "pole_b": "",
            "supported_by": [],
            "risks": [],
            "validation_status": "pending",
        }
    elif not isinstance(thesis, dict):
        notes.append("central_thesis_defaulted")
        data["central_thesis"] = CentralThesis().model_dump(mode="json")

    # --- v1.1.1 selection / compression (empty defaults for Strict / older models) ---
    from app.parallel_life_deep_reading.models import (
        MeaningCompression,
        RelevantContextSelection,
    )

    if not isinstance(data.get("relevant_context_selection"), dict):
        notes.append("relevant_context_selection_defaulted")
        data["relevant_context_selection"] = RelevantContextSelection().model_dump(
            mode="json"
        )
    if not isinstance(data.get("meaning_compression"), dict):
        notes.append("meaning_compression_defaulted")
        data["meaning_compression"] = MeaningCompression().model_dump(mode="json")

    # --- branch_structure + later_branch normalization ---
    bs = data.get("branch_structure")
    if not isinstance(bs, dict):
        notes.append("branch_structure_defaulted")
        bs = {}
    else:
        bs = dict(bs)
    primary = bs.get("primary_branch")
    if not isinstance(primary, dict):
        primary = {}
    secondary_raw = bs.get("secondary_branches")
    if secondary_raw is None and bs.get("secondary_branch") is not None:
        secondary_raw = bs.get("secondary_branch")
        notes.append("migrated_legacy_secondary_branch")
    if secondary_raw is None and bs.get("actual_secondary_branch") is not None:
        secondary_raw = bs.get("actual_secondary_branch")
        notes.append("migrated_actual_secondary_branch_field")

    # Top-level later_branch string (legacy model shorthand)
    if isinstance(bs.get("later_branch"), str) and bs["later_branch"].strip():
        notes.append("normalized_top_level_later_branch_string")
        secondary_raw = list(_as_list(secondary_raw)) + [
            {
                "branch_type": "later_branch",
                "content": bs["later_branch"].strip(),
            }
        ]

    secondaries: list[dict[str, Any]] = []
    for i, item in enumerate(_as_list(secondary_raw)):
        if isinstance(item, str):
            secondaries.append(
                {
                    "id": f"sec_{i+1:03d}",
                    "classification": BranchClassification.actual_secondary_branch.value,
                    "description": item,
                    "explicit_evidence_ids": [],
                }
            )
            notes.append("normalized_secondary_string")
            continue
        if not isinstance(item, dict):
            continue
        classification_raw = _safe_str(item.get("classification") or item.get("branch_type"))
        # later_branch / missing classification + content → actual_secondary_branch shell
        if (
            classification_raw in {"later_branch", "actual_secondary_branch", ""}
            and (item.get("branch_type") == "later_branch" or item.get("content") or classification_raw == "later_branch")
            and classification_raw != BranchClassification.actual_secondary_branch.value
        ) or (
            "classification" not in item
            and item.get("branch_type") == "later_branch"
        ) or (
            "classification" not in item and item.get("content") and not item.get("description")
        ):
            notes.append("normalized_later_branch_variant")
            secondaries.append(
                {
                    "id": _safe_str(item.get("id")) or f"sec_{i+1:03d}",
                    "classification": BranchClassification.actual_secondary_branch.value,
                    "description": _safe_str(item.get("description") or item.get("content")),
                    "available_paths": [_safe_str(x) for x in _as_list(item.get("available_paths")) if _safe_str(x)],
                    "realized_path": _safe_str(item.get("realized_path")),
                    "unrealized_paths": [_safe_str(x) for x in _as_list(item.get("unrealized_paths")) if _safe_str(x)],
                    "explicit_evidence_ids": [
                        _safe_str(x)
                        for x in _as_list(
                            item.get("explicit_evidence_ids") or item.get("supported_by_fact_ids")
                        )
                        if _safe_str(x)
                    ],
                    "ambiguity_status": _safe_str(item.get("ambiguity_status")),
                    "present_relevance": _safe_str(item.get("present_relevance")),
                    "must_not_be_treated_as_historical_choice": False,
                }
            )
            continue
        classification = classification_raw or BranchClassification.actual_secondary_branch.value
        if classification not in {
            BranchClassification.actual_secondary_branch.value,
            BranchClassification.retrospective_counterfactual.value,
        }:
            notes.append(f"normalized_invalid_classification:{classification}")
            classification = BranchClassification.actual_secondary_branch.value
        secondaries.append(
            {
                "id": _safe_str(item.get("id")) or f"sec_{i+1:03d}",
                "classification": classification,
                "parent_branch_id": _safe_str(item.get("parent_branch_id")) or "primary",
                "description": _safe_str(item.get("description") or item.get("question") or item.get("content")),
                "available_paths": [_safe_str(x) for x in _as_list(item.get("available_paths")) if _safe_str(x)],
                "realized_path": _safe_str(item.get("realized_path")),
                "unrealized_paths": [_safe_str(x) for x in _as_list(item.get("unrealized_paths")) if _safe_str(x)],
                "explicit_evidence_ids": [
                    _safe_str(x)
                    for x in _as_list(
                        item.get("explicit_evidence_ids") or item.get("supported_by_fact_ids")
                    )
                    if _safe_str(x)
                ],
                "ambiguity_status": _safe_str(item.get("ambiguity_status")),
                "present_relevance": _safe_str(item.get("present_relevance")),
                "must_not_be_treated_as_historical_choice": bool(
                    item.get("must_not_be_treated_as_historical_choice", False)
                ),
            }
        )

    cf_raw = bs.get("retrospective_counterfactuals")
    if cf_raw is None and bs.get("retrospective_counterfactual") is not None:
        cf_raw = bs.get("retrospective_counterfactual")
        notes.append("migrated_legacy_counterfactual")
    counterfactuals: list[dict[str, Any]] = []
    for i, item in enumerate(_as_list(cf_raw)):
        if isinstance(item, str):
            counterfactuals.append(
                {
                    "id": f"cf_{i+1:03d}",
                    "classification": BranchClassification.retrospective_counterfactual.value,
                    "description": item,
                    "must_not_be_treated_as_historical_choice": True,
                    "explicit_evidence_ids": [],
                }
            )
            continue
        if not isinstance(item, dict):
            continue
        counterfactuals.append(
            {
                "id": _safe_str(item.get("id")) or f"cf_{i+1:03d}",
                "classification": BranchClassification.retrospective_counterfactual.value,
                "description": _safe_str(item.get("description") or item.get("question")),
                "explicit_evidence_ids": [
                    _safe_str(x) for x in _as_list(item.get("explicit_evidence_ids")) if _safe_str(x)
                ],
                "must_not_be_treated_as_historical_choice": True,
                "available_paths": [_safe_str(x) for x in _as_list(item.get("available_paths")) if _safe_str(x)],
                "realized_path": _safe_str(item.get("realized_path")),
                "unrealized_paths": [_safe_str(x) for x in _as_list(item.get("unrealized_paths")) if _safe_str(x)],
                "ambiguity_status": _safe_str(item.get("ambiguity_status")),
                "present_relevance": _safe_str(item.get("present_relevance")),
            }
        )

    data["branch_structure"] = {
        "primary_branch": {
            "period": _safe_str(primary.get("period") or primary.get("branch_point")),
            "triggering_event": _safe_str(
                primary.get("triggering_event") or primary.get("branch_point")
            ),
            "available_paths": [_safe_str(x) for x in _as_list(primary.get("available_paths")) if _safe_str(x)],
            "realized_path": _safe_str(primary.get("realized_path") or primary.get("chosen_path")),
            "unrealized_paths": [
                _safe_str(x)
                for x in _as_list(primary.get("unrealized_paths") or primary.get("unchosen_paths"))
                if _safe_str(x)
            ],
            "constraints": [_safe_str(x) for x in _as_list(primary.get("constraints")) if _safe_str(x)],
            "supporting_fact_ids": [
                _safe_str(x)
                for x in _as_list(
                    primary.get("supporting_fact_ids") or primary.get("chosen_path_fact_ids")
                )
                if _safe_str(x)
            ],
            "ambiguities": [_safe_str(x) for x in _as_list(primary.get("ambiguities")) if _safe_str(x)],
        },
        "realized_outcomes": [_safe_str(x) for x in _as_list(bs.get("realized_outcomes")) if _safe_str(x)],
        "secondary_branches": secondaries,
        "retrospective_counterfactuals": counterfactuals,
        "present_question_ids": [_safe_str(x) for x in _as_list(bs.get("present_question_ids")) if _safe_str(x)],
    }

    # --- wrappers ---
    def _itemize(value: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for item in _as_list(value):
            if isinstance(item, str) and item.strip():
                out.append({"content": item.strip(), "support_ids": []})
            elif isinstance(item, dict):
                # Legacy bags: {lost_choices: [...]} / {protected_choices: [...]}
                legacy_lists = []
                for lk in (
                    "lost_choices",
                    "protected_choices",
                    "items",
                    "candidates",
                    "residues",
                ):
                    if lk in item and isinstance(item[lk], list) and "content" not in item:
                        legacy_lists.extend(item[lk])
                if legacy_lists:
                    for legacy in legacy_lists:
                        if isinstance(legacy, str) and legacy.strip():
                            out.append({"content": legacy.strip(), "support_ids": []})
                        elif isinstance(legacy, dict):
                            out.append(
                                {
                                    "content": _safe_str(
                                        legacy.get("content") or legacy.get("text")
                                    ),
                                    "support_ids": [
                                        _safe_str(x)
                                        for x in _as_list(legacy.get("support_ids"))
                                        if _safe_str(x)
                                    ],
                                }
                            )
                    continue
                out.append(
                    {
                        "content": _safe_str(item.get("content") or item.get("text")),
                        "loss_type": _safe_str(item.get("loss_type")),
                        "support_ids": [
                            _safe_str(x) for x in _as_list(item.get("support_ids")) if _safe_str(x)
                        ],
                        "certainty": _safe_str(item.get("certainty")) or "qualified",
                        "allowed_wording_strength": _safe_str(item.get("allowed_wording_strength"))
                        or "qualified",
                        "causality_status": _safe_str(item.get("causality_status")) or "observed",
                        "allowed_statement_strength": _safe_str(
                            item.get("allowed_statement_strength")
                        )
                        or "supported",
                        "inference_distance": _safe_str(item.get("inference_distance")) or "near",
                        "present_life_domain": _safe_str(item.get("present_life_domain")),
                        "overreach_risk": _safe_str(item.get("overreach_risk")),
                        "advances_manuscript": bool(item.get("advances_manuscript", True)),
                    }
                )
        return out

    def wrap_items(value: Any, notes_key: str) -> dict[str, Any]:
        if isinstance(value, dict) and "items" in value:
            return {"items": _itemize(value.get("items"))}
        if isinstance(value, list):
            notes.append(notes_key)
            return {"items": _itemize(value)}
        if isinstance(value, dict):
            notes.append(notes_key + "_from_dict")
            # Prefer expanding known legacy list keys at root of wrapper
            expanded: list[Any] = []
            for lk in ("lost_choices", "protected_choices", "candidates", "residues"):
                if lk in value:
                    expanded.extend(_as_list(value.get(lk)))
            if expanded:
                return {"items": _itemize(expanded)}
            return {"items": _itemize([value])}
        return {"items": []}

    data["lost_structure"] = wrap_items(data.get("lost_structure"), "lost_structure_wrapped")
    data["protected_structure"] = wrap_items(
        data.get("protected_structure"), "protected_structure_wrapped"
    )

    # Residue — preserve past/present anchors; do not coerce question-only shells.
    def _normalize_residue_item(item: Any, idx: int) -> dict[str, Any] | None:
        if isinstance(item, str) and item.strip():
            return {
                "residue_statement": item.strip(),
                "content": item.strip(),
                "past_anchor_ids": [],
                "present_anchor_ids": [],
                "support_ids": [],
                "inference_distance": "near",
                "present_life_domain": "",
                "overreach_risk": "",
                "advances_manuscript": True,
            }
        if not isinstance(item, dict):
            return None
        statement = _safe_str(
            item.get("residue_statement") or item.get("content") or item.get("text")
        )
        past = [_safe_str(x) for x in _as_list(item.get("past_anchor_ids")) if _safe_str(x)]
        present = [
            _safe_str(x) for x in _as_list(item.get("present_anchor_ids")) if _safe_str(x)
        ]
        support = [_safe_str(x) for x in _as_list(item.get("support_ids")) if _safe_str(x)]
        return {
            "residue_statement": statement,
            "content": statement,
            "past_anchor_ids": past,
            "present_anchor_ids": present,
            "support_ids": support or list(dict.fromkeys([*past, *present])),
            "inference_distance": _safe_str(item.get("inference_distance")) or "near",
            "present_life_domain": _safe_str(item.get("present_life_domain")),
            "overreach_risk": _safe_str(item.get("overreach_risk")),
            "advances_manuscript": bool(item.get("advances_manuscript", True)),
        }

    rc_raw = data.get("residue_candidates")
    rc_items_raw: list[Any] = []
    if isinstance(rc_raw, dict) and "items" in rc_raw:
        rc_items_raw = _as_list(rc_raw.get("items"))
    elif isinstance(rc_raw, list):
        notes.append("residue_candidates_wrapped")
        rc_items_raw = rc_raw
    elif isinstance(rc_raw, dict):
        notes.append("residue_candidates_wrapped_from_dict")
        rc_items_raw = _as_list(rc_raw.get("candidates") or rc_raw.get("residues") or [rc_raw])
    residue_items: list[dict[str, Any]] = []
    for i, item in enumerate(rc_items_raw):
        normalized = _normalize_residue_item(item, i)
        if normalized and normalized.get("residue_statement"):
            residue_items.append(normalized)
    data["residue_candidates"] = {"items": residue_items}

    # lenses
    sel = data.get("selected_observatory_lenses")
    evaluated = data.get("evaluated_observatory_lenses") or data.get("evaluated_lenses")
    if isinstance(sel, dict) and ("selected" in sel or "evaluated" in sel):
        data["selected_observatory_lenses"] = {
            "evaluated": _as_list(sel.get("evaluated") or evaluated),
            "selected": _as_list(sel.get("selected")),
        }
    else:
        notes.append("observatory_selection_wrapped")
        data["selected_observatory_lenses"] = {
            "evaluated": _as_list(evaluated if evaluated is not None else sel),
            "selected": _as_list(sel) if not isinstance(sel, dict) else [],
        }

    # outline — coerce string sections into EditorialSectionPlan shells
    def _section_from_any(item: Any, idx: int) -> dict[str, Any]:
        if isinstance(item, str) and item.strip():
            return {
                "internal_id": f"sec_plan_{idx+1:03d}",
                "public_heading": item.strip(),
                "required": True,
                "new_meaning": "",
                "allowed_boundary_ids": [],
                "forbidden_inferences": [],
                "previous_section_difference": "",
                "next_section_transition": "",
                "reserved_fact_ids": [],
                "prohibited_repeat_ids": [],
                "relative_weight": 1.0,
            }
        if isinstance(item, dict):
            return {
                "internal_id": _safe_str(item.get("internal_id")) or f"sec_plan_{idx+1:03d}",
                "public_heading": _safe_str(
                    item.get("public_heading") or item.get("heading") or item.get("title")
                ),
                "required": bool(item.get("required", True)),
                "new_meaning": _safe_str(item.get("new_meaning")),
                "allowed_boundary_ids": [
                    _safe_str(x) for x in _as_list(item.get("allowed_boundary_ids")) if _safe_str(x)
                ],
                "forbidden_inferences": [
                    _safe_str(x) for x in _as_list(item.get("forbidden_inferences")) if _safe_str(x)
                ],
                "previous_section_difference": _safe_str(item.get("previous_section_difference")),
                "next_section_transition": _safe_str(item.get("next_section_transition")),
                "reserved_fact_ids": [
                    _safe_str(x) for x in _as_list(item.get("reserved_fact_ids")) if _safe_str(x)
                ],
                "prohibited_repeat_ids": [
                    _safe_str(x) for x in _as_list(item.get("prohibited_repeat_ids")) if _safe_str(x)
                ],
                "relative_weight": float(item["relative_weight"])
                if isinstance(item.get("relative_weight"), (int, float))
                else 1.0,
            }
        return {
            "internal_id": f"sec_plan_{idx+1:03d}",
            "public_heading": "",
            "required": True,
            "new_meaning": "",
            "allowed_boundary_ids": [],
            "forbidden_inferences": [],
            "previous_section_difference": "",
            "next_section_transition": "",
            "reserved_fact_ids": [],
            "prohibited_repeat_ids": [],
            "relative_weight": 1.0,
        }

    outline = data.get("editorial_outline")
    if isinstance(outline, dict) and "sections" in outline:
        sections_raw = _as_list(outline.get("sections"))
    else:
        notes.append("editorial_outline_wrapped")
        sections_raw = _as_list(outline)
    if any(isinstance(x, str) for x in sections_raw):
        notes.append("editorial_outline_sections_coerced_from_strings")
    data["editorial_outline"] = {
        "sections": [_section_from_any(x, i) for i, x in enumerate(sections_raw)]
    }

    # repetition map
    rpm = data.get("repetition_prevention_map")
    entries: list[dict[str, Any]] = []
    if isinstance(rpm, dict) and isinstance(rpm.get("entries"), list):
        entries = [x for x in rpm["entries"] if isinstance(x, dict)]
    elif isinstance(rpm, dict):
        notes.append("repetition_map_from_dict")
        entries = [{"key": str(k), "ids": [_safe_str(i) for i in _as_list(v)]} for k, v in rpm.items()]
    data["repetition_prevention_map"] = {"entries": entries}

    # rebranch
    rb = data.get("rebranch_design")
    if isinstance(rb, dict) and "directions" in rb:
        directions = _as_list(rb.get("directions"))
    elif isinstance(rb, list):
        notes.append("rebranch_design_wrapped_list")
        directions = rb
    elif isinstance(rb, dict):
        notes.append("rebranch_design_wrapped_single_object")
        directions = [rb]
    else:
        directions = []
    cleaned_directions: list[dict[str, Any]] = []
    for i, d in enumerate(directions):
        if isinstance(d, str) and d.strip():
            notes.append("rebranch_direction_from_string")
            cleaned_directions.append(
                {
                    "id": f"rb_{i+1:03d}",
                    "source_meaning": d.strip(),
                    "current_receiver": "",
                    "branch_specific_form": "",
                    "support_ids": [],
                    "genericity_score": 2,
                }
            )
            continue
        if not isinstance(d, dict):
            continue
        g = d.get("genericity_score", 2)
        if isinstance(g, str) and g.strip().isdigit():
            g = int(g.strip())
        # Keep invalid ints so strict revalidate can fail → schema repair;
        # drop non-numeric junk without AttributeError.
        if not isinstance(g, int):
            notes.append("rebranch_direction_dropped_non_int_genericity")
            continue
        cleaned_directions.append(
            {
                "id": _safe_str(d.get("id")) or f"rb_{i+1:03d}",
                "source_meaning": _safe_str(d.get("source_meaning")),
                "current_receiver": _safe_str(d.get("current_receiver")),
                "branch_specific_form": _safe_str(d.get("branch_specific_form")),
                "support_ids": [_safe_str(x) for x in _as_list(d.get("support_ids")) if _safe_str(x)],
                "genericity_score": g,
                "invented_scene_used": bool(d.get("invented_scene_used", False)),
                "risks": [_safe_str(x) for x in _as_list(d.get("risks")) if _safe_str(x)],
                "publishable": bool(d.get("publishable", False)),
                "selected_for_manuscript": bool(d.get("selected_for_manuscript", False)),
            }
        )
    data["rebranch_design"] = {"directions": cleaned_directions}

    # additional questions
    aq = data.get("additional_questions")
    if isinstance(aq, dict) and "questions" in aq:
        data["additional_questions"] = {
            "required": bool(aq.get("required", False)),
            "questions": [_safe_str(x) for x in _as_list(aq.get("questions")) if _safe_str(x)],
        }
    else:
        notes.append("additional_questions_wrapped")
        qs = [_safe_str(x) for x in _as_list(aq) if _safe_str(x)]
        data["additional_questions"] = {"required": bool(qs), "questions": qs}

    # sensitive domain
    sda = data.get("sensitive_domain_analysis")
    if isinstance(sda, dict) and "domains" in sda:
        data["sensitive_domain_analysis"] = {
            "domains": [_safe_str(x) for x in _as_list(sda.get("domains")) if _safe_str(x)],
            "notes": [_safe_str(x) for x in _as_list(sda.get("notes")) if _safe_str(x)],
            "clarification_required": bool(sda.get("clarification_required", False)),
        }
    else:
        notes.append("sensitive_domain_wrapped")
        data["sensitive_domain_analysis"] = {
            "domains": [_safe_str(x) for x in _as_list(sda) if _safe_str(x)],
            "notes": [],
            "clarification_required": False,
        }

    # source coverage
    sc = data.get("source_coverage")
    if not isinstance(sc, dict):
        notes.append("source_coverage_defaulted")
        sc = {}
    data["source_coverage"] = {
        "branch_period": bool(sc.get("branch_period", False)),
        "triggering_event": bool(sc.get("triggering_event", False)),
        "chosen_path": bool(sc.get("chosen_path", False)),
        "unchosen_path": bool(sc.get("unchosen_path", False)),
        "present_question": bool(sc.get("present_question", False)),
        "current_context": bool(sc.get("current_context", False)),
    }

    # validation object
    val = data.get("validation")
    if not isinstance(val, dict):
        data["validation"] = Call1Validation().model_dump(mode="json")
    else:
        data["validation"] = {
            "actual_secondary_rejected": [_safe_str(x) for x in _as_list(val.get("actual_secondary_rejected"))],
            "lenses_rejected": [_safe_str(x) for x in _as_list(val.get("lenses_rejected"))],
            "questions_not_converted_to_facts": bool(val.get("questions_not_converted_to_facts", True)),
            "hypotheses_not_converted_to_facts": bool(val.get("hypotheses_not_converted_to_facts", True)),
            "notes": [_safe_str(x) for x in _as_list(val.get("notes"))],
            "source_coverage_missing": [_safe_str(x) for x in _as_list(val.get("source_coverage_missing"))],
        }

    # status
    status = data.get("status")
    try:
        data["status"] = GenerationStatus(status).value if status else GenerationStatus.ready_for_user_confirmation.value
    except Exception:
        data["status"] = GenerationStatus.ready_for_user_confirmation.value

    return data, notes


def _validation_error_paths(exc: ValidationError) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    paths: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        paths.append(loc)
        errors.append(f"{loc}: {err.get('msg')}")
    return errors, paths


def _build_call1_response(
    payload: Call1LLMPayload,
    *,
    notes: list[str],
    repair_attempted: bool,
    repair_succeeded: bool,
    source_text: str,
    input_corpus: str = "",
    context_pack: Any | None = None,
    deep_reading_mode: str = "strict",
    prompt_version: str | None = None,
) -> Call1Response:
    result = Call1Response(
        **payload.model_dump(mode="python"),
        prompt_version=prompt_version or CALL_1_PROMPT_VERSION,
        schema_version=CALL_1_SCHEMA_VERSION,
        parse_diagnostics=Call1ParseDiagnostics(
            normalization_applied=notes,
            repair_attempted=repair_attempted,
            repair_succeeded=repair_succeeded,
            raw_response_saved_in_dev_only=bool(
                os.environ.get("DEEP_READING_DEV_DIAGNOSTICS", "").lower()
                in {"1", "true", "yes"}
            ),
        ),
    )
    return apply_call1_runtime_gates(
        result,
        source_text=source_text,
        input_corpus=input_corpus or source_text,
        context_pack=context_pack,
        deep_reading_mode=deep_reading_mode,
    )


def parse_call1_payload(
    data: Any,
    *,
    source_text: str,
    repair_attempted: bool = False,
    repair_succeeded: bool = False,
    input_corpus: str = "",
    context_pack: Any | None = None,
    deep_reading_mode: str = "strict",
    prompt_version: str | None = None,
) -> Call1Response:
    """
    Layered parse:
    1) strict validate
    2) normalize known variants
    3) revalidate
    Never raises AttributeError — raises Call1SchemaError instead.
    """
    notes: list[str] = []
    try:
        # 1) strict
        try:
            payload = Call1LLMPayload.model_validate(data)
            return _build_call1_response(
                payload,
                notes=[],
                repair_attempted=repair_attempted,
                repair_succeeded=repair_succeeded,
                source_text=source_text,
                input_corpus=input_corpus,
                context_pack=context_pack,
                deep_reading_mode=deep_reading_mode,
                prompt_version=prompt_version,
            )
        except ValidationError as strict_exc:
            strict_errs, strict_paths = _validation_error_paths(strict_exc)
            # 2) normalize + 3) revalidate
            try:
                normalized, notes = normalize_raw_call1_dict(data, source_text=source_text)
                payload = Call1LLMPayload.model_validate(normalized)
                return _build_call1_response(
                    payload,
                    notes=notes,
                    repair_attempted=repair_attempted,
                    repair_succeeded=repair_succeeded,
                    source_text=source_text,
                    input_corpus=input_corpus,
                    context_pack=context_pack,
                    deep_reading_mode=deep_reading_mode,
                    prompt_version=prompt_version,
                )
            except ValidationError as norm_exc:
                errs, paths = _validation_error_paths(norm_exc)
                raise Call1SchemaError(
                    "Call 1 schema validation failed",
                    diagnostics=Call1ParseDiagnostics(
                        validation_errors=[
                            *[f"strict:{e}" for e in strict_errs],
                            *[f"normalized:{e}" for e in errs],
                        ],
                        offending_paths=list(dict.fromkeys([*strict_paths, *paths])),
                        repair_attempted=repair_attempted,
                        repair_succeeded=False,
                        normalization_applied=notes,
                    ),
                ) from norm_exc
    except Call1SchemaError:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise Call1SchemaError(
            f"Call 1 parse failed: {type(exc).__name__}",
            diagnostics=Call1ParseDiagnostics(
                validation_errors=[f"{type(exc).__name__}: {exc}"],
                offending_paths=["<root>"],
                repair_attempted=repair_attempted,
                repair_succeeded=False,
                normalization_applied=notes,
            ),
        ) from exc


def run_call1_grounding(
    source_text: str,
    *,
    clarifications: dict[str, Any] | None = None,
    editorial_context: dict[str, Any] | None = None,
    answers_to_additional_questions: dict[str, str] | None = None,
    deep_reading_mode: str = "strict",
    context_pack: Any | None = None,
) -> Call1Response:
    """Run Call 1. Strict uses v1.0.3 prompts; Contextual (v1.1-exp) uses v1.1.0 prompts."""
    from app.parallel_life_deep_reading.context_pack import (
        CALL_1_PROMPT_VERSION_V11,
        ContextPack,
        DeepReadingMode,
        pack_corpus_text,
        resolve_effective_mode,
        serialize_pack_for_prompt,
    )

    pack: ContextPack | None = None
    if isinstance(context_pack, ContextPack):
        pack = context_pack
    elif isinstance(context_pack, dict):
        pack = ContextPack.model_validate(context_pack)

    mode = resolve_effective_mode(requested_mode=deep_reading_mode, pack=pack)
    use_v11 = mode == DeepReadingMode.contextual

    observatory_prefill: dict[str, Any] | None = None
    observatory_bundle = None
    if use_v11:
        from app.parallel_life_deep_reading.observatory_core import (
            build_observatory_core_bundle,
            serialize_bundle_for_prompt,
        )

        observatory_bundle = build_observatory_core_bundle(source_text, pack)
        observatory_prefill = serialize_bundle_for_prompt(observatory_bundle)

    if use_v11:
        system = call1_system_prompt_v11()
        user = call1_user_prompt_v11(
            source_text,
            clarifications or {},
            editorial_context or {},
            answers_to_additional_questions or {},
            context_pack_approved_items=serialize_pack_for_prompt(pack),
            observatory_core_prefill=observatory_prefill,
        )
        prompt_version = CALL_1_PROMPT_VERSION_V11
    else:
        system = call1_system_prompt()
        user = call1_user_prompt(
            source_text,
            clarifications or {},
            editorial_context or {},
            answers_to_additional_questions or {},
        )
        prompt_version = CALL_1_PROMPT_VERSION

    response_format = openai_response_format()
    input_corpus = build_input_corpus(
        source_text,
        clarifications=clarifications,
        editorial_context=editorial_context,
        answers=answers_to_additional_questions,
    )
    if use_v11:
        pack_text = pack_corpus_text(pack)
        if pack_text:
            input_corpus = f"{input_corpus}\n{pack_text}".strip()

    raw = chat_json_schema(system, user, response_format, max_tokens=5000, temperature=0.2)

    # Persist raw in dev only (no secrets; may contain personal narrative — gated).
    if os.environ.get("DEEP_READING_DEV_DIAGNOSTICS", "").lower() in {"1", "true", "yes"}:
        try:
            os.makedirs("e2e_reports/deep-reading-call1-raw", exist_ok=True)
        except Exception:
            pass

    def _stamp(result: Call1Response) -> Call1Response:
        if getattr(result, "prompt_version", None) != prompt_version:
            return result.model_copy(update={"prompt_version": prompt_version})
        return result

    try:
        return _stamp(
            parse_call1_payload(
                raw,
                source_text=source_text,
                input_corpus=input_corpus,
                context_pack=pack if use_v11 else None,
                deep_reading_mode=mode.value,
                prompt_version=prompt_version,
            )
        )
    except Call1SchemaError as first_err:
        # One schema-repair retry only.
        repair_user = call1_repair_user_prompt(
            previous_response=raw if isinstance(raw, dict) else {"raw": str(raw)},
            validation_errors=first_err.diagnostics.validation_errors,
            expected_schema=call1_json_schema(),
        )
        repaired = chat_json_schema(
            system,
            repair_user,
            response_format,
            max_tokens=5000,
            temperature=0.0,
        )
        try:
            return _stamp(
                parse_call1_payload(
                    repaired,
                    source_text=source_text,
                    repair_attempted=True,
                    repair_succeeded=True,
                    input_corpus=input_corpus,
                    context_pack=pack if use_v11 else None,
                    deep_reading_mode=mode.value,
                    prompt_version=prompt_version,
                )
            )
        except Call1SchemaError as second_err:
            diag = second_err.diagnostics.model_copy(
                update={
                    "repair_attempted": True,
                    "repair_succeeded": False,
                    "validation_errors": [
                        *first_err.diagnostics.validation_errors,
                        *second_err.diagnostics.validation_errors,
                    ],
                }
            )
            # Return typed failure result for service to surface without crashing.
            failed = Call1Response(
                status=GenerationStatus.schema_validation_failed,
                prompt_version=prompt_version,
                schema_version=CALL_1_SCHEMA_VERSION,
                parse_diagnostics=diag,
                validation=Call1Validation(
                    notes=["schema_validation_failed_after_repair"],
                ),
            )
            raise Call1SchemaError(
                "Call 1 schema validation failed after one repair attempt",
                diagnostics=diag,
                partial=failed,
            ) from second_err
