"""v1.1.7-exp Re-branch Decision + Editorial Naturalness."""

from __future__ import annotations

from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
)
from app.parallel_life_deep_reading.models import (
    BranchStructure,
    Call1Result,
    CentralThesis,
    ConfirmedContinuity,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    LostItem,
    LostStructure,
    MeaningCompression,
    PrimaryBranch,
    ProtectedStructure,
    RebranchDesign,
    ResidueCandidate,
    ResidueCandidates,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.prompts import CALL_1_VERSION
from app.parallel_life_deep_reading.section_contracts import (
    CALL_1_PROMPT_VERSION_V117,
    RUNTIME_VERSION_V117_EXP,
    abstract_vocabulary_density,
    build_call2_writing_pack,
    build_rebranch_decision,
    ensure_rebranch_decision_in_body,
    re_branch_realization_check,
    required_section_realization,
    section_contract_evidence_check,
    thesis_closure_check,
    thin_abstract_vocabulary,
)


def _call1() -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V117,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="pack_career_history_001",
                    content="NTT東日本で勤務した",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="context_pack",
                    tags=["context_pack", "category:career_history"],
                ),
                GroundedFact(
                    id="pack_career_history_002",
                    content="外資系半導体企業へ転職した",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="context_pack",
                    tags=["context_pack", "category:career_history"],
                ),
                GroundedFact(
                    id="pack_current_work_004",
                    content="現在は自分の会社を経営している",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="context_pack",
                    tags=["context_pack", "category:current_work"],
                ),
            ],
            questions=[
                GroundedFact(
                    id="q1",
                    content="役職や年収はどうなったか",
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
            current_context=["いまは自分の会社を経営している"],
            confirmed_by_user=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="28歳",
                triggering_event="NTTに残るか外資へ移るか",
                realized_path="外資へ移る",
                unrealized_paths=["一企業の内部で役割を積み上げ続けること"],
                supporting_fact_ids=["pack_career_history_001"],
            )
        ),
        central_thesis=CentralThesis(
            statement=(
                "一企業の内部で役割を積み上げる道を離れたという個人の分岐を、"
                "日本型の長期雇用と企業間移動のキャリアモデルと並べて読むことができる。"
            ),
            supported_by=["pack_career_history_001", "pack_career_history_002"],
            validation_status="passed",
        ),
        meaning_compression=MeaningCompression(
            past_structure="残るか移るか",
            present_structure="現在は自分の会社を経営している。",
            unresolved_question="役職や年収はどうなったか",
            social_institutional_parallel="長期雇用と企業間移動が併存",
        ),
        cross_lens_relations=[
            {
                "id": "clr_ee_regime_001",
                "personal_structure": "一企業の内部で役割を積み上げる道を離れた",
                "social_structure": "長期雇用と企業間移動が併存してきた",
                "interpretation": "境界として読むことができる",
                "causality_status": "non_causal_parallel",
            }
        ],
        lost_structure=LostStructure(
            items=[
                LostItem(
                    content="NTTに残る選択をした場合のキャリア",
                    support_ids=["pack_career_history_001"],
                )
            ]
        ),
        protected_structure=ProtectedStructure(
            items=[
                ConfirmedContinuity(
                    content="外資系企業へ転職したこと",
                    support_ids=["pack_career_history_002"],
                )
            ]
        ),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement="複数業界を経験した",
                    past_anchor_ids=["pack_career_history_001"],
                    present_anchor_ids=["pack_current_work_004"],
                )
            ]
        ),
        rebranch_design=RebranchDesign(directions=[]),
        user_confirmation_view=UserConfirmationView(
            present_questions=["役職や年収はどうなったか"]
        ),
    )


def test_active_pin_supersedes_v117():
    """v1.1.7 constants remain; active Contextual pin moves forward (v1.1.8+)."""
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert CALL_1_PROMPT_VERSION_V117 == "parallel-life-call-1-v1.1.7-exp"
    assert RUNTIME_VERSION_V117_EXP == "parallel-life-runtime-v1.1.7-exp"
    # Active pin is no longer frozen at v1.1.7
    assert CALL_1_PROMPT_VERSION_V11 != CALL_1_PROMPT_VERSION_V117
    assert "v1.1." in CALL_1_PROMPT_VERSION_V11


def test_rebranch_decision_fields():
    ok, notes, repaired, contracts = section_contract_evidence_check(_call1())
    assert ok, notes
    reb = contracts.by_id("re_branch")
    assert reb and reb.must_be_present
    assert reb.present_choice
    assert reb.what_is_no_longer_required
    assert reb.what_can_now_be_chosen
    assert reb.non_genericity_score >= 0.5
    assert reb.rebranch_decision
    d = build_rebranch_decision(repaired)
    assert d.present_choice
    pack = build_call2_writing_pack(repaired)
    assert pack["schema"] == "call2_writing_pack_v1.1.7"
    assert pack["rebranch_decision"]["present_choice"]


def test_question_only_rebranch_fails_gate():
    ok, missing, _ = re_branch_realization_check(
        "これから何を尺度にするか考えていく。",
        residue_body="いまも問いが残っている。",
    )
    assert ok is False
    assert missing


def test_ensure_rebranch_repairs_reflection_only():
    _, _, repaired, contracts = section_contract_evidence_check(_call1())
    chosen = contracts.by_id("chosen_path")
    body = f"""## 分岐点
残るか移るかの境界があった。

## 選んだ道
{chosen.factual_choice}を選んだ。振り返ると、{chosen.structural_shift}。{chosen.thesis_link}。

## 選ばなかった人生
一企業の内部で役割を積み上げ続ける道があった。

## 失ったもの
同じ制度のなかで確かめる物差しが離れた。

## 守られたもの
定義し直す余白が残った。

## 今に残った構造
いまも残る問いが、物差しとして並ぶ。

## 社会との接続
雇用モデルが並ぶ。

## これからの再分岐
何を長期の蓄積として数えるのかは、あらためて置かれる問いになる。見ていくことはできる。
"""
    fixed = ensure_rebranch_decision_in_body(body, contracts)
    ok, missing, _ = required_section_realization(fixed, contracts)
    assert "required_section_unrealized:re_branch" not in (missing or [])
    closure_ok, closure_missing, _ = thesis_closure_check(fixed, contracts)
    assert closure_ok, closure_missing
    assert "余地" in fixed or "選び直" in fixed


def test_abstract_vocab_thinning():
    text = "蓄積 " * 6 + "構造 " * 5
    dens = abstract_vocabulary_density(text)
    assert dens["thinning_recommended"]
    thinned = thin_abstract_vocabulary(text)
    dens2 = abstract_vocabulary_density(thinned)
    assert dens2["counts"]["蓄積"] < dens["counts"]["蓄積"]
