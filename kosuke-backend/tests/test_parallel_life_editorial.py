"""Tests for Parallel Life Editorial Edition (depth=editorial)."""

from __future__ import annotations

import asyncio
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import (
    EditorialContext,
    ParallelLifeClarifications,
    ParallelLifeEditorialRequest,
    ParallelLifeRequest,
    ParallelLifeResult,
)
from app.parallel_life_editorial import (
    extract_editorial_branch_structure,
    generate_editorial_clarification_questions,
    generate_editorial_parallel_life,
    normalize_depth,
)
from app.parallel_life_editorial_essay import (
    EditorialLLMRequiredError,
    detect_orphan_fragments,
    fact_validate_editorial,
    generate_editorial_essay,
)
from app.parallel_life_domain import extract_grounded_primary_branch
from app.parallel_life_engine import (
    _heuristic_parallel_life,
    export_parallel_life_markdown,
    generate_parallel_life,
)
from tests.editorial_essay_fixtures import (
    FERTILITY_ESSAY_JA,
    UNIVERSITY_ESSAY_JA,
    patch_editorial_essay,
)

FERTILITY_TEXT = """45歳のとき、不妊治療を経て子どもを授かった。
実際に選んだのは、妻と息子と三人で暮らす人生だった。
選ばなかった道は、不妊治療を諦めることだった。
今も、二人目を持っていたらどうだったかと考えることがある。"""

_CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_EN_WORD = re.compile(r"[A-Za-z]{4,}")


def _client():
    return TestClient(app)


def test_normalize_depth_aliases_deep_to_editorial():
    assert normalize_depth("deep") == "editorial"
    assert normalize_depth("editorial") == "editorial"
    assert normalize_depth("standard") == "standard"
    assert normalize_depth(None) == "standard"


def test_editorial_requires_llm_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(EditorialLLMRequiredError):
        asyncio.run(
            generate_editorial_parallel_life(
                ParallelLifeEditorialRequest(
                    source_text=FERTILITY_TEXT,
                    clarifications=ParallelLifeClarifications(
                        chosen_path="妻と息子と三人で暮らす人生",
                    ),
                    language="ja",
                )
            )
        )


def test_editorial_mode_is_distinct_from_standard(monkeypatch):
    patch_editorial_essay(monkeypatch)
    clar = ParallelLifeClarifications(
        chosen_path="妻と息子と三人で暮らす人生",
        unchosen_path="不妊治療を諦めること",
    )
    standard = _heuristic_parallel_life(
        ParallelLifeRequest(
            source_text=FERTILITY_TEXT,
            clarifications=clar,
            language="ja",
            depth="standard",
        )
    )
    editorial = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY_TEXT,
                clarifications=clar,
                editorial_context=EditorialContext(
                    current_life_context="妻と息子との暮らしと仕事"
                ),
                language="ja",
            )
        )
    )
    assert standard.depth == "standard"
    assert editorial.result.depth == "editorial"
    assert editorial.result.generation_mode == "llm"
    assert len(editorial.result.observatory_layers) >= 3
    assert 2 <= len(standard.observatory_layers) <= 3
    assert editorial.branch_structure.secondary_branches
    assert editorial.branch_structure.realized_outcome


def test_editorial_questions_exclude_already_known_facts():
    clar = ParallelLifeClarifications(constraints="費用と時間")
    ctx = EditorialContext(life_before="治療と仕事の往復")
    qs = generate_editorial_clarification_questions(
        FERTILITY_TEXT,
        "ja",
        clarifications=clar,
        editorial_context=ctx,
    )
    ids = {q.id for q in qs}
    assert "life_before" not in ids
    assert "unseen_conditions" not in ids
    assert len(qs) <= 5
    clar2 = ParallelLifeClarifications(unchosen_path="不妊治療を諦めること")
    qs2 = generate_editorial_clarification_questions(
        FERTILITY_TEXT, "ja", clarifications=clar2
    )
    # Naming the unchosen path is not the same as answering what it holds now.
    assert "meaning_of_unchosen_life" in {q.id for q in qs2}


def test_multi_branch_extraction_fertility_case():
    clar = ParallelLifeClarifications(
        chosen_path="妻と息子と三人で暮らす人生",
        unchosen_path="不妊治療を諦めること",
    )
    structure = extract_editorial_branch_structure(
        FERTILITY_TEXT, clar, EditorialContext(), ja=True
    )
    assert "不妊" in structure.primary_branch or "治療" in structure.primary_branch
    assert structure.realized_outcome
    assert "息子" in (structure.realized_outcome or "") or "三人" in (
        structure.realized_outcome or ""
    )
    assert structure.secondary_branches
    assert any("二人目" in s for s in structure.secondary_branches)
    assert structure.present_question
    assert any(
        k in structure.present_question
        for k in ("家族", "記憶", "支え", "連続", "責任")
    )


