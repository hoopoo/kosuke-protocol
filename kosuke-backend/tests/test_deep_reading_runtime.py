"""Unit tests for Deep Reading runtime validation (Production Candidate v1.0)."""

from __future__ import annotations

from app.parallel_life_deep_reading.fixtures import (
    CASE1_SOURCE,
    build_case1_bad_draft,
    build_case1_call1,
    build_case2_call1,
    build_case3_call1,
)
from app.parallel_life_deep_reading.models import (
    BranchClassification,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    ObservatoryLensCandidate,
    RebranchDirection,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    detect_generic_advice,
    detect_unsupported_scenes,
    filter_publishable_rebranch,
    filter_selected_lenses,
    recalculate_lens_evidence_gate,
    recalculate_publication_gate,
    recalculate_rebranch_publishable,
    validate_title,
)
from app.parallel_life_deep_reading.session_store import DeepReadingSessionStore


def test_prompt_versions_frozen():
    assert PROMPT_VERSIONS["call_1"] == "parallel-life-call-1-v1.0.3"
    assert PROMPT_VERSIONS["call_2"] == "parallel-life-call-2-v1.0.3"
    assert PROMPT_VERSIONS["call_3"] == "parallel-life-call-3-v1.0.3"


def test_user_question_not_kept_as_fact():
    call1 = build_case1_call1(with_actual_secondary=False)
    # Inject a misclassified question into facts
    call1.grounded_input.facts.append(
        GroundedFact(
            id="q_as_fact",
            content="二人目は必要だった",
            boundary_type=FactBoundaryType.user_question,
        )
    )
    gated = apply_call1_runtime_gates(call1)
    assert all(f.id != "q_as_fact" for f in gated.grounded_input.facts)
    assert any(q.id == "q_as_fact" for q in gated.grounded_input.questions)


def test_user_hypothesis_not_converted_to_fact():
    call1 = build_case1_call1(with_actual_secondary=False)
    call1.grounded_input.facts.append(
        GroundedFact(
            id="h_as_fact",
            content="きっと兄弟がいた方が良かった",
            boundary_type=FactBoundaryType.user_hypothesis,
        )
    )
    gated = apply_call1_runtime_gates(call1)
    assert all(f.id != "h_as_fact" for f in gated.grounded_input.facts)
    assert any(h.id == "h_as_fact" for h in gated.grounded_input.hypotheses)


def test_actual_secondary_requires_explicit_evidence_question_insufficient():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    assert call1.branch_structure.secondary_branches == []
    assert len(call1.branch_structure.retrospective_counterfactuals) >= 1
    assert all(
        b.classification == BranchClassification.retrospective_counterfactual
        for b in call1.branch_structure.retrospective_counterfactuals
    )
    assert "sec_bad" in call1.validation.actual_secondary_rejected or any(
        "downgraded" in (b.ambiguity_status or "")
        for b in call1.branch_structure.retrospective_counterfactuals
    )


def test_actual_secondary_with_decision_evidence():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=True))
    assert len(call1.branch_structure.secondary_branches) == 1
    assert (
        call1.branch_structure.secondary_branches[0].classification
        == BranchClassification.actual_secondary_branch
    )
    assert call1.branch_structure.secondary_branches[0].explicit_evidence_ids


def test_lens_evidence_gate_recalculated():
    cand = ObservatoryLensCandidate(
        lens_id="body",
        explicit_evidence_ids=["fact_002"],
        residue_evidence_ids=[],
        new_meaning_added="",
        evidence_gate_passed=True,
    )
    gated = recalculate_lens_evidence_gate(cand)
    assert gated.evidence_gate_passed is False
    assert "missing_residue_evidence" in (gated.rejection_reason or "")


def test_zero_lens_is_valid():
    from app.parallel_life_deep_reading.call1_schema import (
        call1_evaluated_lenses,
        call1_selected_lenses,
    )

    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    assert call1_selected_lenses(call1) == []
    evaluated, selected = filter_selected_lenses(call1_evaluated_lenses(call1))
    assert selected == []
    assert evaluated  # rejected candidates preserved


def test_rebranch_publishable_recalculated_not_trusted():
    cand = RebranchDirection(
        id="x",
        source_meaning="a",
        current_receiver="b",
        branch_specific_form="c",
        support_ids=["fact_1"],
        genericity_score=2,
        invented_scene_used=False,
        publishable=True,
        selected_for_manuscript=True,
    )
    fixed = recalculate_rebranch_publishable(cand)
    assert fixed.publishable is False
    assert fixed.selected_for_manuscript is False


