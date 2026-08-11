"""Unit tests for Deep Reading SessionStore protocol (memory backend)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.parallel_life_deep_reading.session_store import (
    InMemorySessionStore,
    SessionExpiredError,
    StaleSessionRevisionError,
    is_expired,
)


def test_create_get_exists_delete():
    store = InMemorySessionStore()
    session = store.create(raw_user_input="分岐の話", language="ja")
    assert session.session_id
    assert session.session_revision == 0
    assert session.expires_at
    assert store.exists(session.session_id)
    got = store.get(session.session_id)
    assert got is not None
    assert got.raw_user_input == "分岐の話"
    store.delete(session.session_id)
    assert store.get(session.session_id) is None


def test_save_increments_revision_and_extends_ttl():
    store = InMemorySessionStore()
    session = store.create(raw_user_input="x")
    first_exp = session.expires_at
    session.status = session.status  # no-op touch
    session.raw_user_input = "updated"
    saved = store.save(session, expected_revision=0)
    assert saved.session_revision == 1
    assert saved.raw_user_input == "updated"
    assert saved.expires_at >= first_exp
    again = store.save(saved, expected_revision=1)
    assert again.session_revision == 2


def test_stale_revision_rejected():
    store = InMemorySessionStore()
    session = store.create(raw_user_input="x")
    store.save(session, expected_revision=0)
    with pytest.raises(StaleSessionRevisionError):
        store.save(session, expected_revision=0)


def test_expired_session_get_returns_none():
    store = InMemorySessionStore()
    session = store.create(raw_user_input="x")
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with store._lock:
        stored = store._sessions[session.session_id]
        store._sessions[session.session_id] = stored.model_copy(update={"expires_at": past})
    assert store.get(session.session_id) is None
    assert not store.exists(session.session_id)


def test_save_expired_raises():
    store = InMemorySessionStore()
    session = store.create(raw_user_input="x")
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with store._lock:
        stored = store._sessions[session.session_id]
        store._sessions[session.session_id] = stored.model_copy(update={"expires_at": past})
    with pytest.raises(SessionExpiredError):
        store.save(session, expected_revision=0)


def test_is_expired_helper():
    store = InMemorySessionStore()
    session = store.create(raw_user_input="x")
    assert not is_expired(session)
    past = session.model_copy(
        update={"expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
    )
    assert is_expired(past)