def test_realized_outcome_and_secondary_branch():
    structure = extract_editorial_branch_structure(
        FERTILITY_TEXT,
        ParallelLifeClarifications(chosen_path="妻と息子と三人で暮らす人生"),
        EditorialContext(),
        ja=True,
    )
    assert "三人" in (structure.realized_outcome or "") or "息子" in (
        structure.realized_outcome or ""
    )
    assert any("二人目" in s for s in structure.secondary_branches)


def test_factual_polarity_protection_in_editorial(monkeypatch):
    patch_editorial_essay(monkeypatch, UNIVERSITY_ESSAY_JA)
    text = (
        "第一志望の早稲田大学第一文学部に受かった。"
        "実際に選んだのは進学することだった。"
        "選ばなかった道は進学を諦めることだった。"
    )
    result = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=text,
                clarifications=ParallelLifeClarifications(
                    chosen_path="早稲田大学へ進学する",
                    unchosen_path="進学を諦める",
                ),
                language="ja",
            )
        )
    ).result
    blob = result.branch_point + result.chosen_path + result.title
    assert "落ち" not in blob
    assert "不合格" not in blob


def test_current_life_context_appears_in_residue_and_rebranch(monkeypatch):
    patch_editorial_essay(monkeypatch)
    ctx = EditorialContext(
        current_life_context="妻と息子との暮らし、家族の記録を残したい",
        present_influence="家族の時間を最優先するようになった",
    )
    resp = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY_TEXT,
                clarifications=ParallelLifeClarifications(
                    chosen_path="妻と息子と三人で暮らす人生",
                    unchosen_path="不妊治療を諦めること",
                ),
                editorial_context=ctx,
                language="ja",
            )
        )
    )
    assert "家族" in resp.result.residue or "記録" in resp.result.residue
    joined = " ".join(resp.result.rebranch)
    assert "家族" in joined or "記憶" in joined or "記録" in joined


def test_observatory_lenses_selected_after_interpretation(monkeypatch):
    patch_editorial_essay(monkeypatch)
    resp = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY_TEXT,
                clarifications=ParallelLifeClarifications(
                    chosen_path="妻と息子と三人で暮らす人生",
                ),
                language="ja",
            )
        )
    )
    ids = [layer.id for layer in resp.result.observatory_layers]
    assert 3 <= len(ids) <= 4
    assert len(ids) == len(set(ids))
    assert any(i in ids for i in ("intimacy", "body", "book", "protocol-publishing"))


def test_title_generated_after_full_result_is_literary_not_age_only(monkeypatch):
    patch_editorial_essay(monkeypatch)
    resp = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY_TEXT,
                clarifications=ParallelLifeClarifications(
                    chosen_path="妻と息子と三人で暮らす人生",
                ),
                language="ja",
            )
        )
    )
    assert resp.result.title
    assert "残らなかった" not in resp.result.title
    assert "創作" not in resp.result.title
    assert _CJK.search(resp.result.title)


def test_japanese_editorial_has_no_english_fallback_prose(monkeypatch):
    patch_editorial_essay(monkeypatch)
    resp = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY_TEXT,
                clarifications=ParallelLifeClarifications(
                    chosen_path="妻と息子と三人で暮らす人生",
                ),
                language="ja",
            )
        )
    )
    r = resp.result
    prose = "".join(
        [
            r.title,
            r.subtitle,
            r.branch_point,
            r.chosen_path,
            r.unchosen_life,
            r.residue,
            r.cross_lens_synthesis,
            r.closing,
            *r.lost,
            *r.protected,
            *r.rebranch,
            *(layer.body for layer in r.observatory_layers),
        ]
    )
    banned = {"What", "The", "This", "Branch", "Chosen", "Protected", "Residue"}
    found = set(_EN_WORD.findall(prose)) & banned
    assert not found, found


def test_detect_orphan_fragments_flags_broken_suffix():
    result = ParallelLifeResult(
        title="三人になった45歳",
        subtitle="副題",
        branch_point="分岐。",
        chosen_path="選んだ道。",
        unchosen_life="選ばなかった道。",
        lost=["失ったもの"],
        protected=["守られたもの"],
        residue="不。残った問い。",
        observatory_layers=[],
        cross_lens_synthesis="合成。",
        rebranch=["問い"],
        closing="結び。",
        generation_mode="llm",
        language="ja",
        depth="editorial",
    )
    orphans = detect_orphan_fragments(result)
    assert any("不" in o for o in orphans)


