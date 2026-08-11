"""Production Candidate v1.0.3 — unsupported causality / affect / role + present-anchor."""

from __future__ import annotations

from app.parallel_life_deep_reading.fixtures import build_case1_call1
from app.parallel_life_deep_reading.models import (
    FactBoundaryType,
    GroundedFact,
    GroundedInput,
    ResidueCandidate,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.runtime_validation import (
    detect_unsupported_affect,
    detect_unsupported_causality,
    detect_unsupported_role_behavior,
    recalculate_publication_gate,
    validate_residue_candidate,
)


def test_prompt_versions_v103():
    # v1.0.3 overreach suite remains valid; Call2/3 advanced to v1.0.3 in v1.0.4.
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


def test_open_causal_question_allowed():
    grounded = _uni_grounded()
    body = (
        "過去の選択が現在の生活にどのように影響を与えたのかを考えることがある。"
        "因果関係までは分からない。"
    )
    assert detect_unsupported_causality(body, grounded) == []


def test_neutralize_preserves_present_clause():
    from app.parallel_life_deep_reading.runtime_validation import (
        neutralize_causality_excerpts,
    )

    body = (
        "この選択は、現在も妻と息子との三人家族で暮らし、自分の会社を経営している"
        "という生活構造に繋がっている。問いが残っている。"
    )
    excerpt = (
        "この選択は、現在も妻と息子との三人家族で暮らし、自分の会社を経営している"
        "という生活構造に繋がっている。"
    )
    out = neutralize_causality_excerpts(body, [excerpt])
    assert "経営している" in out
    assert "繋が" not in out
    assert "残っている" in out


def test_a_unsupported_causality_blocked():
    grounded = _uni_grounded()
    body = "大学での経験が現在の経営観に影響を与えている。"
    findings = detect_unsupported_causality(body, grounded)
    assert findings, "causal assertion without explicit support must block"
    assert findings[0].causality_strength >= 2


def test_a2_variant_causality_spellings_blocked():
    grounded = _uni_grounded()
    for body in (
        "この出来事が選択に繋がった。",
        "この出来事は選んだ人生へとつながった。",
        "この経験はキャリアの基盤を形成している。",
        "この選択は異なる未来を開いた。",
        "創作があったかもしれないという思索をもたらす。",
        "合格したことが現在の生活に与える影響を並べると見えてくる。",
        "この選択は選ばなかった結果である。",
        "過去の選択と現在の生活は繋がっている。",
        "この選択が現在の生活にどのように影響を与えているのかを考えると、経営していることが見えてくる。",
        "これにより、さまざまな経験を積むことができた。",
        "この選択の結果、現在も三人家族で暮らしている。",
        "この経歴は大学選択の影響を受けているのかもしれない。",
    ):
        findings = detect_unsupported_causality(body, grounded)
        assert findings, f"expected block for: {body}"


def test_e_supported_causality_allowed():
    grounded = GroundedInput(
        facts=[
            GroundedFact(
                id="f1",
                content="この経験がきっかけで転職した",
                boundary_type=FactBoundaryType.explicit_fact,
                source_text="この経験がきっかけで転職した",
            ),
            GroundedFact(
                id="f2",
                content="現在は別の会社で働いている",
                boundary_type=FactBoundaryType.explicit_fact,
                source_text="現在は別の会社で働いている",
            ),
        ],
        current_context=["現在は別の会社で働いている"],
        confirmed_by_user=True,
    )
    body = "この経験をきっかけに転職した。"
    findings = detect_unsupported_causality(body, grounded)
    assert findings == []


def test_f_qualified_association_allowed():
    grounded = _uni_grounded()
    body = (
        "現在の選択基準と並べて見ると、共通する関心は読み取れる。"
        "ただし因果関係までは確認できない。"
    )
    findings = detect_unsupported_causality(body, grounded)
    assert findings == []


def test_b2_unsupported_as_unsupported_affect():
    grounded = GroundedInput(
        feelings=[
            GroundedFact(
                id="feel1",
                content="楽しいと感じている",
                boundary_type=FactBoundaryType.user_feeling,
            )
        ],
        current_context=["現在は三人家族で暮らしている"],
        confirmed_by_user=True,
    )
    body = "息子を授かったことは、新たな喜びをもたらした。"
    assert detect_unsupported_affect(body, grounded)
    assert detect_unsupported_causality(body, grounded)


def test_b_unsupported_affect():
    grounded = GroundedInput(
        facts=[
            GroundedFact(
                id="f1",
                content="現在は妻と息子との三人家族で暮らしている",
                boundary_type=FactBoundaryType.explicit_fact,
            )
        ],
        feelings=[
            GroundedFact(
                id="feel1",
                content="家庭という感じがして楽しい",
                boundary_type=FactBoundaryType.user_feeling,
                source_text="家庭という感じがして楽しい",
            )
        ],
        current_context=["現在は妻と息子との三人家族で暮らしている"],
        confirmed_by_user=True,
    )
    # 楽しい does not license 満足
    body = "現在の家族に満足している。"
    findings = detect_unsupported_affect(body, grounded)
    assert findings
    assert findings[0].affect_type == "満足"

    allowed = "現在の家庭生活を楽しいと感じている。"
    assert detect_unsupported_affect(allowed, grounded) == []


def test_c_unsupported_role_behavior():
    grounded = GroundedInput(
        facts=[
            GroundedFact(
                id="f1",
                content="息子は可愛い",
                boundary_type=FactBoundaryType.explicit_fact,
                source_text="息子は可愛い",
            )
        ],
        feelings=[
            GroundedFact(
                id="feel1",
                content="息子は可愛いと感じている",
                boundary_type=FactBoundaryType.user_feeling,
            )
        ],
        current_context=["現在は妻と息子との三人家族で暮らしている"],
        confirmed_by_user=True,
    )
    body = "息子の成長を見守っている。"
    findings = detect_unsupported_role_behavior(body, grounded)
    assert findings
    assert "成長を見守" in findings[0].role_type


def test_d_question_cannot_satisfy_present_anchor():
    """「二人目がいたらどうだったか」 may be past/question anchor, not present_life."""
    call1 = build_case1_call1()
    q = next(
        q
        for q in call1.grounded_input.questions
        if "二人目" in q.content or "どうだったか" in q.content
    )
    # Question alone as present anchor → reject
    bad = ResidueCandidate(
        residue_statement="過去の分岐のあとで現在の生活構造が続いており未接続が残っている",
        past_anchor_ids=["fact_003"],
        present_anchor_ids=[q.id],
        advances_manuscript=True,
        inference_distance="near",
    )
    ok, reason = validate_residue_candidate(bad, call1.grounded_input, sensitive=True)
    assert ok is None
    assert "present" in reason

    # Same question may appear as past/question-side anchor with real present life
    good = ResidueCandidate(
        residue_statement="二人目の問いのあとでも、三人家族での暮らしと経営が続いており未接続が残っている",
        past_anchor_ids=[q.id],
        present_anchor_ids=["fact_005"],
        advances_manuscript=True,
        inference_distance="near",
    )
    ok2, reason2 = validate_residue_candidate(good, call1.grounded_input, sensitive=True)
    assert ok2 is not None, reason2
    assert q.id not in ok2.present_anchor_ids
    assert "fact_005" in ok2.present_anchor_ids


def test_publication_gate_blocks_new_categories():
    call1 = build_case1_call1()
    call1.grounded_input.confirmed_by_user = True
    body = (
        "大学での経験が現在の経営観に影響を与えている。"
        "現在の家族に満足している。"
        "息子の成長を見守っている。"
        "現在は妻と息子との三人家族で暮らしている。"
    )
    gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=None,
        body=body,
        title=call1.central_thesis.statement[:40],
        subtitle="",
        rebranch_candidates=[],
    )
    assert gate.unsupported_causality_count >= 1
    assert gate.unsupported_affect_count >= 1
    assert gate.unsupported_role_behavior_count >= 1
    assert "unsupported_causality" in gate.blocking_reasons
    assert "unsupported_affect" in gate.blocking_reasons
    assert "unsupported_role_behavior" in gate.blocking_reasons
    assert gate.publishable is False


