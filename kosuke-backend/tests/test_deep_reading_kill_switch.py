"""Kill switch: DEEP_READING_ENABLED=false → 503; Standard routes untouched."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient


def test_deep_reading_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("DEEP_READING_ENABLED", "false")
    # Re-import is heavy; call helper + route via client after env set at import.
    # main reads env at request time via deep_reading_enabled().
    from app import main as main_mod

    assert main_mod.deep_reading_enabled() is False
    client = TestClient(main_mod.app)
    enabled = client.get("/experience/parallel-life/deep-reading/enabled")
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is False

    ground = client.post(
        "/experience/parallel-life/deep-reading/ground",
        json={"source_text": "分岐", "language": "ja"},
    )
    assert ground.status_code == 503
    assert "メンテナンス" in ground.json()["detail"]


def test_deep_reading_enabled_probe_true(monkeypatch):
    monkeypatch.setenv("DEEP_READING_ENABLED", "true")
    from app import main as main_mod

    assert main_mod.deep_reading_enabled() is True
    client = TestClient(main_mod.app)
    res = client.get("/experience/parallel-life/deep-reading/enabled")
    assert res.status_code == 200
    assert res.json()["enabled"] is True


def test_healthz_includes_flag(monkeypatch):
    monkeypatch.setenv("DEEP_READING_ENABLED", "false")
    from app import main as main_mod

    client = TestClient(main_mod.app)
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["deep_reading_enabled"] is False
