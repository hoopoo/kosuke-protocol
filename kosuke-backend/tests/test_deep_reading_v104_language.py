"""Production Candidate v1.0.4 — causal frame, title frame, schema leakage."""

from __future__ import annotations

from app.parallel_life_deep_reading.models import (
    FactBoundaryType,
    GroundedFact,
    GroundedInput,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.runtime_validation import (
    detect_schema_leakage_prose,
    detect_unsupported_causal_frame,
    detect_unsupported_causality,
    repair_schema_leakage_prose,
    title_has_unsupported_causal_frame,
    validate_title,
)


def test_prompt_versions_v104():
    assert PROMPT_VERSIONS["call_1"] == "parallel-life-call-1-v1.0.3"
    assert PROMPT_VERSIONS["call_2"] == "parallel-life-call-2-v1.0.3"
    assert PROMPT_VERSIONS["call_3"] == "parallel-life-call-3-v1.0.3"


def _uni_grounded() -> GroundedInput:
    return GroundedInput(
        facts=[
            GroundedFact(
                id="fact_u1",
                content="大学に合格し進学した",
                boundary_type=FactBoundaryType.explicit_fact,
                source_text="大学に合格し進学した",
            ),
            GroundedFact(
                id="fact_u2",
                content="現在は自分の会社を経営している",
                boundary_type=FactBoundaryType.explicit_fact,
                source_text="現在は自分の会社を経営している",
            ),
        ],
        current_context=["現在は自分の会社を経営している"],
        confirmed_by_user=True,
    )


def test_a_unsupported_causal_frame():
    grounded = _uni_grounded()
    for body in (
        "現在の経営観にどのような影響を与えているのかを考えることがある。",
        "大学選びが現在の職業にどのように関わっているのかを考えることがある。",
        "これまでの経験が現在の仕事にどのように影響しているのかを考えるが、因果関係を確認することはできない。",
    ):
        findings = detect_unsupported_causal_frame(body, grounded)
        assert findings, body
        assert findings[0].frame_type in {
            "causal_presupposition",
            "unsupported_meaning_completion",
        }


def test_b_title_causal_frame_rejected():
    grounded = _uni_grounded()
    title = "早稲田進学が残した影響"
    assert title_has_unsupported_causal_frame(title, grounded) is True
    tv = validate_title(
        title,
        "",
        grounded,
        "選ばなかった道について考えることがある",
        "現在は自分の会社を経営している。問いが残っている。",
    )
    assert tv.passed is False
    assert tv.title_causal_frame_violation is True
    assert "title_unsupported_causal_frame" in tv.notes


def test_c_schema_leakage_prose():
    body = "この選択は、実際に選んだのは第一志望への進学だった。"
    findings = detect_schema_leakage_prose(body)
    assert findings
    assert findings[0].leakage_type in {
        "double_topic_choice",
        "actual_chosen_wa",
        "choice_wa_jissai",
    }


def test_d_direct_narrative_valid():
    grounded = _uni_grounded()
    body = "第一志望の早稲田大学第一文学部へ進学した。"
    assert detect_schema_leakage_prose(body) == []
    assert detect_unsupported_causal_frame(body, grounded) == []
    assert detect_unsupported_causality(body, grounded) == []


def test_e_qualified_comparison_valid():
    grounded = _uni_grounded()
    body = (
        "現在の仕事観とこの経験には似た判断軸が見えるが、因果関係までは確認できない。"
    )
    assert detect_unsupported_causal_frame(body, grounded) == []
    assert detect_unsupported_causality(body, grounded) == []


def test_causal_change_and_bond_blocked():
    grounded = _uni_grounded()
    for body in (
        "この出来事は、私の学びの道を大きく変えるものであった。",
        "この仕事は、過去の学びと深く結びついている。",
    ):
        assert detect_unsupported_causality(body, grounded), body


def test_schema_leakage_repair_rewrites_double_topic():
    body = "この選択は、実際に選んだのは第一志望の大学へ進学する道だった。問いが残っている。"
    out = repair_schema_leakage_prose(body)
    assert "この選択は、実際に選んだのは" not in out
    assert "実際に選んだのは" not in out
    assert "第一志望" in out
