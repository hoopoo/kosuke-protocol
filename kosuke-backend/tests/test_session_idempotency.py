"""Idempotency + revision persistence for draft/edit (no live Cloudflare)."""

from __future__ import annotations

from app.parallel_life_deep_reading.models import (
    Call1Result,
    Call2Draft,
    Call3Result,
    Call3Validation,
    GenerationStatus,
    GroundedInput,
)
from app.parallel_life_deep_reading.service import DeepReadingService
from app.parallel_life_deep_reading.session_store import InMemorySessionStore


def _confirmed_call1() -> Call1Result:
    return Call1Result(
        grounded_input=GroundedInput(confirmed_by_user=True),
        status=GenerationStatus.ready_for_draft,
    )


def test_draft_idempotency_replays_without_second_generation():
    store = InMemorySessionStore()
    service = DeepReadingService(store=store)
    session = store.create(raw_user_input="x")
    session.call1 = _confirmed_call1()
    session = store.save(session, expected_revision=0)

    draft_a = Call2Draft(
        body_markdown="原稿A\n",
        status=GenerationStatus.draft_generated,
    )
    r1 = service.draft(session.session_id, inject_draft=draft_a, idempotency_key="k1")
    assert r1.session.call2 is not None
    assert r1.session.draft_attempt_count == 1

    draft_b = Call2Draft(
        body_markdown="原稿B_SHOULD_NOT_APPLY\n",
        status=GenerationStatus.draft_generated,
    )
    r2 = service.draft(session.session_id, inject_draft=draft_b, idempotency_key="k1")
    assert r2.session.call2 is not None
    assert "原稿A" in (r2.session.call2.body_markdown or "")
    assert r2.session.draft_attempt_count == 1


def test_edit_idempotency_replays():
    store = InMemorySessionStore()
    service = DeepReadingService(store=store)
    session = store.create(raw_user_input="x")
    session.call1 = _confirmed_call1()
    session.call2 = Call2Draft(body_markdown="draft\n")
    session = store.save(session, expected_revision=0)

    call3 = Call3Result(
        final_title="T",
        body_markdown="body\n",
        status=GenerationStatus.complete,
        validation=Call3Validation(publishable=True),
    )
    r1 = service.edit_validate(session.session_id, inject_call3=call3, idempotency_key="e1")
    assert r1.session.status == GenerationStatus.complete
    assert r1.session.edit_attempt_count == 1

    call3_b = Call3Result(
        final_title="OTHER",
        body_markdown="other\n",
        status=GenerationStatus.complete,
        validation=Call3Validation(publishable=True),
    )
    r2 = service.edit_validate(session.session_id, inject_call3=call3_b, idempotency_key="e1")
    assert r2.session.call3 is not None
    assert r2.session.call3.final_title == "T"
    assert r2.session.edit_attempt_count == 1