def test_manual_fidelity_gap_flag_when_residual_overreach_publishable():
    """Diagnostic: publishable but residual soft-overreach phrases remain."""
    call1 = build_case1_call1()
    call1.grounded_input.confirmed_by_user = True
    # Inject explicit causal evidence so detectors may pass while phrase remains
    # (gap detector watches residual soft phrases independently).
    call1.grounded_input.facts.append(
        GroundedFact(
            id="fact_causal",
            content="影響を与えている",
            boundary_type=FactBoundaryType.explicit_fact,
            source_text="影響を与えている",
        )
    )
    # Build a body that is otherwise likely publishable after gate strips —
    # we only assert the flag field exists and follows the documented rule:
    # true when publishable AND residual soft phrases remain.
    from app.parallel_life_deep_reading.runtime_validation import (
        detect_unsupported_causality,
    )

    # If corpus contains the exact phrase, causality detector allows it;
    # residual pattern check should still set gap when publishable.
    body_allowed = "影響を与えている。現在は妻と息子との三人家族で暮らしている。問いが残っている。"
    assert detect_unsupported_causality(body_allowed, call1.grounded_input) == []
    gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=None,
        body=body_allowed,
        title=call1.central_thesis.statement[:40] or "分岐を読み直す",
        subtitle="",
        rebranch_candidates=[],
    )
    if gate.publishable:
        assert gate.manual_fidelity_gap_possible is True
