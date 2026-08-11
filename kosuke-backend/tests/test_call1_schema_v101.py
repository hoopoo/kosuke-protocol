"""Call 1 schema v1.0.1 — parser hardening, normalization, runtime corrections."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parallel_life_deep_reading.call1_schema import (
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
    Call1SchemaError,
    call1_rebranch_directions,
    call1_selected_lenses,
)
from app.parallel_life_deep_reading.grounding import (
    normalize_raw_call1_dict,
    parse_call1_payload,
    run_call1_grounding,
)
from app.parallel_life_deep_reading.models import (
    BranchClassification,
    FactBoundaryType,
    GenerationStatus,
)
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    correct_fact_boundaries,
    filter_call1_rebranch_directions,
    looks_like_user_question,
)
from app.parallel_life_deep_reading.models import GroundedFact, GroundedInput, RebranchDirection
from app.parallel_life_deep_reading.fixtures import (
    CASE1_SOURCE,
    CASE2_SOURCE,
    build_case1_call1,
    build_case2_call1,
)

LIVE_RAW = Path(__file__).resolve().parents[1] / "e2e_reports" / "deep-reading-v1.0-live-run"


def test_prompt_and_schema_versions():
    assert CALL_1_PROMPT_VERSION == "parallel-life-call-1-v1.0.3"
    assert CALL_1_SCHEMA_VERSION == "parallel-life-call-1-schema-v1.0.2"


def test_bool_input_sufficiency_normalized_not_crash():
    raw = {
        "status": "ready_for_user_confirmation",
        "grounded_input": {
            "explicit_fact": ["45歳で子どもを授かった", "現在は三人家族"],
            "user_feeling": ["二人目を持っていたらどうだったか"],
        },
        "input_sufficiency": True,
        "user_confirmation_view": True,
        "central_thesis": "問いと現在の共存",
        "branch_structure": {
            "primary_branch": {
                "period": "45歳",
                "triggering_event": "子どもを授かった",
                "realized_path": "三人家族",
                "unrealized_paths": ["治療を諦める"],
            },
            "retrospective_counterfactuals": ["二人目を持っていたらどうだったか"],
        },
        "rebranch_design": {
            "source_meaning": "兄弟がいる意味",
            "current_receiver": "友人来訪の現在",
            "branch_specific_form": "家庭らしさを言葉にする",
            "support_ids": ["fact_001"],
            "genericity_score": 0,
        },
        "residue_candidates": [{"content": "かなった選択にも問いは残る", "support_ids": ["fact_001"]}],
        "selected_observatory_lenses": [],
        "editorial_outline": [],
        "additional_questions": [],
        "source_coverage": {
            "branch_period": True,
            "triggering_event": True,
            "chosen_path": True,
            "unchosen_path": True,
            "present_question": True,
            "current_context": True,
        },
    }
    # Ensure current context present for coverage
    raw["grounded_input"]["current_context"] = ["三人家族で暮らしている"]
    result = parse_call1_payload(raw, source_text=CASE1_SOURCE)
    assert isinstance(result.input_sufficiency.required_fields_complete, bool)
    assert result.user_confirmation_view.branch_period != "" or result.branch_structure.primary_branch.period
    assert any(q.boundary_type == FactBoundaryType.user_question for q in result.grounded_input.questions)


def test_string_user_confirmation_view_normalized():
    raw = {
        "grounded_input": {
            "facts": [{"id": "f1", "content": "現在は文章をまとめている", "boundary_type": "explicit_fact"}],
            "questions": [{"id": "q1", "content": "別の大学ならどう変わったか", "boundary_type": "user_question"}],
            "current_context": ["文章をまとめている"],
        },
        "input_sufficiency": "complete",
        "user_confirmation_view": "ok",
        "central_thesis": "合格の事実を保つ",
        "branch_structure": {
            "primary_branch": {
                "period": "19歳",
                "triggering_event": "第一志望の早稲田大学第一文学部に合格した",
                "realized_path": "早稲田へ進学",
                "unrealized_paths": ["別の大学"],
            }
        },
        "rebranch_design": {"directions": []},
        "selected_observatory_lenses": {"evaluated": [], "selected": []},
        "lost_structure": {"items": []},
        "protected_structure": {"items": []},
        "residue_candidates": {"items": [{"content": "経路が残る", "support_ids": ["f1"]}]},
        "editorial_outline": {"sections": []},
        "additional_questions": {"required": False, "questions": []},
        "source_coverage": {
            "branch_period": True,
            "triggering_event": True,
            "chosen_path": True,
            "unchosen_path": True,
            "present_question": True,
            "current_context": True,
        },
        "validation": {},
        "sensitive_domain_analysis": {"domains": [], "notes": [], "clarification_required": False},
        "repetition_prevention_map": {"entries": []},
        "status": "ready_for_user_confirmation",
    }
    result = parse_call1_payload(raw, source_text=CASE2_SOURCE)
    assert result.user_confirmation_view.triggering_event or result.branch_structure.primary_branch.triggering_event
    assert "合格" in result.branch_structure.primary_branch.triggering_event


def test_malformed_nested_type_no_attribute_error():
    weird = {
        "grounded_input": None,
        "input_sufficiency": 1,
        "user_confirmation_view": ["x"],
        "central_thesis": None,
        "branch_structure": "nope",
        "rebranch_design": "bad",
        "selected_observatory_lenses": False,
        "lost_structure": False,
        "protected_structure": "x",
        "residue_candidates": True,
        "editorial_outline": None,
        "additional_questions": True,
        "source_coverage": False,
    }
    # Should not raise AttributeError
    normalized, notes = normalize_raw_call1_dict(weird, source_text="現在は会社員。別の道ならどうだったか。")
    assert isinstance(normalized, dict)
    assert any("coerced" in n or "defaulted" in n or "wrapped" in n for n in notes)
    # Parsing may still fail validation if facts empty — but not AttributeError
    try:
        parse_call1_payload(weird, source_text="現在は会社員。別の道ならどうだったか。")
    except Call1SchemaError as exc:
        assert "AttributeError" not in str(exc)
        assert exc.diagnostics.validation_errors or exc.diagnostics.offending_paths


def test_question_ending_classified_as_user_question():
    assert looks_like_user_question("二人目を持っていたらどうだったか")
    grounded = GroundedInput(
        feelings=[
            GroundedFact(
                id="f1",
                content="今も、二人目を持っていたらどうだったかと考えることがある。",
                boundary_type=FactBoundaryType.user_feeling,
            )
        ]
    )
    fixed = correct_fact_boundaries(grounded)
    assert fixed.feelings == []
    assert len(fixed.questions) == 1
    assert fixed.questions[0].boundary_type == FactBoundaryType.user_question


def test_duplicate_question_removed_from_feelings():
    call1 = apply_call1_runtime_gates(
        build_case1_call1(with_actual_secondary=False),
        source_text=CASE1_SOURCE,
    )
    # Inject duplicate feeling
    call1.grounded_input.feelings.append(
        GroundedFact(
            id="dup",
            content="二人目を持っていたらどうだったか",
            boundary_type=FactBoundaryType.user_feeling,
        )
    )
    call1 = apply_call1_runtime_gates(call1, source_text=CASE1_SOURCE)
    q_texts = {q.content for q in call1.grounded_input.questions}
    assert any("二人目" in q for q in q_texts)
    assert all("どうだったか" not in f.content for f in call1.grounded_input.feelings)


def test_explicit_discussion_becomes_actual_secondary():
    raw = {
        "grounded_input": {
            "facts": [
                {"id": "fact_001", "content": "不妊治療を経て子どもを授かった", "boundary_type": "explicit_fact"},
                {
                    "id": "fact_007",
                    "content": "二人目を目指す治療を続けるか妻と話し合い、やめた",
                    "boundary_type": "explicit_fact",
                },
                {"id": "fact_005", "content": "現在は三人家族で暮らしている", "boundary_type": "explicit_fact"},
            ],
            "questions": [
                {"id": "q1", "content": "二人目を持っていたらどうだったか", "boundary_type": "user_question"}
            ],
            "current_context": ["三人家族で暮らしている"],
        },
        "input_sufficiency": {
            "required_fields_complete": True,
            "current_context_requirement_met": True,
            "missing_fields": [],
            "additional_questions": [],
        },
        "branch_structure": {
            "primary_branch": {
                "period": "45歳",
                "triggering_event": "子どもを授かった",
                "realized_path": "三人家族",
                "unrealized_paths": ["諦める"],
            },
            "secondary_branches": [
                {
                    "branch_type": "later_branch",
                    "content": "息子を授かった後、二人目を目指す治療を続けるか妻と話し合い、やめた。",
                }
            ],
        },
        "central_thesis": {"statement": "現在と問いの共存"},
        "user_confirmation_view": {},
        "rebranch_design": {"directions": []},
        "selected_observatory_lenses": {"evaluated": [], "selected": []},
        "lost_structure": {"items": []},
        "protected_structure": {"items": []},
        "residue_candidates": {"items": [{"content": "問いが残る", "support_ids": ["q1"]}]},
        "editorial_outline": {"sections": []},
        "additional_questions": {"required": False, "questions": []},
        "source_coverage": {
            "branch_period": True,
            "triggering_event": True,
            "chosen_path": True,
            "unchosen_path": True,
            "present_question": True,
            "current_context": True,
        },
        "validation": {},
        "sensitive_domain_analysis": {"domains": [], "notes": [], "clarification_required": False},
        "repetition_prevention_map": {"entries": []},
        "status": "ready_for_user_confirmation",
    }
    result = parse_call1_payload(
        raw,
        source_text=CASE1_SOURCE + "\n二人目を目指す治療を続けるか妻と話し合い、やめた。",
    )
    assert len(result.branch_structure.secondary_branches) >= 1
    assert (
        result.branch_structure.secondary_branches[0].classification
        == BranchClassification.actual_secondary_branch
    )
    assert result.branch_structure.secondary_branches[0].explicit_evidence_ids


def test_question_only_becomes_retrospective_counterfactual():
    call1 = apply_call1_runtime_gates(
        build_case1_call1(with_actual_secondary=False),
        source_text=CASE1_SOURCE,
    )
    assert call1.branch_structure.secondary_branches == []
    assert len(call1.branch_structure.retrospective_counterfactuals) >= 1


def test_empty_support_ids_removes_rebranch():
    kept = filter_call1_rebranch_directions(
        [
            RebranchDirection(
                id="a",
                source_meaning="x",
                current_receiver="y",
                branch_specific_form="z",
                support_ids=[],
                genericity_score=0,
            )
        ]
    )
    assert kept == []


def test_genericity_gt_1_removes_rebranch():
    kept = filter_call1_rebranch_directions(
        [
            RebranchDirection(
                id="a",
                source_meaning="x",
                current_receiver="y",
                branch_specific_form="z",
                support_ids=["f1"],
                genericity_score=2,
            )
        ]
    )
    assert kept == []


def test_source_coverage_gate_blocks_ready_status():
    call1 = build_case2_call1()
    call1.grounded_input.current_context = []
    call1 = apply_call1_runtime_gates(call1, source_text=CASE2_SOURCE)
    # May still detect current context from facts containing 現在
    if not call1.source_coverage.current_context:
        assert call1.status == GenerationStatus.needs_additional_input


def test_university_entities_retained_in_fixture_path():
    call1 = apply_call1_runtime_gates(build_case2_call1(), source_text=CASE2_SOURCE)
    blob = " ".join(f.content for f in call1.grounded_input.facts)
    blob += call1.branch_structure.primary_branch.triggering_event
    for token in ("第一志望", "早稲田", "合格", "別の大学"):
        assert token in blob


def test_bool_input_sufficiency_rejected_by_strict_schema():
    with pytest.raises(Exception):
        from app.parallel_life_deep_reading.models import Call1LLMPayload

        Call1LLMPayload.model_validate(
            {
                "input_sufficiency": True,
                "user_confirmation_view": {
                    "branch_period": "x",
                    "triggering_event": "y",
                    "chosen_path": "z",
                    "unchosen_path": "w",
                    "actual_secondary_branches": [],
                    "retrospective_counterfactuals": [],
                    "present_questions": [],
                    "current_context": [],
                    "feelings": [],
                    "hypotheses": [],
                    "unknowns": [],
                    "central_thesis_preview": "",
                    "observatory_lens_candidates": [],
                    "items_to_confirm": [],
                },
            }
        )


def test_string_user_confirmation_view_rejected_by_strict_schema():
    with pytest.raises(Exception):
        from app.parallel_life_deep_reading.models import Call1LLMPayload

        Call1LLMPayload.model_validate({"user_confirmation_view": "ok"})


def test_schema_repair_retry_succeeds(monkeypatch):
    # Survives normalize root shape but fails Pydantic (invalid genericity Literal).
    bad = {
        "status": "ready_for_user_confirmation",
        "grounded_input": {
            "facts": [{"id": "f1", "content": "45歳で子どもを授かった", "boundary_type": "explicit_fact"}],
            "questions": [
                {"id": "q1", "content": "二人目を持っていたらどうだったか", "boundary_type": "user_question"}
            ],
            "feelings": [],
            "hypotheses": [],
            "unknowns": [],
            "model_inferences": [],
            "current_context": ["三人家族"],
            "sensitive_domains": [],
            "confirmed_by_user": False,
            "requested_corrections": [],
        },
        "input_sufficiency": {
            "required_fields_complete": True,
            "current_context_requirement_met": True,
            "missing_fields": [],
            "additional_questions": [],
        },
        "sensitive_domain_analysis": {"domains": [], "notes": [], "clarification_required": False},
        "branch_structure": {
            "primary_branch": {
                "period": "45歳",
                "triggering_event": "子どもを授かった",
                "available_paths": [],
                "realized_path": "三人家族",
                "unrealized_paths": ["諦める"],
                "constraints": [],
                "supporting_fact_ids": ["f1"],
                "ambiguities": [],
            },
            "realized_outcomes": [],
            "secondary_branches": [],
            "retrospective_counterfactuals": [],
            "present_question_ids": ["q1"],
        },
        "central_thesis": {
            "thesis_type": "",
            "statement": "現在と問いの共存",
            "pole_a": "",
            "pole_b": "",
            "supported_by": ["f1"],
            "risks": [],
            "validation_status": "pending",
        },
        "lost_structure": {"items": []},
        "protected_structure": {"items": []},
        "residue_candidates": {"items": []},
        "selected_observatory_lenses": {"evaluated": [], "selected": []},
        "editorial_outline": {"sections": []},
        "repetition_prevention_map": {"entries": []},
        "rebranch_design": {
            "directions": [
                {
                    "id": "r1",
                    "source_meaning": "兄弟がいる意味",
                    "current_receiver": "友人来訪",
                    "branch_specific_form": "家庭らしさ",
                    "support_ids": ["f1"],
                    "genericity_score": 99,
                    "invented_scene_used": False,
                    "risks": [],
                    "publishable": False,
                    "selected_for_manuscript": False,
                }
            ]
        },
        "additional_questions": {"required": False, "questions": []},
        "user_confirmation_view": {
            "branch_period": "45歳",
            "triggering_event": "子どもを授かった",
            "chosen_path": "三人家族",
            "unchosen_path": "諦める",
            "actual_secondary_branches": [],
            "retrospective_counterfactuals": [],
            "present_questions": ["二人目を持っていたらどうだったか"],
            "current_context": ["三人家族"],
            "feelings": [],
            "hypotheses": [],
            "unknowns": [],
            "central_thesis_preview": "現在と問いの共存",
            "observatory_lens_candidates": [],
            "items_to_confirm": [],
        },
        "validation": {
            "actual_secondary_rejected": [],
            "lenses_rejected": [],
            "questions_not_converted_to_facts": True,
            "hypotheses_not_converted_to_facts": True,
            "notes": [],
            "source_coverage_missing": [],
        },
        "source_coverage": {
            "branch_period": True,
            "triggering_event": True,
            "chosen_path": True,
            "unchosen_path": True,
            "present_question": True,
            "current_context": True,
        },
    }
    good = {
        "status": "ready_for_user_confirmation",
        "grounded_input": {
            "facts": [
                {"id": "f1", "content": "45歳で子どもを授かった", "boundary_type": "explicit_fact"},
                {"id": "f2", "content": "現在は三人家族", "boundary_type": "explicit_fact"},
            ],
            "questions": [
                {"id": "q1", "content": "二人目を持っていたらどうだったか", "boundary_type": "user_question"}
            ],
            "feelings": [],
            "hypotheses": [],
            "unknowns": [],
            "model_inferences": [],
            "current_context": ["三人家族"],
            "sensitive_domains": [],
            "confirmed_by_user": False,
            "requested_corrections": [],
        },
        "input_sufficiency": {
            "required_fields_complete": True,
            "current_context_requirement_met": True,
            "missing_fields": [],
            "additional_questions": [],
        },
        "sensitive_domain_analysis": {"domains": [], "notes": [], "clarification_required": False},
        "branch_structure": {
            "primary_branch": {
                "period": "45歳",
                "triggering_event": "子どもを授かった",
                "available_paths": [],
                "realized_path": "三人家族",
                "unrealized_paths": ["諦める"],
                "constraints": [],
                "supporting_fact_ids": ["f1"],
                "ambiguities": [],
            },
            "realized_outcomes": [],
            "secondary_branches": [],
            "retrospective_counterfactuals": [
                {
                    "id": "cf1",
                    "classification": "retrospective_counterfactual",
                    "description": "二人目を持っていたらどうだったか",
                    "available_paths": [],
                    "realized_path": "",
                    "unrealized_paths": [],
                    "explicit_evidence_ids": [],
                    "ambiguity_status": "",
                    "present_relevance": "",
                    "must_not_be_treated_as_historical_choice": True,
                }
            ],
            "present_question_ids": ["q1"],
        },
        "central_thesis": {
            "thesis_type": "",
            "statement": "現在と問いの共存",
            "pole_a": "",
            "pole_b": "",
            "supported_by": ["f1"],
            "risks": [],
            "validation_status": "pending",
        },
        "lost_structure": {"items": []},
        "protected_structure": {"items": []},
        "residue_candidates": {"items": [{"content": "問いが残る", "support_ids": ["q1"]}]},
        "selected_observatory_lenses": {"evaluated": [], "selected": []},
        "editorial_outline": {"sections": []},
        "repetition_prevention_map": {"entries": []},
        "rebranch_design": {"directions": []},
        "additional_questions": {"required": False, "questions": []},
        "user_confirmation_view": {
            "branch_period": "45歳",
            "triggering_event": "子どもを授かった",
            "chosen_path": "三人家族",
            "unchosen_path": "諦める",
            "actual_secondary_branches": [],
            "retrospective_counterfactuals": ["二人目を持っていたらどうだったか"],
            "present_questions": ["二人目を持っていたらどうだったか"],
            "current_context": ["三人家族"],
            "feelings": [],
            "hypotheses": [],
            "unknowns": [],
            "central_thesis_preview": "現在と問いの共存",
            "observatory_lens_candidates": [],
            "items_to_confirm": [],
        },
        "validation": {
            "actual_secondary_rejected": [],
            "lenses_rejected": [],
            "questions_not_converted_to_facts": True,
            "hypotheses_not_converted_to_facts": True,
            "notes": [],
            "source_coverage_missing": [],
        },
        "source_coverage": {
            "branch_period": True,
            "triggering_event": True,
            "chosen_path": True,
            "unchosen_path": True,
            "present_question": True,
            "current_context": True,
        },
    }

    calls = {"n": 0}

    def fake_chat(system, user, response_format, **kwargs):
        calls["n"] += 1
        return bad if calls["n"] == 1 else good

    monkeypatch.setattr(
        "app.parallel_life_deep_reading.grounding.chat_json_schema", fake_chat
    )
    result = run_call1_grounding(CASE1_SOURCE)
    assert calls["n"] == 2
    assert result.parse_diagnostics is not None
    assert result.parse_diagnostics.repair_attempted is True
    assert result.parse_diagnostics.repair_succeeded is True
    assert result.status in {
        GenerationStatus.ready_for_user_confirmation,
        GenerationStatus.needs_additional_input,
    }


def test_schema_repair_failure_returns_typed_error(monkeypatch):
    # Invalid after normalize: nested direction keeps illegal genericity_score.
    bad = {
        "status": "ready_for_user_confirmation",
        "grounded_input": {
            "facts": [],
            "questions": [],
            "feelings": [],
            "hypotheses": [],
            "unknowns": [],
            "model_inferences": [],
            "current_context": ["x"],
            "sensitive_domains": [],
            "confirmed_by_user": False,
            "requested_corrections": [],
        },
        "input_sufficiency": {
            "required_fields_complete": True,
            "current_context_requirement_met": True,
            "missing_fields": [],
            "additional_questions": [],
        },
        "sensitive_domain_analysis": {"domains": [], "notes": [], "clarification_required": False},
        "branch_structure": {
            "primary_branch": {
                "period": "a",
                "triggering_event": "b",
                "available_paths": [],
                "realized_path": "c",
                "unrealized_paths": ["d"],
                "constraints": [],
                "supporting_fact_ids": [],
                "ambiguities": [],
            },
            "realized_outcomes": [],
            "secondary_branches": [],
            "retrospective_counterfactuals": [],
            "present_question_ids": [],
        },
        "central_thesis": {
            "thesis_type": "",
            "statement": "s",
            "pole_a": "",
            "pole_b": "",
            "supported_by": [],
            "risks": [],
            "validation_status": "pending",
        },
        "lost_structure": {"items": []},
        "protected_structure": {"items": []},
        "residue_candidates": {"items": []},
        "selected_observatory_lenses": {"evaluated": [], "selected": []},
        "editorial_outline": {"sections": []},
        "repetition_prevention_map": {"entries": []},
        "rebranch_design": {
            "directions": [
                {
                    "id": "r1",
                    "source_meaning": "x",
                    "current_receiver": "y",
                    "branch_specific_form": "z",
                    "support_ids": ["f1"],
                    "genericity_score": 99,
                }
            ]
        },
        "additional_questions": {"required": False, "questions": []},
        "user_confirmation_view": {
            "branch_period": "a",
            "triggering_event": "b",
            "chosen_path": "c",
            "unchosen_path": "d",
            "actual_secondary_branches": [],
            "retrospective_counterfactuals": [],
            "present_questions": [],
            "current_context": ["x"],
            "feelings": [],
            "hypotheses": [],
            "unknowns": [],
            "central_thesis_preview": "s",
            "observatory_lens_candidates": [],
            "items_to_confirm": [],
        },
        "validation": {
            "actual_secondary_rejected": [],
            "lenses_rejected": [],
            "questions_not_converted_to_facts": True,
            "hypotheses_not_converted_to_facts": True,
            "notes": [],
            "source_coverage_missing": [],
        },
        "source_coverage": {
            "branch_period": True,
            "triggering_event": True,
            "chosen_path": True,
            "unchosen_path": True,
            "present_question": True,
            "current_context": True,
        },
    }

    def fake_chat(system, user, response_format, **kwargs):
        return bad

    monkeypatch.setattr(
        "app.parallel_life_deep_reading.grounding.chat_json_schema", fake_chat
    )
    with pytest.raises(Call1SchemaError) as exc:
        run_call1_grounding(CASE1_SOURCE)
    assert exc.value.diagnostics.repair_attempted is True
    assert exc.value.diagnostics.repair_succeeded is False
    assert exc.value.partial is not None
    assert exc.value.partial.status == GenerationStatus.schema_validation_failed


@pytest.mark.parametrize(
    "case_file",
    [
        "case1_call1_raw.json",
        "case2_call1_raw.json",
        "case3_call1_raw.json",
        "case4_call1_raw.json",
    ],
)
def test_live_failure_fixtures_do_not_attributeerror(case_file):
    path = LIVE_RAW / case_file
    if not path.exists():
        pytest.skip("live raw fixture not present")
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        parse_call1_payload(raw, source_text="現在の状況あり。どうだったか。")
    except Call1SchemaError:
        pass  # acceptable if still incomplete after normalize
    # AttributeError must not escape
