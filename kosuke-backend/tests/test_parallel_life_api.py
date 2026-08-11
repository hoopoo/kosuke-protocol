"""Endpoint-level tests for the Parallel Life experience.

These use FastAPI's TestClient against the real app, with no OpenAI key
configured, to confirm the dedicated ``/experience/parallel-life`` endpoints
work end to end without requiring the vector store or an API key (product
spec §7, §44).
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


JA_TEXT = "20歳のとき、彼氏と別れて、就職のために田舎へ帰った。あのまま東京に残っていたら、結婚していたのかなと思うことがある。"
EN_TEXT = "At twenty, I ended a relationship and returned to my hometown for work. Sometimes I wonder whether we might have married if I had stayed in Tokyo."


def test_lens_endpoint_is_available(client):
    r = client.get("/experience/parallel-life/lens")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "parallel-life"
    assert data["available"] is True
    assert "standard" in data["supported_depths"]
    assert "editorial" in data["supported_depths"]
    assert len(data["observatory_lenses"]) >= 8


def test_clarify_endpoint_returns_bounded_questions(client):
    r = client.post(
        "/experience/parallel-life/clarify",
        json={"source_text": JA_TEXT, "language": "ja"},
    )
    assert r.status_code == 200
    data = r.json()
    assert 0 <= len(data["questions"]) <= 4


def test_clarify_endpoint_requires_text(client):
    r = client.post(
        "/experience/parallel-life/clarify",
        json={"source_text": "   ", "language": "ja"},
    )
    assert r.status_code == 400


def test_generate_endpoint_japanese_standard(client):
    r = client.post(
        "/experience/parallel-life",
        json={
            "source_text": JA_TEXT,
            "clarifications": {},
            "language": "ja",
            "depth": "standard",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["generation_mode"] == "heuristic"
    assert data["language"] == "ja"
    assert data["depth"] == "standard"
    assert 3 <= len(data["lost"]) <= 6
    assert 3 <= len(data["protected"]) <= 6
    assert 2 <= len(data["observatory_layers"]) <= 4
    ids = [layer["id"] for layer in data["observatory_layers"]]
    assert len(ids) == len(set(ids))
    assert data["cross_lens_synthesis"].strip()
    # Language consistency across the entire structured response.
    for text in (data["title"], data["subtitle"], data["branch_point"], data["closing"]):
        assert _has_cjk(text)


def test_generate_endpoint_english_deep_requires_llm_without_key(client):
    """Legacy depth=deep routes to Editorial Edition, which requires an LLM."""
    r = client.post(
        "/experience/parallel-life",
        json={
            "source_text": EN_TEXT,
            "clarifications": {"age": "20"},
            "language": "en",
            "depth": "deep",
        },
    )
    assert r.status_code == 503
    detail = r.json()["detail"]
    assert "LLM" in detail or "Editorial" in detail


def test_generate_endpoint_deep_with_mock_essay(client, monkeypatch):
    from tests.editorial_essay_fixtures import patch_editorial_essay

    # English request still accepts Japanese mock for routing/depth smoke check.
    patch_editorial_essay(monkeypatch)
    r = client.post(
        "/experience/parallel-life",
        json={
            "source_text": JA_TEXT,
            "clarifications": {"age": "20"},
            "language": "ja",
            "depth": "deep",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["depth"] == "editorial"
    assert data["generation_mode"] == "llm"


def test_generate_endpoint_requires_text(client):
    r = client.post(
        "/experience/parallel-life",
        json={"source_text": "", "language": "ja", "depth": "standard"},
    )
    assert r.status_code == 400


def test_generate_endpoint_clarifications_optional(client):
    r = client.post(
        "/experience/parallel-life",
        json={"source_text": JA_TEXT, "language": "ja"},
    )
    assert r.status_code == 200


def test_export_endpoint_returns_markdown(client):
    gen = client.post(
        "/experience/parallel-life",
        json={"source_text": JA_TEXT, "language": "ja", "depth": "standard"},
    )
    result = gen.json()
    r = client.post(
        "/experience/parallel-life/export",
        json={"result": result, "created_at": "2026-08-06"},
    )
    assert r.status_code == 200
    assert r.text.startswith("#")
    assert "分岐点" in r.text
    assert "Powered by Kosuke Protocol" in r.text


def test_response_contains_no_technical_fields(client):
    r = client.post(
        "/experience/parallel-life",
        json={"source_text": JA_TEXT, "language": "ja"},
    )
    data = r.json()
    for banned in ("embedding", "vector", "fluke_score", "prompt", "model_name"):
        assert banned not in data


def test_generate_endpoint_uses_official_lens_names_in_japanese(client):
    from app.observatory_lenses import OBSERVATORY_LENSES

    r = client.post(
        "/experience/parallel-life",
        json={"source_text": JA_TEXT, "language": "ja", "depth": "standard"},
    )
    assert r.status_code == 200
    data = r.json()
    for layer in data["observatory_layers"]:
        assert layer["title"] == OBSERVATORY_LENSES[layer["id"]].name_en
        assert layer["title"] not in ("市場のシグナル", "プロトコル・パブリッシング", "書物")
        assert layer["descriptor"].strip()


def test_generate_endpoint_title_is_grammatically_valid(client):
    from app.parallel_life_engine import _is_valid_english_title

    r = client.post(
        "/experience/parallel-life",
        json={
            "source_text": "Something happened when I was twenty four.",
            "clarifications": {"age": "24"},
            "language": "en",
            "depth": "standard",
        },
    )
    data = r.json()
    assert _is_valid_english_title(data["title"]), data["title"]


def test_export_endpoint_uses_language_appropriate_closing_heading(client):
    gen_ja = client.post(
        "/experience/parallel-life",
        json={"source_text": JA_TEXT, "language": "ja", "depth": "standard"},
    )
    r_ja = client.post(
        "/experience/parallel-life/export",
        json={"result": gen_ja.json(), "created_at": "2026-08-06"},
    )
    assert "## 結び" in r_ja.text
    assert "## Closing" not in r_ja.text

    gen_en = client.post(
        "/experience/parallel-life",
        json={"source_text": EN_TEXT, "language": "en", "depth": "standard"},
    )
    r_en = client.post(
        "/experience/parallel-life/export",
        json={"result": gen_en.json(), "created_at": "2026-08-06"},
    )
    assert "## Closing" in r_en.text
