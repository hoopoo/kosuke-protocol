"""v1.1.4-exp Interpretive Claims."""

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
from app.parallel_life_deep_reading.prompts import (
    CALL_1_VERSION,
    call1_system_prompt,
    call2_system_prompt_v114,
)
from app.parallel_life_deep_reading.section_contracts import (
    CALL_1_PROMPT_VERSION_V114,
    RUNTIME_VERSION_V114_EXP,
    _is_fact_like,
    build_call2_writing_pack,
    section_contract_evidence_check,
)


def _ntt_fact_like_call1() -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V114,
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
            present_structure="自分の会社を経営している",
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
        # Fact-like Call1 content (the v1.1.3 failure mode)
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


def test_versions_strict_untouched():
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert "Interpretive Claims" not in call1_system_prompt()
    assert CALL_1_PROMPT_VERSION_V114 == "parallel-life-call-1-v1.1.4-exp"
    assert RUNTIME_VERSION_V114_EXP == "parallel-life-runtime-v1.1.4-exp"
    assert CALL_1_PROMPT_VERSION_V11.startswith("parallel-life-call-1-v1.1.")
    assert "interpretive" in call2_system_prompt_v114().lower()


def test_upgrades_fact_like_and_fills_interpretive_claims():
    assert _is_fact_like("NTTに残る選択をした場合のキャリア")
    assert _is_fact_like("外資系企業へ転職したこと")
    ok, notes, repaired, contracts = section_contract_evidence_check(_ntt_fact_like_call1())
    assert ok, notes
    assert "section_repair:lost_upgraded_from_fact_like" in notes
    assert "section_repair:protected_upgraded_from_fact_like" in notes
    assert not _is_fact_like(repaired.lost_structure.items[0].content)
    assert not _is_fact_like(repaired.protected_structure.items[0].content)
    lost = contracts.by_id("lost")
    prot = contracts.by_id("protected")
    residue = contracts.by_id("residue")
    rebranch = contracts.by_id("re_branch")
    assert lost and lost.interpretive_claim and not _is_fact_like(lost.required_meaning)
    assert prot and prot.interpretive_claim and not _is_fact_like(prot.required_meaning)
    assert residue and residue.interpretive_claim
    assert rebranch and rebranch.must_be_present and rebranch.interpretive_claim
    assert "測" in lost.interpretive_claim or "確かめ" in lost.interpretive_claim
    assert "閉じ" in prot.interpretive_claim or "余白" in prot.required_meaning


def test_writing_pack_exposes_interpretive_claims():
    _, _, repaired, _ = section_contract_evidence_check(_ntt_fact_like_call1())
    pack = build_call2_writing_pack(repaired)
    assert pack["schema"].startswith("call2_writing_pack_v1.1.")
    assert pack["interpretive_claims_by_section"]["lost"]
    assert pack["editorial_constraints"]["interpretation_first_evidence_second"] is True
    for facts in pack["evidence_by_section"].values():
        assert len(facts) <= 2
