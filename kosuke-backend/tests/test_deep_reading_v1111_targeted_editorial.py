"""v1.1.11-exp Track B targeted editorial — plus Track A freeze checks."""

from __future__ import annotations

from app.parallel_life_deep_reading.branch_semantics import (
    CALL_1_PROMPT_VERSION_V1111,
    RUNTIME_VERSION_V1111_EXP,
    allows_career_product_logic,
    build_branch_semantics,
)
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
    MeaningCompression,
    PrimaryBranch,
)
from app.parallel_life_deep_reading.runtime_validation import (
    detect_unsupported_causality,
    rewrite_unsupported_causality_phrases,
)
from app.parallel_life_deep_reading.section_contracts import (
    LOCKED_PUBLIC_LABELS_JA,
    _chosen_path_closure_fields,
    _section_claim_realized,
    _synthesize_rebranch,
    build_rebranch_decision,
    normalize_markdown_section_headings,
    parse_locked_sections,
    re_branch_realization_check,
)


def test_pins_v1111():
    # v1.1.0-rc1 freeze pins (behavior identical to v1.1.11-exp Track B)
    assert CALL_1_PROMPT_VERSION_V11 == "parallel-life-call-1-v1.1.9"
    assert CALL_1_PROMPT_VERSION_V1111 == "parallel-life-call-1-v1.1.9"
    assert RUNTIME_VERSION_V11_EXP == RUNTIME_VERSION_V1111_EXP
    assert RUNTIME_VERSION_V1111_EXP == "parallel-life-runtime-v1.1.11"


def test_track_a_locked_labels_still_normalize():
    messy = "序文 ## 残されたもの。本文\n##守られたもの\n本文2\n"
    fixed = normalize_markdown_section_headings(messy)
    parsed = parse_locked_sections(fixed)
    assert "守られたもの" in parsed
    assert "## 残されたもの" not in fixed


def test_career_chosen_path_structural_shift_not_resume():
    call1 = Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V1111,
        schema_version=RUNTIME_VERSION_V1111_EXP,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="pack_career_history_001",
                    content="NTT東日本で勤務した",
                    boundary_type=FactBoundaryType.explicit_fact,
                    tags=["context_pack", "category:career_history"],
                ),
                GroundedFact(
                    id="pack_career_history_002",
                    content="外資系半導体企業へ転職した",
                    boundary_type=FactBoundaryType.explicit_fact,
                    tags=["context_pack", "category:career_history"],
                ),
            ],
            questions=[],
            current_context=["いまは自分の会社を経営している"],
            confirmed_by_user=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="28歳",
                triggering_event="NTTに残るか外資へ移るか",
                realized_path="外資系企業へ移ること",
                unrealized_paths=["NTTに残る"],
                supporting_fact_ids=["pack_career_history_001"],
            )
        ),
        central_thesis=CentralThesis(
            statement="一企業の内部で役割を積み上げる道を離れた分岐を読む。",
            supported_by=["pack_career_history_001"],
            validation_status="passed",
        ),
        meaning_compression=MeaningCompression(),
    )
    call1 = call1.model_copy(
        update={"branch_semantics": build_branch_semantics(call1).model_dump(mode="json")}
    )
    assert allows_career_product_logic(build_branch_semantics(call1))
    closure = _chosen_path_closure_fields(call1)
    assert "一制度" in closure["structural_shift"] or "組織を移" in closure["structural_shift"]
    assert "定義し直" not in closure["structural_shift"]
    body = (
        "選んだのは、NTTを離れて外資系企業へ移ることだった。"
        "一つの所属にとどまる道を選ばなかったこととして、この移り方を見ることができる。"
        "いまも残る問いの起点として、この移り方が現在の生活と並んでいる。"
    )
    assert _section_claim_realized("chosen_path", body, closure["interpretive_claim"])


def test_education_rebranch_release_and_domain_place():
    call1 = Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V1111,
        schema_version=RUNTIME_VERSION_V1111_EXP,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="第一志望の大学に合格した",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f2",
                    content="いまは別の仕事をしている",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="current_work",
                    tags=["context_pack", "category:current_work"],
                ),
            ],
            questions=[
                GroundedFact(
                    id="q1",
                    content="別の大学へ行っていたら",
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
            current_context=["いまは別の仕事をしている"],
            confirmed_by_user=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="19歳",
                triggering_event="第一志望の大学に合格した",
                realized_path="その大学へ進学すること",
                unrealized_paths=["別の大学へ進学すること"],
                supporting_fact_ids=["f1"],
            )
        ),
        central_thesis=CentralThesis(
            statement="進学の分岐をいま読み直せる。",
            supported_by=["f1"],
            validation_status="passed",
        ),
        meaning_compression=MeaningCompression(),
    )
    sem = build_branch_semantics(call1)
    call1 = call1.model_copy(update={"branch_semantics": sem.model_dump(mode="json")})
    decision = build_rebranch_decision(call1)
    assert "仕事の場" not in (decision.present_choice or "")
    assert "固定しなくてよい" in (decision.what_is_no_longer_required or "") or (
        decision.present_choice == ""
    )
    direction = _synthesize_rebranch(call1)
    if direction is not None:
        assert "仕事の場で" not in direction.branch_specific_form
        assert "進路" in direction.branch_specific_form or "生活" in direction.branch_specific_form
    body = (
        "一度決めた測り方を固定しなくてよい。いまの問いの置き方を、静かに見直す余地がある。\n\n"
        "いまも残る問いは、進路上の自己と別の形成のあいだとして並んでいる。"
    )
    ok, missing, _ = re_branch_realization_check(body)
    assert ok, missing


def test_romance_branch_point_accepts_sakai_me():
    body = (
        "20代後半に、長く付き合っていた人と別れた。"
        "この出来事は、ただ一度の別れというより、関係を続けることと別れることの境目に立った時間だった。"
    )
    assert _section_claim_realized("branch_point", body, "")


def test_health_causality_rewrite_clears_wo_kaeru_trip():
    raw = (
        "38歳のときに体調を崩し、働き方を変えるかを考えたことは、"
        "一度きりの判断というより、身体の制約に合わせて生活をどう成り立たせるかが分かれた境界だった。"
    )
    fixed = rewrite_unsupported_causality_phrases(raw)
    assert "を変える" not in fixed
    assert "どう置くか" in fixed
    g = GroundedInput(
        facts=[
            GroundedFact(
                id="f1",
                content="38歳のときに体調を崩し、仕事量を減らして治療と休養を優先した",
                boundary_type=FactBoundaryType.explicit_fact,
            )
        ],
        current_context=["治療を続けながら在宅中心で仕事をしている"],
    )
    assert detect_unsupported_causality(fixed, g, sensitive=True) == []


def test_health_lost_unverifiability_realized():
    body = (
        "失ったのは、以前と同じペースで働き続ける側で続いていた身体条件や働き方を、"
        "いま同じように辿って確かめることではないか。"
        "仕事量を抑えて働いている現在からは、その連続が実際にどこまで続いたのかを検証することはできない。"
    )
    assert _section_claim_realized("lost", body, "")
    assert all(lab for lab in LOCKED_PUBLIC_LABELS_JA[:1])  # freeze smoke