def test_fact_validate_rejects_creativity_title_on_fertility():
    req = ParallelLifeEditorialRequest(
        source_text=FERTILITY_TEXT,
        clarifications=ParallelLifeClarifications(
            chosen_path="妻と息子と三人で暮らす人生",
            unchosen_path="不妊治療を諦めること",
        ),
        language="ja",
    )
    grounded = extract_grounded_primary_branch(
        req.source_text, req.clarifications, req.editorial_context, ja=True
    )
    bad = ParallelLifeResult(
        title="創作に残らなかった45歳",
        subtitle="副題",
        branch_point="不妊治療を経て子どもを授かった。",
        chosen_path="妻と息子と三人。",
        unchosen_life="治療を諦める。",
        lost=["a", "b"],
        protected=["c", "d"],
        residue="家族の問い。",
        observatory_layers=[],
        cross_lens_synthesis="合成。",
        rebranch=["e", "f"],
        closing="結び。",
        generation_mode="llm",
        language="ja",
        depth="editorial",
    )
    issues = fact_validate_editorial(bad, req, grounded, ja=True)
    assert any("title_creativity" in i or "creativity" in i for i in issues)


def test_markdown_export_labels_editorial():
    result = _heuristic_parallel_life(
        ParallelLifeRequest(source_text=FERTILITY_TEXT, language="ja", depth="standard")
    )
    editorial = result.model_copy(update={"depth": "editorial"})
    md = export_parallel_life_markdown(editorial, "2026-08-06")
    assert "編集版" in md


def test_generate_parallel_life_deep_aliases_to_editorial(monkeypatch):
    patch_editorial_essay(monkeypatch)
    result = asyncio.run(
        generate_parallel_life(
            ParallelLifeRequest(
                source_text=FERTILITY_TEXT,
                language="ja",
                depth="deep",
                clarifications=ParallelLifeClarifications(
                    chosen_path="妻と息子と三人で暮らす人生",
                ),
            )
        )
    )
    assert result.depth == "editorial"
    assert result.generation_mode == "llm"


def test_editorial_clarify_endpoint():
    client = _client()
    r = client.post(
        "/experience/parallel-life/editorial/clarify",
        json={
            "source_text": FERTILITY_TEXT,
            "language": "ja",
            "clarifications": {"chosen_path": "妻と息子と三人で暮らす人生"},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert 0 < len(data["questions"]) <= 5


def test_editorial_generate_endpoint_requires_llm(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = _client()
    r = client.post(
        "/experience/parallel-life/editorial",
        json={
            "source_text": FERTILITY_TEXT,
            "language": "ja",
            "clarifications": {
                "chosen_path": "妻と息子と三人で暮らす人生",
                "unchosen_path": "不妊治療を諦めること",
            },
            "editorial_context": {
                "current_life_context": "妻と息子との暮らし",
            },
        },
    )
    assert r.status_code == 503
    assert "LLM" in r.json()["detail"] or "編集版" in r.json()["detail"]


def test_editorial_generate_endpoint_with_mock(monkeypatch):
    patch_editorial_essay(monkeypatch, FERTILITY_ESSAY_JA)
    client = _client()
    r = client.post(
        "/experience/parallel-life/editorial",
        json={
            "source_text": FERTILITY_TEXT,
            "language": "ja",
            "clarifications": {
                "chosen_path": "妻と息子と三人で暮らす人生",
                "unchosen_path": "不妊治療を諦めること",
            },
            "editorial_context": {
                "current_life_context": "妻と息子との暮らし",
            },
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "branch_structure" in data
    assert data["result"]["depth"] == "editorial"
    assert data["result"]["generation_mode"] == "llm"
    assert data["branch_structure"]["secondary_branches"]
    assert data["branch_structure"]["realized_outcome"]
    assert "不。" not in data["result"]["residue"]


def test_generate_editorial_essay_no_heuristic_fallback(monkeypatch):
    """Even if generation fails, never silently return heuristic prose."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def _boom(*_a, **_k):
        raise RuntimeError("model down")

    monkeypatch.setattr("app.parallel_life_editorial_essay._chat_json", _boom)
    with pytest.raises(Exception) as excinfo:
        asyncio.run(
            generate_editorial_essay(
                ParallelLifeEditorialRequest(
                    source_text=FERTILITY_TEXT,
                    language="ja",
                )
            )
        )
    assert "heuristic" not in str(excinfo.value).lower()
