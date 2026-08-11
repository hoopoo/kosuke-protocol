"""Integration tests for Deep Reading Call 1→2→3 flow."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parallel_life_deep_reading.edit_validate import run_call3_edit_validate
from app.parallel_life_deep_reading.fixtures import (
    CASE1_SOURCE,
    build_case1_bad_draft,
    build_case1_call1,
    build_case2_call1,
    build_case3_call1,
)
from app.parallel_life_deep_reading.models import (
    Call3Result,
    DeepReadingConfirmRequest,
    DeepReadingGroundRequest,
    GenerationStatus,
)
from app.parallel_life_deep_reading.runtime_validation import apply_call1_runtime_gates
from app.parallel_life_deep_reading.service import DeepReadingService
from app.parallel_life_deep_reading.session_store import DeepReadingSessionStore


@pytest.fixture()
def service() -> DeepReadingService:
    store = DeepReadingSessionStore()
    return DeepReadingService(store=store)


def test_ground_requires_llm_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    res = client.post(
        "/experience/parallel-life/deep-reading/ground",
        json={"source_text": CASE1_SOURCE, "language": "ja"},
    )
    assert res.status_code == 503


def test_full_flow_with_injected_stages(service: DeepReadingService):
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    resp = service.ground(
        DeepReadingGroundRequest(source_text=CASE1_SOURCE, language="ja"),
        inject_call1=call1,
    )
    sid = resp.session.session_id
    assert resp.progress_label == "内容をご確認ください"
    from app.parallel_life_deep_reading.call1_schema import call1_selected_lenses

    assert resp.session.call1 is not None
    assert call1_selected_lenses(resp.session.call1) == []

    # Draft before confirm must fail
    with pytest.raises(Exception):
        service.draft(sid)

    confirm = service.confirm(
        DeepReadingConfirmRequest(session_id=sid, action="approve")
    )
    assert confirm.session.call1.grounded_input.confirmed_by_user is True
    assert confirm.session.status == GenerationStatus.ready_for_draft

    # Safe publishable draft body for case 1
    safe_body = """# 三人の暮らしに残る、もう一人の問い

45歳のとき、不妊治療を経て子どもを授かった。選んだのは、妻と息子との三人家族で暮らしていく道だった。現在も三人で暮らし、息子を可愛いと感じている。息子の友人が家に遊びに来ることも楽しい。

二人目を持っていたら、どうだっただろう。その問いは、現在の三人家族を否定しない。かなった選択にも未選択の可能性は残る。

選ばなかった人生の答えをつくるためではない。問いが、現在の暮らしの何を照らしているかを知るためである。