def test_genericity_score_zero_or_one_required():
    ok = recalculate_rebranch_publishable(
        RebranchDirection(
            id="ok",
            source_meaning="息子に兄弟がいる意味",
            current_receiver="友人来訪の現在",
            branch_specific_form="家庭らしさを一度言葉にする",
            support_ids=["fact_005"],
            genericity_score=1,
        )
    )
    assert ok.publishable is True
    bad = recalculate_rebranch_publishable(
        RebranchDirection(
            id="bad",
            source_meaning="成長",
            current_receiver="生活",
            branch_specific_form="小さく始める",
            support_ids=[],
            genericity_score=3,
            publishable=True,
        )
    )
    assert bad.publishable is False


def test_unsupported_scene_detection():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    body = "夕方、息子の友人たちの声がリビングに響く。自分の会社の仕事を終え、家へ戻ったときなのか。"
    scenes = detect_unsupported_scenes(body, call1.grounded_input)
    assert scenes
    assert any(s.scene_type in {"specific_room", "homecoming"} for s in scenes)


def test_generic_advice_detection():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    body = "まずは一つから、無理のない範囲で小さく始めよう。"
    findings = detect_generic_advice(body, call1.grounded_input)
    assert findings


def test_case_specific_advice_may_pass():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    body = (
        "息子の友人が家に遊びに来る現在を照らすため、"
        "家庭らしさを一度だけ言葉にして記録する。"
    )
    findings = detect_generic_advice(body, call1.grounded_input)
    # May or may not flag depending on triad; must not auto-fail solely on 記録する
    # Strong case-specific object + reason + context should pass
    assert all(
        f.case_specific_object_present or f.reason_present or f.current_context_present
        for f in findings
    ) or findings == []


def test_title_rejects_unrelated_creativity_theme():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    body = "現在の三人家族の暮らしに戻る。"
    tv = validate_title(
        "創作に残らなかった45歳",
        "",
        call1.grounded_input,
        call1.central_thesis.statement,
        body,
    )
    assert tv.title_introduces_new_unverified_theme is True
    assert tv.passed is False


def test_session_isolation():
    store = DeepReadingSessionStore()
    a = store.create(raw_user_input="case A")
    b = store.create(raw_user_input="case B")
    assert a.session_id != b.session_id
    assert store.get(a.session_id).raw_user_input == "case A"
    assert store.get(b.session_id).raw_user_input == "case B"
    a.raw_user_input = "mutated"
    store.save(a)
    assert store.get(b.session_id).raw_user_input == "case B"


def test_case2_no_rejection_inversion_structure():
    from app.parallel_life_deep_reading.call1_schema import call1_selected_lenses

    call1 = apply_call1_runtime_gates(build_case2_call1())
    assert "合格" in call1.branch_structure.primary_branch.triggering_event
    assert call1.branch_structure.secondary_branches == []
    assert call1_selected_lenses(call1) == []


def test_case3_generic_rebranch_filtered():
    from app.parallel_life_deep_reading.call1_schema import call1_rebranch_directions

    call1 = apply_call1_runtime_gates(build_case3_call1())
    publishable = call1_rebranch_directions(call1)
    assert all(r.genericity_score <= 1 for r in publishable)
    assert all("時間を確保" not in r.branch_specific_form for r in publishable)


def test_publication_gate_blocks_unconfirmed():
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    draft = build_case1_bad_draft()
    gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=draft,
        body=draft.body_markdown,
        title="三人の暮らしに残る、もう一人の問い",
        subtitle="",
        rebranch_candidates=draft.rebranch_candidates,
    )
    assert gate.publishable is False
    assert "grounded_input_not_confirmed" in gate.blocking_reasons


def test_fallback_disabled_constant():
    """Deep Reading must not expose a heuristic long-form generator."""
    import app.parallel_life_deep_reading as pkg
    import app.parallel_life_deep_reading.draft as draft_mod
    import app.parallel_life_deep_reading.grounding as ground_mod

    assert not hasattr(pkg, "heuristic_deep_reading")
    assert not hasattr(draft_mod, "_heuristic")
    assert not hasattr(ground_mod, "_heuristic_manuscript")
