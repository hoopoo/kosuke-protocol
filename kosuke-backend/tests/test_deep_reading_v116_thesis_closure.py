"""v1.1.6-exp Thesis Closure for Chosen Path + Re-branch."""

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
    CALL_1_PROMPT_VERSION_V116,
    RUNTIME_VERSION_V116_EXP,
    _situation_phrase,
    _synthesize_residue_interpretive,
    build_call2_writing_pack,
    claim_text_is_malformed,
    required_section_realization,
    section_contract_evidence_check,
    thesis_closure_check,
)


def _call1() -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V116,
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
            present_structure="現在は自分の会社を経営しており、過去の選択が今の自分に影響を与えている。",
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
    assert "Thesis Closure" not in call1_system_prompt()
    assert CALL_1_PROMPT_VERSION_V116 == "parallel-life-call-1-v1.1.6-exp"
    assert RUNTIME_VERSION_V116_EXP == "parallel-life-runtime-v1.1.6-exp"


def test_situation_phrase_and_residue_grammar():
    assert "という状況のなかで" in _situation_phrase("自分の会社を経営している")
    assert claim_text_is_malformed("経営しているのなかで問いが残る")
    claim = _synthesize_residue_interpretive(_call1())
    assert not claim_text_is_malformed(claim)
    assert "ているのなかで" not in claim
    assert "という状況のなかで" in claim or "いまも残る" in claim


def test_chosen_and_rebranch_closure_fields():
    ok, notes, repaired, contracts = section_contract_evidence_check(_call1())
    assert ok, notes
    chosen = contracts.by_id("chosen_path")
    reb = contracts.by_id("re_branch")
    assert chosen and chosen.realization_required
    assert chosen.factual_choice
    assert chosen.structural_shift
    assert "定義し直" in chosen.structural_shift or "積み上げ" in chosen.structural_shift
    assert chosen.thesis_link
    assert reb and reb.realization_required
    assert reb.present_choice and "選" in reb.present_choice
    assert reb.measurement_shift
    assert reb.non_genericity is True
    pack = build_call2_writing_pack(repaired)
    assert pack["schema"] == "call2_writing_pack_v1.1.6"
    assert pack["thesis_closure"]["chosen_path"]["structural_shift"]


def test_thesis_closure_check_passes_strong_body():
    _, _, repaired, contracts = section_contract_evidence_check(_call1())
    chosen = contracts.by_id("chosen_path")
    reb = contracts.by_id("re_branch")
    body = f"""## 分岐点
残るか移るかの境界があった。

## 選んだ道
{chosen.factual_choice}を選んだ。振り返ると、{chosen.structural_shift}。{chosen.thesis_link}。

## 選ばなかった人生
一企業の内部で役割を積み上げ続ける可能性が残る。

## 失ったもの
同じ制度の時間のなかで進み具合を確かめ続ける物差しだったとも読める。

## 守られたもの
一つの所属に固定しきらず、仕事を別の言葉で定義し直す余白が残った。

## 今に残った構造
役職や年収はどうなったかという問いが、いまの生活のなかで別の物差しとして想像される。

## 社会との接続
長期雇用と企業間移動が社会のなかに並ぶ。

## これからの再分岐
{reb.measurement_shift}。{reb.present_choice}余地がある。いまも残る問いのそばで、現在の読み方を置き直せる。
"""
    ok, missing, details = required_section_realization(body, contracts)
    assert ok, missing
    closure_ok, closure_missing, _ = thesis_closure_check(body, contracts)
    assert closure_ok, closure_missing
    assert details.get("thesis_closure", {}).get("arc") == "closed"


def test_chronology_only_chosen_path_fails():
    _, _, _, contracts = section_contract_evidence_check(_call1())
    bad = """## 分岐点
分岐があった。

## 選んだ道
選ばれたのは、別の企業へ移る道だった。その後、いくつかの場を経験している。

## 選ばなかった人生
積み上げる道が残る。

## 失ったもの
物差しとしての連続性。

## 守られたもの
定義し直す余白。

## 今に残った構造
問いが残る。

## 社会との接続
社会の並び。

## これからの再分岐
これから考えていく。
"""
    ok, missing, _ = required_section_realization(bad, contracts)
    assert not ok
    assert any("chosen_path" in m for m in missing)
    assert any("re_branch" in m for m in missing)