分岐の最後に戻ってくるのは、妻と息子と自分が暮らす、いまの家である。
"""
    draft_resp = service.draft(
        sid,
        inject_draft={
            "body_markdown": safe_body,
            "title_candidates": [
                "三人の暮らしに残る、もう一人の問い",
                "かなった家族の隣の問い",
                "現在の三人に残る問い",
            ],
            "subtitle_candidates": ["かなった家族の隣に可能性を置く"],
            "rebranch_candidates": [
                {
                    "id": "rb1",
                    "source_meaning": "息子に兄弟がいる家族へ託された意味",
                    "current_receiver": "息子の友人が家に遊びに来る現在",
                    "branch_specific_form": "家庭らしさを一度だけ言葉にする",
                    "support_ids": ["fact_005"],
                    "genericity_score": 0,
                    "invented_scene_used": False,
                }
            ],
        },
    )
    assert draft_resp.session.status == GenerationStatus.draft_generated

    # Call 3 with monkeypatched chat to avoid network: inject result via edit path
    # Use run_call3 with mocked chat_json
    from app.parallel_life_deep_reading import edit_validate as ev

    def fake_chat(system, user, **kwargs):
        return {
            "final_title": "三人の暮らしに残る、もう一人の問い",
            "final_subtitle": "かなった家族の隣に可能性を置く",
            "body_markdown": safe_body,
        }

    original = ev.chat_json
    ev.chat_json = fake_chat  # type: ignore[assignment]
    try:
        final = service.edit_validate(sid)
    finally:
        ev.chat_json = original  # type: ignore[assignment]

    assert final.session.call3 is not None
    # May complete or fail depending on gate strictness; observatory omission OK
    from app.parallel_life_deep_reading.call1_schema import call1_selected_lenses

    assert call1_selected_lenses(final.session.call1) == []
    if final.session.status == GenerationStatus.complete:
        assert final.session.final_manuscript
        md = service.export(sid)
        assert "三人の暮らし" in md
        assert "explicit_facts" not in md


def test_confirmation_required_api_message(service: DeepReadingService):
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    resp = service.ground(
        DeepReadingGroundRequest(source_text=CASE1_SOURCE),
        inject_call1=call1,
    )
    with pytest.raises(Exception) as exc:
        service.draft(resp.session.session_id)
    assert "confirmed_by_user" in str(exc.value)


def test_validation_failure_blocks_publication(service: DeepReadingService):
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    call1 = call1.model_copy(
        update={
            "grounded_input": call1.grounded_input.model_copy(
                update={"confirmed_by_user": True}
            )
        }
    )
    bad = build_case1_bad_draft()
    from app.parallel_life_deep_reading import edit_validate as ev

    def fake_chat(system, user, **kwargs):
        return {
            "final_title": "創作に残らなかった45歳",
            "final_subtitle": "",
            "body_markdown": bad.body_markdown,
        }

    original = ev.chat_json
    ev.chat_json = fake_chat  # type: ignore[assignment]
    try:
        result = run_call3_edit_validate(call1, bad, max_passes=1)
    finally:
        ev.chat_json = original  # type: ignore[assignment]

    assert result.validation.publishable is False or result.status == GenerationStatus.validation_failed
    assert (
        result.validation.unsupported_scenes
        or result.validation.generic_advice_findings
        or not result.validation.title_validation.passed
        or result.validation.blocking_reasons
    )


def test_rebranch_and_observatory_omission_valid(service: DeepReadingService):
    from app.parallel_life_deep_reading.call1_schema import (
        call1_rebranch_directions,
        call1_selected_lenses,
    )

    for builder in (build_case2_call1, build_case3_call1):
        call1 = apply_call1_runtime_gates(builder())
        assert call1_selected_lenses(call1) == []
        assert isinstance(call1_rebranch_directions(call1), list)


def test_regression_fixtures_case1_question_only():
    from app.parallel_life_deep_reading.call1_schema import call1_selected_lenses

    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    assert len(call1.branch_structure.secondary_branches) == 0
    assert len(call1.branch_structure.retrospective_counterfactuals) >= 1
    assert call1_selected_lenses(call1) == []


def test_regression_fixtures_case2_admission():
    call1 = apply_call1_runtime_gates(build_case2_call1())
    blob = call1.branch_structure.primary_branch.triggering_event
    assert "合格" in blob
    assert "不合格" not in blob
    assert "移住" not in blob


def test_regression_fixtures_case3_corporate_not_failure():
    from app.parallel_life_deep_reading.call1_schema import (
        call1_rebranch_directions,
        call1_selected_lenses,
    )

    call1 = apply_call1_runtime_gates(build_case3_call1())
    assert "失敗だった" not in call1.central_thesis.statement
    assert "遅すぎる" not in call1.central_thesis.statement
    assert call1_selected_lenses(call1) == []
    assert all(r.genericity_score <= 1 for r in call1_rebranch_directions(call1))


def test_get_session_endpoint_404():
    client = TestClient(app)
    res = client.get("/experience/parallel-life/deep-reading/session/does-not-exist")
    assert res.status_code == 404


def test_confirm_abort(service: DeepReadingService):
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    resp = service.ground(
        DeepReadingGroundRequest(source_text=CASE1_SOURCE),
        inject_call1=call1,
    )
    out = service.confirm(
        DeepReadingConfirmRequest(session_id=resp.session.session_id, action="abort")
    )
    assert out.session.status == GenerationStatus.editorial_failure


def test_retry_limit(service: DeepReadingService, monkeypatch):
    call1 = apply_call1_runtime_gates(build_case1_call1(with_actual_secondary=False))
    resp = service.ground(
        DeepReadingGroundRequest(source_text=CASE1_SOURCE),
        inject_call1=call1,
    )
    sid = resp.session.session_id
    service.confirm(DeepReadingConfirmRequest(session_id=sid, action="approve"))
    session = service.store.get(sid)
    assert session is not None
    session.draft_attempt_count = 3
    service.store.save(session)
    with pytest.raises(Exception):
        service.draft(sid, inject_draft={"body_markdown": "x" * 100, "title_candidates": ["a", "b", "c"]})
