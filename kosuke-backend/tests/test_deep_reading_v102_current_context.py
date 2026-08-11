"""Regression: real-user current_context collapse + present_question UI (v1.0.2)."""

from __future__ import annotations

from app.parallel_life_deep_reading.call1_schema import call1_residue_items
from app.parallel_life_deep_reading.models import (
    AdditionalQuestions,
    BranchStructure,
    Call1Result,
    Call1Validation,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    InputSufficiency,
    PrimaryBranch,
    ResidueCandidates,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    is_generic_current_context_label,
    preserve_concrete_current_context,
    scrub_confirmation_ui_items,
)
from app.parallel_life_deep_reading.service import DeepReadingService
from app.parallel_life_deep_reading import SCHEMA_VERSION


REAL_USER_SOURCE = """30歳のとき、当時お付き合いしていた中国人女性と別れた。
中国人女性とは別れ、その後、今の妻（日本人）と結婚しました。
選ばなかった道は、中国人女性とお付き合いを継続すること。
息子が一人と妻の三人で生活しています。また、猫がいます。"""


def _collapsed_call1() -> Call1Result:
    return Call1Result(
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="30歳のとき中国人女性と別れた",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f2",
                    content="その後日本人の妻と結婚した",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
            current_context=["現在の生活"],
            questions=[],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="30歳",
                triggering_event="当時お付き合いしていた中国人女性と別れたこと",
                realized_path="中国人女性とは別れ、その後、今の妻（日本人）と結婚しました。",
                unrealized_paths=["中国人女性とお付き合いを継続すること。"],
                supporting_fact_ids=["f1", "f2"],
            )
        ),
        central_thesis=CentralThesis(statement=""),
        user_confirmation_view=UserConfirmationView(
            items_to_confirm=["present_question", "present_question"]
        ),
        validation=Call1Validation(),
        input_sufficiency=InputSufficiency(),
        additional_questions=AdditionalQuestions(),
        status=GenerationStatus.needs_additional_input,
        residue_candidates=ResidueCandidates(items=[]),
    )


def test_versions_v102_patch():
    assert PROMPT_VERSIONS["call_1"] == "parallel-life-call-1-v1.0.3"
    assert PROMPT_VERSIONS["call_2"] == "parallel-life-call-2-v1.0.3"
    assert PROMPT_VERSIONS["call_3"] == "parallel-life-call-3-v1.0.3"
    assert SCHEMA_VERSION == "parallel-life-runtime-v1.0.6"


def test_generic_label_detection():
    assert is_generic_current_context_label("現在の生活")
    assert is_generic_current_context_label("今の暮らし")
    assert not is_generic_current_context_label("息子が一人と妻の三人で生活しています")


def test_preserve_recovers_family_and_cat():
    grounded = GroundedInput(current_context=["現在の生活"])
    fixed = preserve_concrete_current_context(grounded, source_text=REAL_USER_SOURCE)
    assert "現在の生活" not in fixed.current_context
    assert any("三人" in c for c in fixed.current_context)
    assert any("猫" in c for c in fixed.current_context)
    assert not any("結婚" in c for c in fixed.current_context)


def test_runtime_gates_no_raw_present_question_and_no_false_contradiction():
    gated = apply_call1_runtime_gates(
        _collapsed_call1(), source_text=REAL_USER_SOURCE, input_corpus=REAL_USER_SOURCE
    )
    view = gated.user_confirmation_view
    assert "現在の生活" not in view.current_context
    assert any("三人" in c for c in view.current_context)
    assert any("猫" in c for c in view.current_context)
    assert "present_question" not in view.items_to_confirm
    assert view.items_to_confirm == scrub_confirmation_ui_items(view.items_to_confirm)
    assert gated.validation.material_contradiction_count == 0
    assert len(gated.additional_questions.questions) == 1
    assert "考えることはありますか" in gated.additional_questions.questions[0]
    residues = call1_residue_items(gated)
    assert residues
    stmt = residues[0].statement()
    assert "作った" not in stmt
    assert "並べて読む" in stmt or "現在の生活" in stmt
    assert residues[0].present_anchor_ids
    assert residues[0].past_anchor_ids


def test_approve_message_separates_missing_present_question():
    svc = DeepReadingService.__new__(DeepReadingService)
    gated = apply_call1_runtime_gates(
        _collapsed_call1(), source_text=REAL_USER_SOURCE, input_corpus=REAL_USER_SOURCE
    )
    msg = svc._approve_incomplete_message(gated)
    assert "矛盾" not in msg
    assert "問い" in msg
