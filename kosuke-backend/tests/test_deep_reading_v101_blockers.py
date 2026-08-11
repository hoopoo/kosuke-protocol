"""Production v1.0.1 — Public QA release-blocker regressions (Cases 06/08/09/10)."""

from __future__ import annotations

import pytest

from app.parallel_life_deep_reading import SCHEMA_VERSION
from app.parallel_life_deep_reading.models import (
    BranchStructure,
    Call1Result,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    PrimaryBranch,
    SensitiveDomainAnalysis,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    recalculate_publication_gate,
)
from app.parallel_life_deep_reading.service import (
    DeepReadingGenerationError,
    DeepReadingService,
)
from app.parallel_life_deep_reading.v101_gates import (
    assess_branch_concreteness,
    build_safe_sensitive_coexistence_thesis,
    detect_material_contradictions,
    detect_unrealized_path_modality_violations,
    repair_unrealized_path_modality,
    sensitive_thesis_is_unsupported_causal,
)
from app.parallel_life_deep_reading.models import (
    Call2Draft,
    DeepReadingConfirmRequest,
)


def test_runtime_version_v105():
    assert SCHEMA_VERSION == "parallel-life-runtime-v1.0.6"
    assert PROMPT_VERSIONS["call_1"] == "parallel-life-call-1-v1.0.3"
    assert PROMPT_VERSIONS["call_2"] == "parallel-life-call-2-v1.0.3"
    assert PROMPT_VERSIONS["call_3"] == "parallel-life-call-3-v1.0.3"


def _case09_call1() -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="第一志望の会社に落ちた",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_text="第一志望の会社に落ちた",
                ),
                GroundedFact(
                    id="f2",
                    content="第一志望の会社に入社した",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_text="第一志望の会社に入社した",
                ),
            ],
            current_context=["今は転職して別の会社にいる"],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="22歳",
                triggering_event="第一志望の会社に落ちた",
                realized_path="第一志望の会社に入社した",
                unrealized_paths=["別の会社に入ること"],
                available_paths=["第一志望の会社に入社した", "別の会社に入ること"],
            )
        ),
        central_thesis=CentralThesis(
            statement=(
                "第一志望の会社に落ちたことが、別の会社に入る選択肢を考えるきっかけとなった。"
            )
        ),
        user_confirmation_view=UserConfirmationView(
            branch_period="22歳",
            triggering_event="第一志望の会社に落ちた",
            chosen_path="第一志望の会社に入社した",
            unchosen_path="別の会社に入ること",
            current_context=["今は転職して別の会社にいる"],
            central_thesis_preview=(
                "第一志望の会社に落ちたことが、別の会社に入る選択肢を考えるきっかけとなった。"
            ),
        ),
    )


def test_case09_contradiction_not_ready():
    src = (
        "時期: 22歳\n"
        "出来事: 第一志望の会社に落ちた\n"
        "選んだ道: 第一志望の会社に入社した\n"
        "選ばなかった道: 別の会社に入ること\n"
        "いまの問い: 別の会社だったらどうだったか\n"
        "いまの状況: 今は転職して別の会社にいる"
    )
    raw = _case09_call1()
    assert detect_material_contradictions(raw, source_text=src)
    gated = apply_call1_runtime_gates(raw, source_text=src)
    assert gated.status != GenerationStatus.ready_for_user_confirmation
    assert gated.status == GenerationStatus.needs_additional_input
    assert gated.validation.material_contradiction_count > 0
    assert gated.validation.thesis_deferred_due_to_contradiction is True
    assert not (gated.central_thesis.statement or "").strip()
    assert not gated.residue_candidates.items
    assert gated.user_confirmation_view.items_to_confirm
    assert any("矛盾" in x for x in gated.user_confirmation_view.items_to_confirm)
    assert gated.additional_questions.questions
    assert any("実際にはどちら" in q for q in gated.additional_questions.questions)


def test_case09_call2_blocked_on_approve():
    from app.parallel_life_deep_reading.session_store import DeepReadingSessionStore

    store = DeepReadingSessionStore()
    service = DeepReadingService(store=store)

    # Inject gated Call1 into a fresh session without live LLM
    src = "出来事: 第一志望の会社に落ちた\n選んだ道: 第一志望の会社に入社した"
    gated = apply_call1_runtime_gates(_case09_call1(), source_text=src)
    session = store.create(raw_user_input=src, language="ja")
    session.call1 = gated
    session.status = gated.status
    store.save(session)

    with pytest.raises(DeepReadingGenerationError):
        service.confirm(
            DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
        )
    session2 = store.get(session.session_id)
    assert session2 is not None
    assert session2.call1 is not None
    assert session2.call1.grounded_input.confirmed_by_user is False

    with pytest.raises(DeepReadingGenerationError):
        service.draft(session.session_id)


