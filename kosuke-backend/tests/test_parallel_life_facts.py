"""Factual grounding / polarity protection for Parallel Life."""

import pytest

from app.models import ParallelLifeClarifications, ParallelLifeRequest, ParallelLifeResult
from app.parallel_life_engine import _heuristic_parallel_life
from app.parallel_life_facts import (
    extract_parallel_life_facts,
    validate_factual_consistency,
)


def _req(text: str, language: str = "ja") -> ParallelLifeRequest:
    return ParallelLifeRequest(
        source_text=text,
        language=language,
        depth="standard",
        clarifications=ParallelLifeClarifications(),
    )


def _corpus(result: ParallelLifeResult) -> str:
    return "\n".join(
        [
            result.title,
            result.subtitle,
            result.branch_point,
            result.chosen_path,
            result.unchosen_life,
            result.residue,
            result.cross_lens_synthesis,
            result.closing,
            *result.lost,
            *result.protected,
            *result.rebranch,
            *(layer.body for layer in result.observatory_layers),
        ]
    )


# --- Extraction --------------------------------------------------------------


def test_extract_admission_to_waseda():
    text = "第一志望の早稲田大学第一文学部に受かった。"
    facts = extract_parallel_life_facts(text, ParallelLifeClarifications(), ja=True)
    assert facts.education_polarity == "admitted"
    assert any(i.text == "早稲田大学" for i in facts.institutions)
    assert any(i.text == "第一文学部" for i in facts.institutions)
    assert facts.chosen_path is not None
    assert facts.chosen_path.provenance == "explicit_user_input"


def test_extract_rejection():
    facts = extract_parallel_life_facts("第一志望に落ちた。", ParallelLifeClarifications(), ja=True)
    assert facts.education_polarity == "rejected"


def test_extract_place_work_marriage_polarities():
    assert extract_parallel_life_facts("東京に残った。", ParallelLifeClarifications(), ja=True).place_polarity == "stayed"
    assert extract_parallel_life_facts("東京を離れた。", ParallelLifeClarifications(), ja=True).place_polarity == "left"
    assert extract_parallel_life_facts("会社を辞めた。", ParallelLifeClarifications(), ja=True).work_polarity == "resigned"
    assert extract_parallel_life_facts("会社に残った。", ParallelLifeClarifications(), ja=True).work_polarity == "stayed"
    assert extract_parallel_life_facts("結婚した。", ParallelLifeClarifications(), ja=True).marriage_polarity == "married"
    assert (
        extract_parallel_life_facts("結婚しなかった。", ParallelLifeClarifications(), ja=True).marriage_polarity
        == "not_married"
    )


def test_inferred_never_overwrites_explicit_admission():
    facts = extract_parallel_life_facts(
        "第一志望の早稲田大学に受かった。",
        ParallelLifeClarifications(unchosen_path="別の大学"),
        ja=True,
    )
    assert facts.education_polarity == "admitted"
    assert facts.chosen_path is not None
    assert "早稲田" in facts.chosen_path.text or facts.chosen_path.text == "早稲田大学"


# --- Heuristic polarity integrity -------------------------------------------


def test_waseda_admission_is_not_narrated_as_rejection():
    text = "第一志望の早稲田大学第一文学部に受かった。"
    result = _heuristic_parallel_life(_req(text))
    corpus = _corpus(result)

    assert "落ちた" not in corpus
    assert "不合格" not in corpus
    assert "別の大学へ" not in corpus
    assert "別の大学に" not in corpus
    assert "進学先を離れ" not in corpus
    assert "戻らなかった" not in result.title
    assert "選ばなかった" not in result.title
    assert "あきらめる" not in result.chosen_path
    assert "合格" in result.branch_point or "受かった" in result.title or "進んだ" in result.title
    assert "早稲田" in result.title or "早稲田" in result.branch_point or "早稲田" in result.chosen_path


def test_rejection_is_not_narrated_as_admission():
    result = _heuristic_parallel_life(_req("第一志望に落ちた。"))
    corpus = _corpus(result)
    assert "受かった" not in corpus
    assert "合格した" not in corpus


def test_tokyo_stayed_is_not_narrated_as_left():
    result = _heuristic_parallel_life(_req("東京に残った。"))
    corpus = _corpus(result)
    assert "東京を離れた" not in corpus
    assert "残" in result.title or "選択" in result.title


def test_tokyo_left_is_not_narrated_as_stayed():
    result = _heuristic_parallel_life(_req("東京を離れた。"))
    # Title / chosen must not claim staying as the fact.
    assert "に残った道" not in result.title
    assert "残ることだった" not in result.chosen_path


def test_quit_job_is_not_narrated_as_stayed():
    result = _heuristic_parallel_life(_req("会社を辞めた。"))
    corpus = _corpus(result)
    assert "会社に残った" not in corpus
    assert "仕事を続けた" not in corpus


def test_stayed_at_company_is_not_narrated_as_quit():
    result = _heuristic_parallel_life(_req("会社に残った。"))
    corpus = _corpus(result)
    assert "退職した" not in corpus
    assert "戻らなかった仕事" not in corpus
    assert "続けなかった仕事" not in corpus
    assert "選ばなかった仕事" not in corpus


def test_married_is_not_narrated_as_not_married():
    result = _heuristic_parallel_life(_req("結婚した。"))
    corpus = _corpus(result)
    assert "結婚しなかった" not in corpus
    assert "戻らなかった恋愛" not in corpus


def test_not_married_is_not_narrated_as_married_choice():
    result = _heuristic_parallel_life(_req("結婚しなかった。"))
    assert "選んだ結婚" not in result.title


# --- Contradiction validator -------------------------------------------------


def test_validate_factual_consistency_rejects_admission_inversion():
    result = ParallelLifeResult(
        title="戻らなかった進学先",
        subtitle="s",
        branch_point="第一志望に落ちたことが分岐だった。",
        chosen_path="別の大学へ進んだ。",
        unchosen_life="u",
        lost=["a", "b", "c"],
        protected=["a", "b", "c"],
        residue="r",
        observatory_layers=[],
        cross_lens_synthesis="s",
        rebranch=["a", "b", "c"],
        closing="c",
        language="ja",
    )
    with pytest.raises(ValueError):
        validate_factual_consistency(
            "第一志望の早稲田大学第一文学部に受かった。",
            result,
            ja=True,
        )


def test_validate_factual_consistency_allows_admission_prose():
    result = ParallelLifeResult(
        title="受かったあとの早稲田大学",
        subtitle="s",
        branch_point="早稲田大学への合格は分岐でもあった。",
        chosen_path="進んだのは早稲田大学だった。",
        unchosen_life="進学しなかった側の道を選んでいたら違っていたかもしれない。",
        lost=["a", "b", "c"],
        protected=["第一志望への合格という事実", "b", "c"],
        residue="r",
        observatory_layers=[],
        cross_lens_synthesis="s",
        rebranch=["a", "b", "c"],
        closing="c",
        language="ja",
    )
    validate_factual_consistency(
        "第一志望の早稲田大学第一文学部に受かった。",
        result,
        ja=True,
    )


def test_english_admission_polarity():
    text = "I got accepted to my first-choice university."
    facts = extract_parallel_life_facts(text, ParallelLifeClarifications(), ja=False)
    assert facts.education_polarity == "admitted"
    result = _heuristic_parallel_life(_req(text, "en"))
    corpus = _corpus(result).lower()
    assert "rejected" not in corpus
    assert "did not get in" not in corpus
    assert "another university" not in corpus
