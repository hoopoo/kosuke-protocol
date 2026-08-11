"""v1.1.3-exp Section Contracts + minimal Call2 writing pack."""

from __future__ import annotations

from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
)
from app.parallel_life_deep_reading.models import (
    BranchStructure,
    Call1Result,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
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
    CALL_1_PROMPT_VERSION_V113,
    RUNTIME_VERSION_V113_EXP,
    build_call2_writing_pack,
    compress_resume_body,
    required_section_realization,
    section_contract_evidence_check,
    section_resume_flags,
    writing_pack_size_stats,
)


def _ntt_call1_empty_sections() -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V113,
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
                    content="あのとき残っていたらどうなっていたか",
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
            unresolved_question="あのとき残っていたら",
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
        lost_structure=LostStructure(items=[]),
        protected_structure=ProtectedStructure(items=[]),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement="過去の分岐の問いを現在の経営と並べて読むことができる",
                    past_anchor_ids=["pack_career_history_001"],
                    present_anchor_ids=["pack_current_work_004"],
                )
            ]
        ),
        rebranch_design=RebranchDesign(directions=[]),
        user_confirmation_view=UserConfirmationView(
            present_questions=["あのとき残っていたら"]
        ),
    )


def test_versions_untouched_for_strict():
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert "Section Contracts" not in call1_system_prompt()
    # Active Contextual pin may advance; v1.1.3 remains a historical contract pin.
    assert CALL_1_PROMPT_VERSION_V113 == "parallel-life-call-1-v1.1.3-exp"
    assert RUNTIME_VERSION_V113_EXP == "parallel-life-runtime-v1.1.3-exp"
    assert CALL_1_PROMPT_VERSION_V11.startswith("parallel-life-call-1-v1.1.")


def test_repair_fills_lost_protected_rebranch():
    ok, notes, repaired, contracts = section_contract_evidence_check(_ntt_call1_empty_sections())
    assert ok
    assert repaired.lost_structure.items
    assert repaired.protected_structure.items
    assert repaired.rebranch_design.directions
    assert "section_repair:lost_backfilled" in notes
    assert contracts.by_id("lost") and contracts.by_id("lost").must_be_present
    assert contracts.by_id("protected") and contracts.by_id("protected").must_be_present
    assert contracts.by_id("re_branch") and contracts.by_id("re_branch").must_be_present


def test_writing_pack_removes_full_dump_duplication():
    _, _, repaired, _ = section_contract_evidence_check(_ntt_call1_empty_sections())
    pack = build_call2_writing_pack(repaired)
    stats = writing_pack_size_stats(pack, repaired)
    assert stats["duplicate_full_call1_in_writing_pack"] is False
    assert "confirmed_call1" not in pack
    assert "explicit_facts" not in pack
    # Minimal evidence delivery: per-section budget, no full dump key
    assert "evidence_by_section" in pack
    for sid, facts in pack["evidence_by_section"].items():
        assert len(facts) <= 2
    # Writing pack should not embed a second full call1 tree
    assert "grounded_input" not in pack
    assert "lost_structure" not in pack


def test_compress_resume_and_realization():
    body = (
        "28歳のとき、NTT東日本に残るか、外資へ移るかという分かれ目があった。"
        "NTT東日本で勤務したのち、外資系半導体企業へ転職し、その後は複数の業界と企業を経験している。"
        "現在は自分の会社を経営し、複数の観測、Protocol、文章制作を行っている。"
    )
    assert section_resume_flags(body)["resume_density"] > 5
    compressed = compress_resume_body(body)
    assert section_resume_flags(compressed)["resume_density"] <= 5

    _, _, repaired, contracts = section_contract_evidence_check(_ntt_call1_empty_sections())
    lost_c = contracts.by_id("lost")
    prot_c = contracts.by_id("protected")
    res_c = contracts.by_id("residue")
    reb_c = contracts.by_id("re_branch")
    sample = f"""## 分岐点
残るか移るかの境界としての分かれ目があった。

## 選んだ道
測り方の転換として一つの組織を離れ、別の場へ移った。

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
    ok, missing, _ = required_section_realization(sample, contracts)
    assert ok, missing