def test_case08_unrealized_modality_violation_and_repair():
    call1 = Call1Result(
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="家から通える大学にした",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
            current_context=["今はその大学とは関係のない仕事をしている"],
            confirmed_by_user=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="18歳",
                triggering_event="進学先を決めた",
                realized_path="家から通える大学にした",
                unrealized_paths=["地方の大学へ行く"],
            )
        ),
        central_thesis=CentralThesis(statement="進学の選択と現在の問い"),
        user_confirmation_view=UserConfirmationView(
            unchosen_path="地方の大学へ行く",
            chosen_path="家から通える大学にした",
        ),
    )
    bad = "18歳で進学先を決めたとき、家から通える大学を選んだ。地方の大学へ行くことがあった。\n"
    hits = detect_unrealized_path_modality_violations(bad, call1)
    assert hits, "expected modality violation"
    assert any("ことがあった" in h.excerpt for h in hits)

    draft = Call2Draft(body_markdown=bad, title_candidates=["18歳の進学"])
    gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=draft,
        body=bad,
        title="18歳の進学",
        subtitle="",
        rebranch_candidates=[],
    )
    assert gate.unrealized_path_modality_violation_count > 0
    assert "unrealized_path_modality_violation" in gate.blocking_reasons
    assert gate.publishable is False

    repaired = repair_unrealized_path_modality(bad, call1)
    assert "ことがあった" not in repaired
    assert "選ばなかった" in repaired
    hits2 = detect_unrealized_path_modality_violations(repaired, call1)
    assert not hits2


def test_case10_vague_branch_not_ready():
    call1 = Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="なんとなく今まで働いてきた",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f2",
                    content="今の人生を選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
            current_context=["今も仕事をしている"],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="特にない",
                triggering_event="なんとなく今まで働いてきた",
                realized_path="今の人生",
                unrealized_paths=["もっと自由な人生"],
            )
        ),
        central_thesis=CentralThesis(statement="別の人生の選択肢について考える"),
        user_confirmation_view=UserConfirmationView(
            branch_period="特にない",
            triggering_event="なんとなく今まで働いてきた",
            chosen_path="今の人生",
            unchosen_path="もっと自由な人生",
        ),
    )
    assert assess_branch_concreteness(call1).ok is False
    gated = apply_call1_runtime_gates(call1, source_text="時期: 特にない\n出来事: なんとなく今まで働いてきた")
    assert gated.status == GenerationStatus.structural_ambiguity
    assert gated.validation.branch_concreteness_ok is False
    assert not gated.residue_candidates.items
    assert gated.additional_questions.questions
    assert len(gated.additional_questions.questions) <= 2


def test_case06_sensitive_thesis_rejected_and_rewritten():
    call1 = Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="体調を崩して働き方を変えた",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f2",
                    content="仕事量を減らした",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f3",
                    content="今は以前よりゆっくり働いている",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
            feelings=[
                GroundedFact(
                    id="feel1",
                    content="今の働き方は楽だと感じる",
                    boundary_type=FactBoundaryType.user_feeling,
                )
            ],
            current_context=["今は以前よりゆっくり働いている"],
            sensitive_domains=["health", "body"],
        ),
        sensitive_domain_analysis=SensitiveDomainAnalysis(domains=["health", "body"]),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="50歳",
                triggering_event="体調を崩して働き方を変えた",
                realized_path="仕事量を減らした",
                unrealized_paths=["以前と同じように働き続ける"],
            )
        ),
        central_thesis=CentralThesis(
            statement="働き方を変えたことで、今は楽に働けている。"
        ),
        user_confirmation_view=UserConfirmationView(
            chosen_path="仕事量を減らした",
            central_thesis_preview="働き方を変えたことで、今は楽に働けている。",
        ),
    )
    for bad in (
        "働き方を変えたことで、今は楽に働けている。",
        "体調を崩して働き方を変えたことが、今の楽な働き方につながっている。",
        "体調を崩したことで働き方を変えたことは良い選択だった",
    ):
        assert sensitive_thesis_is_unsupported_causal(bad, call1, source_text="") is True, bad
    safe = build_safe_sensitive_coexistence_thesis(call1)
    assert safe
    assert "ことで" not in safe
    assert "つなが" not in safe
    assert "楽" in safe

    gated = apply_call1_runtime_gates(
        call1,
        source_text=(
            "体調を崩して働き方を変えた。仕事量を減らした。"
            "今は以前よりゆっくり働いている。今の働き方は楽だと感じる。"
        ),
    )
    assert gated.validation.sensitive_thesis_rejected is True
    stmt = gated.central_thesis.statement or ""
    assert "ことで" not in stmt
    assert "つなが" not in stmt
    assert "楽" in stmt or stmt == ""
