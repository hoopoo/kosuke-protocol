"""v1.1.5-exp Section Realization + residue claim builder fix."""

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
from app.parallel_life_deep_reading.prompts import CALL_1_VERSION, call1_system_prompt
from app.parallel_life_deep_reading.section_contracts import (
    CALL_1_PROMPT_VERSION_V115,
    RUNTIME_VERSION_V115_EXP,
    build_call2_writing_pack,
    build_claim_atoms,
    claim_text_is_malformed,
    required_section_realization,
    section_contract_evidence_check,
    _synthesize_residue_interpretive,
)


def _call1() -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V115,
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
            # Malicious long prose that previously caused 「。のなかで」 joins
            present_structure=(
                "現在は自分の会社を経営しており、過去の選択が今の自分に影響を与えている。"
            ),
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


def test_versions():
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert "Section Realization" not in call1_system_prompt()
    assert CALL_1_PROMPT_VERSION_V115 == "parallel-life-call-1-v1.1.5-exp"
    assert RUNTIME_VERSION_V115_EXP == "parallel-life-runtime-v1.1.5-exp"
    assert CALL_1_PROMPT_VERSION_V11.startswith("parallel-life-call-1-v1.1.")


def test_residue_claim_builder_no_malformed_join():
    atoms = build_claim_atoms(_call1())
    assert "。" not in atoms.present_anchor
    assert atoms.present_anchor in {"自分の会社を経営している", "会社を経営している", "いまの生活"}
    claim = _synthesize_residue_interpretive(_call1())
    assert not claim_text_is_malformed(claim)
    assert "。の" not in claim
    assert "影響を与えている。の" not in claim
    assert "物差し" in claim or "測" in claim


def test_contracts_have_realization_fields_and_locked_labels():
    ok, notes, repaired, contracts = section_contract_evidence_check(_call1())
    assert ok, notes
    assert not contracts.diagnostics.get("malformed_claims")
    for sid in ("lost", "protected", "residue", "re_branch", "observatory"):
        c = contracts.by_id(sid)
        assert c and c.must_be_present
        assert c.required_public_label
        assert c.realization_goal
        assert c.minimum_paragraphs >= 1
        assert c.interpretive_claim
        assert not claim_text_is_malformed(c.interpretive_claim)
    pack = build_call2_writing_pack(repaired)
    assert pack["schema"].startswith("call2_writing_pack_v1.1.")
    assert "失ったもの" in pack["locked_public_labels_in_order"]
    assert "これからの再分岐" in pack["locked_public_labels_in_order"]
    assert "社会との接続" in pack["locked_public_labels_in_order"]


def test_required_section_realization_needs_labels_and_claims():
    _, _, repaired, contracts = section_contract_evidence_check(_call1())
    bad = "## 分岐点\n\n分岐があった。\n"
    ok, missing, _ = required_section_realization(bad, contracts)
    assert not ok
    assert any("required_public_label_missing" in m for m in missing)

    lost_c = contracts.by_id("lost")
    prot_c = contracts.by_id("protected")
    res_c = contracts.by_id("residue")
    reb_c = contracts.by_id("re_branch")
    body = f"""## 分岐点
残るか移るかの境界としての分岐があった。

## 選んだ道
測り方の転換として外へ移った。

## 選ばなかった人生
一企業の内部で役割を積み上げ続ける可能性が残る。

## 失ったもの
{lost_c.interpretive_claim}

## 守られたもの
{prot_c.interpretive_claim}

## 今に残った構造
{res_c.interpretive_claim}

## 社会との接続
長期雇用と企業間移動が社会のなかに並ぶ。

## これからの再分岐
{reb_c.interpretive_claim}
いまも残る問いのそばで、現在の読み方を置き直せる。
"""
    ok2, missing2, details = required_section_realization(body, contracts)
    assert ok2, missing2
    assert details["lost"]["realization_status"] == "realized"
    assert details["re_branch"]["realization_status"] == "realized"
