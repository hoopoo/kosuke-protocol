"""Endpoint-level language smoke tests for the Protocol Experience.

These use FastAPI's TestClient against the real engines and vector store, with
no OpenAI key configured, to confirm the guided flow stays single-language end
to end (the most important regression to guard against).
"""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def _has_cjk(text: str) -> bool:
    return bool(CJK.search(text))


@pytest.fixture(autouse=True)
def _no_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_japanese_flow_is_japanese_only(client):
    r = client.post(
        "/experience/fragment",
        json={"text": "昔住んでいた街のことを、ときどき急に思い出す。", "language": "ja"},
    )
    assert r.status_code == 200
    frags = r.json()["fragments"]
    assert 4 <= len(frags) <= 7
    selected = frags[-1]["text"]

    for mode in ("near", "far", "time", "chance"):
        s = client.post(
            "/experience/sample",
            json={"fragment_text": selected, "mode": mode, "language": "ja"},
        )
        assert s.status_code == 200
        sampled = s.json()["sampled_fragment"]["text"]
        assert _has_cjk(sampled), f"Japanese sample returned non-Japanese: {sampled!r}"

    data = s.json()
    fk = client.post(
        "/experience/fluke",
        json={
            "original_fragment": data["selected_fragment"],
            "sampled_fragment": data["sampled_fragment"],
            "language": "ja",
        },
    )
    assert fk.status_code == 200
    fluke = fk.json()
    assert _has_cjk(fluke["tension"])
    assert _has_cjk(fluke["reflection_prompt"])


def test_english_flow_is_english_only(client):
    r = client.post(
        "/experience/fragment",
        json={
            "text": "I changed jobs and gained time, but lost track of what I want.",
            "language": "en",
        },
    )
    assert r.status_code == 200
    selected = r.json()["fragments"][-1]["text"]

    for mode in ("near", "far", "time", "chance"):
        s = client.post(
            "/experience/sample",
            json={"fragment_text": selected, "mode": mode, "language": "en"},
        )
        assert s.status_code == 200
        sampled = s.json()["sampled_fragment"]["text"]
        assert not _has_cjk(sampled), f"English sample returned Japanese: {sampled!r}"

    data = s.json()
    fk = client.post(
        "/experience/fluke",
        json={
            "original_fragment": data["selected_fragment"],
            "sampled_fragment": data["sampled_fragment"],
            "language": "en",
        },
    )
    assert fk.status_code == 200
    fluke = fk.json()
    assert not _has_cjk(fluke["tension"])
    assert not _has_cjk(fluke["reflection_prompt"])


def test_export_markdown_single_card(client):
    r = client.post(
        "/experience/export",
        json={
            "source_text": "源のテキスト",
            "original_fragment_text": "手放せない記憶",
            "sampled_fragment_text": "終わっていない時間",
            "tension": "二つは同じことを指している。",
            "reflection_question": "何が変わりますか。",
            "reflection": "まだ終わらせていなかった。",
            "meaning": "決められないのではなく、まだ終わらせていなかった。",
            "sampling_mode": "far",
            "language": "ja",
        },
    )
    assert r.status_code == 200
    assert "決められないのではなく" in r.text
    assert r.text.startswith("#")
