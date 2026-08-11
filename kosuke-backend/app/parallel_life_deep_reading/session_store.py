"""Deep Reading session store — memory (local) or Durable Object HTTP (Cloudflare).

Business logic must depend only on SessionStoreProtocol, never on DO/D1 directly.
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol, runtime_checkable

import httpx

from app.parallel_life_deep_reading.models import DeepReadingSession, GenerationStatus
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS

DEFAULT_SESSION_TTL_HOURS = 24


class StaleSessionRevisionError(RuntimeError):
    """Raised when expected_revision does not match stored session_revision."""


class SessionExpiredError(RuntimeError):
    """Raised when session exists but expires_at is in the past."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _expires_iso(hours: int = DEFAULT_SESSION_TTL_HOURS) -> str:
    return (_now() + timedelta(hours=hours)).isoformat()


def parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_expired(session: DeepReadingSession, *, now: Optional[datetime] = None) -> bool:
    exp = parse_iso(session.expires_at)
    if exp is None:
        return False
    return (now or _now()) >= exp


@runtime_checkable
class SessionStoreProtocol(Protocol):
    def create(
        self,
        *,
        raw_user_input: str,
        language: str = "ja",
        clarifications: dict | None = None,
        editorial_context: dict | None = None,
    ) -> DeepReadingSession: ...

    def get(self, session_id: str) -> Optional[DeepReadingSession]: ...

    def save(
        self,
        session: DeepReadingSession,
        *,
        expected_revision: int | None = None,
        extend_ttl: bool = True,
    ) -> DeepReadingSession: ...

    def delete(self, session_id: str) -> None: ...

    def exists(self, session_id: str) -> bool: ...


class InMemorySessionStore:
    """Process-local session map for local development and tests."""

    def __init__(self, *, ttl_hours: int = DEFAULT_SESSION_TTL_HOURS) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, DeepReadingSession] = {}
        self._ttl_hours = ttl_hours

    def create(
        self,
        *,
        raw_user_input: str,
        language: str = "ja",
        clarifications: dict | None = None,
        editorial_context: dict | None = None,
    ) -> DeepReadingSession:
        session_id = str(uuid.uuid4())
        now = _now_iso()
        session = DeepReadingSession(
            session_id=session_id,
            raw_user_input=raw_user_input,
            language=language,
            clarifications=dict(clarifications or {}),
            editorial_context=dict(editorial_context or {}),
            prompt_versions=dict(PROMPT_VERSIONS),
            model_metadata={},
            status=GenerationStatus.ready_for_user_confirmation,
            created_at=now,
            updated_at=now,
            session_revision=0,
            expires_at=_expires_iso(self._ttl_hours),
            idempotency_keys={},
        )
        with self._lock:
            self._sessions[session_id] = session
        return session.model_copy(deep=True)

    def get(self, session_id: str) -> Optional[DeepReadingSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if is_expired(session):
                self._sessions.pop(session_id, None)
                return None
            return session.model_copy(deep=True)

    def save(
        self,
        session: DeepReadingSession,
        *,
        expected_revision: int | None = None,
        extend_ttl: bool = True,
    ) -> DeepReadingSession:
        with self._lock:
            current = self._sessions.get(session.session_id)
            if current is None:
                raise KeyError("session_not_found")
            if is_expired(current):
                self._sessions.pop(session.session_id, None)
                raise SessionExpiredError("session_expired")
            if expected_revision is not None and current.session_revision != expected_revision:
                raise StaleSessionRevisionError(
                    f"stale_revision: expected={expected_revision} actual={current.session_revision}"
                )
            next_rev = current.session_revision + 1
            updated = session.model_copy(
                update={
                    "session_revision": next_rev,
                    "updated_at": _now_iso(),
                    "expires_at": (
                        _expires_iso(self._ttl_hours) if extend_ttl else session.expires_at
                    ),
                }
            )
            self._sessions[session.session_id] = updated
            return updated.model_copy(deep=True)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def exists(self, session_id: str) -> bool:
        return self.get(session_id) is not None

    def clear_all(self) -> None:
        """Test helper — never call from production routes."""
        with self._lock:
            self._sessions.clear()


# Back-compat alias
DeepReadingSessionStore = InMemorySessionStore


class HttpDurableObjectSessionStore:
    """HTTP client for the Cloudflare Durable Object session Worker."""

    def __init__(
        self,
        *,
        base_url: str,
        auth_token: str = "",
        ttl_hours: int = DEFAULT_SESSION_TTL_HOURS,
        timeout_s: float = 15.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._token = auth_token
        self._ttl_hours = ttl_hours
        self._timeout = timeout_s

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def create(
        self,
        *,
        raw_user_input: str,
        language: str = "ja",
        clarifications: dict | None = None,
        editorial_context: dict | None = None,
    ) -> DeepReadingSession:
        session_id = str(uuid.uuid4())
        now = _now_iso()
        session = DeepReadingSession(
            session_id=session_id,
            raw_user_input=raw_user_input,
            language=language,
            clarifications=dict(clarifications or {}),
            editorial_context=dict(editorial_context or {}),
            prompt_versions=dict(PROMPT_VERSIONS),
            model_metadata={},
            status=GenerationStatus.ready_for_user_confirmation,
            created_at=now,
            updated_at=now,
            session_revision=0,
            expires_at=_expires_iso(self._ttl_hours),
            idempotency_keys={},
        )
        with httpx.Client(timeout=self._timeout) as client:
            res = client.put(
                f"{self._base}/sessions/{session_id}",
                headers=self._headers(),
                json=session.model_dump(mode="json"),
            )
            res.raise_for_status()
            return DeepReadingSession.model_validate(res.json())

    def get(self, session_id: str) -> Optional[DeepReadingSession]:
        with httpx.Client(timeout=self._timeout) as client:
            res = client.get(
                f"{self._base}/sessions/{session_id}",
                headers=self._headers(),
            )
            if res.status_code == 404:
                return None
            res.raise_for_status()
            session = DeepReadingSession.model_validate(res.json())
            if is_expired(session):
                self.delete(session_id)
                return None
            return session

    def save(
        self,
        session: DeepReadingSession,
        *,
        expected_revision: int | None = None,
        extend_ttl: bool = True,
    ) -> DeepReadingSession:
        payload: dict[str, Any] = {
            "session": session.model_dump(mode="json"),
            "expected_revision": expected_revision,
            "extend_ttl_hours": self._ttl_hours if extend_ttl else None,
        }
        with httpx.Client(timeout=self._timeout) as client:
            res = client.patch(
                f"{self._base}/sessions/{session.session_id}",
                headers=self._headers(),
                json=payload,
            )
            if res.status_code == 409:
                raise StaleSessionRevisionError(res.text)
            if res.status_code == 410:
                raise SessionExpiredError("session_expired")
            if res.status_code == 404:
                raise KeyError("session_not_found")
            res.raise_for_status()
            return DeepReadingSession.model_validate(res.json())

    def delete(self, session_id: str) -> None:
        with httpx.Client(timeout=self._timeout) as client:
            res = client.delete(
                f"{self._base}/sessions/{session_id}",
                headers=self._headers(),
            )
            if res.status_code not in (200, 204, 404):
                res.raise_for_status()

    def exists(self, session_id: str) -> bool:
        return self.get(session_id) is not None


_STORE: SessionStoreProtocol | None = None


def build_session_store() -> SessionStoreProtocol:
    backend = os.environ.get("SESSION_STORE_BACKEND", "memory").strip().lower()
    ttl = int(os.environ.get("SESSION_TTL_HOURS", str(DEFAULT_SESSION_TTL_HOURS)))
    if backend in {"do", "durable_object", "http", "cloudflare"}:
        url = os.environ.get("SESSION_STORE_URL", "").strip()
        if not url:
            raise RuntimeError("SESSION_STORE_URL required when SESSION_STORE_BACKEND=do")
        return HttpDurableObjectSessionStore(
            base_url=url,
            auth_token=os.environ.get("SESSION_STORE_TOKEN", "").strip(),
            ttl_hours=ttl,
        )
    return InMemorySessionStore(ttl_hours=ttl)


def get_session_store() -> SessionStoreProtocol:
    global _STORE
    if _STORE is None:
        _STORE = build_session_store()
    return _STORE


def reset_session_store_for_tests(store: SessionStoreProtocol | None = None) -> SessionStoreProtocol:
    """Replace process-global store (tests only)."""
    global _STORE
    _STORE = store if store is not None else InMemorySessionStore()
    return _STORE
