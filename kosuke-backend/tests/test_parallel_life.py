"""Tests for the Parallel Life generation engine (pure heuristic paths).

These target the heuristic fallback directly (no OpenAI key, no vector DB) so
they run fast and deterministically, and confirm the experience degrades
gracefully and stays single-language when no LLM is configured (product spec
§44).
"""

import asyncio
import re

import pytest

from app.models import ParallelLifeClarifications, ParallelLifeRequest
from app.observatory_lenses import (
    OBSERVATORY_LENS_IDS,
    OBSERVATORY_LENSES,
    is_valid_lens_id,
    select_observatory_lenses,
    validate_lens_ids,
)
from app.parallel_life_engine import (
    _cross_lens_synthesis,
    _dedupe_semantically,
    _heuristic_parallel_life,
    _is_valid_english_title,
    _is_valid_japanese_title,
    _lost_and_protected,
    _match_topic,
    _rebranch_items,
    _target_count,
    _title_and_subtitle,
    _validate_cross_lens_synthesis_quality,
    _validate_no_leakage_or_truncation,
    _validate_rebranch_items,
    export_parallel_life_markdown,
    generate_clarification_questions,
    generate_parallel_life,
)
from app.parallel_life_lens import get_parallel_life_lens_config

CJK = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
ASCII_LETTERS = re.compile(r"[A-Za-z]")

# Forbidden deterministic / unsafe language that must never appear.
FORBIDDEN_JA = [
    "絶対に", "必ず幸せ", "診断します", "運命", "宿命",
]
FORBIDDEN_EN = [
    "would have married", "definitely happier", "you always avoid",
    "diagnos", "destiny", "everything happens for a reason", "no regrets",
    "your true self", "the life you were meant to live",
]


def _has_cjk(text: str) -> bool:
    return bool(CJK.search(text or ""))


@pytest.fixture(autouse=True)
def _no_openai(monkeypatch):
    """Force heuristic fallback by removing any configured API key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _req(text: str, language: str = "ja", depth: str = "standard", **clar) -> ParallelLifeRequest:
    return ParallelLifeRequest(
        source_text=text,
        clarifications=ParallelLifeClarifications(**clar),
        language=language,
        depth=depth,
    )


JA_TEXT = "20歳のとき、彼氏と別れて、就職のために田舎へ帰った。あのまま東京に残っていたら、結婚していたのかなと思うことがある。"
EN_TEXT = "At twenty, I ended a relationship and returned to my hometown for work. Sometimes I wonder whether we might have married if I had stayed in Tokyo."


def _all_text(result) -> str:
    parts = [
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
        *(layer.title + " " + layer.body for layer in result.observatory_layers),
    ]
    return " ".join(parts)


# --- 1/4/5/6/9/10: structural validity (standard + deep) ---


def test_heuristic_standard_output_is_structurally_valid():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja", "standard"))
    assert result.title.strip()
    assert result.subtitle.strip()
    assert result.branch_point.strip()
    assert result.chosen_path.strip()
    assert result.unchosen_life.strip()
    assert 3 <= len(result.lost) <= 6
    assert 3 <= len(result.protected) <= 6
    assert result.residue.strip()
    assert 2 <= len(result.observatory_layers) <= 4
    assert result.cross_lens_synthesis.strip()
    assert 3 <= len(result.rebranch) <= 6
    assert result.closing.strip()
    assert result.generation_mode == "heuristic"
    assert result.depth == "standard"


def test_heuristic_deep_output_is_structurally_valid():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja", "deep"))
    assert result.depth == "deep"
    assert 2 <= len(result.observatory_layers) <= 4
    assert 3 <= len(result.rebranch) <= 6
    assert result.cross_lens_synthesis.strip()


# --- 7/8: Observatory Layer count and duplicates ---


def test_observatory_layer_count_never_exceeds_four_and_has_no_duplicates():
    for depth in ("standard", "deep"):
        for text in (JA_TEXT, EN_TEXT):
            result = _heuristic_parallel_life(_req(text, "ja" if _has_cjk(text) else "en", depth))
            ids = [layer.id for layer in result.observatory_layers]
            assert len(ids) <= 4
            assert len(ids) == len(set(ids))
            assert all(is_valid_lens_id(i) for i in ids)


# --- 2/3/18: language consistency ---


def test_japanese_mode_has_no_english_fallback_leakage():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    text = _all_text(result)
    for forbidden in FORBIDDEN_EN:
        assert forbidden.lower() not in text.lower()
    # Every major section should contain Japanese.
    for section in (
        result.title,
        result.branch_point,
        result.chosen_path,
        result.unchosen_life,
        result.residue,
        result.cross_lens_synthesis,
        result.closing,
    ):
        assert _has_cjk(section), f"Expected Japanese, got: {section!r}"


def test_english_mode_has_no_japanese_static_templates():
    result = _heuristic_parallel_life(_req(EN_TEXT, "en"))
    assert result.language == "en"
    for section in (
        result.title,
        result.branch_point,
        result.chosen_path,
        result.unchosen_life,
        result.residue,
        result.cross_lens_synthesis,
        result.closing,
    ):
        assert not _has_cjk(section), f"Unexpected Japanese in English output: {section!r}"
        assert ASCII_LETTERS.search(section)


# --- 10/19: heuristic fallback works with no API key ---


def test_generate_parallel_life_falls_back_without_key():
    result = asyncio.run(generate_parallel_life(_req(JA_TEXT, "ja")))
    assert result.generation_mode == "heuristic"
    assert result.title.strip()


# --- 12: malformed LLM output falls back safely (simulated) ---


def test_malformed_llm_output_raises_and_caller_can_fall_back(monkeypatch):
    from app.parallel_life_engine import _parse_and_validate_llm_output

    request = _req(JA_TEXT, "ja")
    with pytest.raises(Exception):
        _parse_and_validate_llm_output("not json at all", request)

    with pytest.raises(Exception):
        _parse_and_validate_llm_output('{"title": "t"}', request)


# --- 13: no deterministic alternate-life claims ---


def test_unchosen_life_uses_hedged_language_not_deterministic_claims():
    for text, lang in ((JA_TEXT, "ja"), (EN_TEXT, "en")):
        result = _heuristic_parallel_life(_req(text, lang))
        combined = result.unchosen_life
        for forbidden in FORBIDDEN_JA + FORBIDDEN_EN:
            assert forbidden.lower() not in combined.lower()
        if lang == "ja":
            assert any(hedge in combined for hedge in ["かもしれない", "可能性", "分からない", "できない"])
        else:
            assert any(
                hedge in combined.lower()
                for hedge in ["may have", "might have", "cannot be known", "possible life"]
            )


# --- 14: no system prompt text leaks into output ---


def test_no_system_prompt_leakage():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    text = _all_text(result)
    for banned in ["system_prompt", "You are Parallel Life", "gpt-4o-mini", "OPENAI_API_KEY"]:
        assert banned not in text


# --- 16: clarification answers remain optional ---


def test_clarifications_are_optional_and_generation_still_succeeds():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    assert result.title.strip()
    clar = ParallelLifeClarifications()
    assert all(
        getattr(clar, f) is None
        for f in ("age", "chosen_path", "unchosen_path", "what_remains", "constraints", "lost", "protected")
    )


def test_clarifications_when_provided_are_incorporated():
    result = _heuristic_parallel_life(
        _req(
            JA_TEXT,
            "ja",
            lost="友人たちとの距離",
            protected="家族との時間",
        )
    )
    assert "友人たちとの距離" in result.lost
    assert "家族との時間" in result.protected


# --- 17: unsupported lens ids are rejected ---


def test_unsupported_lens_ids_are_rejected():
    assert not is_valid_lens_id("not-a-real-lens")
    validated = validate_lens_ids(["book", "not-a-real-lens", "book", "market-signals", "also-fake"])
    assert validated == ["book", "market-signals"]


def test_select_observatory_lenses_bounds():
    for depth in ("standard", "deep"):
        selected = select_observatory_lenses(JA_TEXT, "", depth)
        assert 2 <= len(selected) <= 4
        assert len(selected) == len(set(selected))
        assert all(lid in OBSERVATORY_LENS_IDS for lid in selected)


# --- 11: lens availability is true after activation ---


def test_parallel_life_lens_is_available():
    config = get_parallel_life_lens_config()
    assert config.available is True
    assert config.id == "parallel-life"
    assert "standard" in config.supported_depths
    assert "editorial" in config.supported_depths
    assert len(config.observatory_lenses) == len(OBSERVATORY_LENS_IDS)


# --- 15: Markdown export contains all sections ---


def test_markdown_export_contains_all_sections():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    md = export_parallel_life_markdown(result, "2026-08-06")
    assert result.title in md
    assert "分岐点" in md
    assert "選んだ人生" in md
    assert "選ばなかった人生" in md
    assert "失ったもの" in md
    assert "守られたもの" in md
    assert "今に残っているもの" in md
    assert "社会との接続" in md
    assert "レンズを重ねると見えること" in md
    assert "これからの小さな再分岐" in md
    assert "結び" in md
    for item in result.lost:
        assert item in md
    for layer in result.observatory_layers:
        assert layer.title in md
    # No technical/debug leakage.
    for banned in ["gpt-4o-mini", "OPENAI_API_KEY", "fluke_score", "embedding"]:
        assert banned not in md


def test_markdown_export_english():
    result = _heuristic_parallel_life(_req(EN_TEXT, "en"))
    md = export_parallel_life_markdown(result, "2026-08-06")
    assert "Branch Point" in md
    assert "Chosen Path" in md
    assert "Unchosen Life" in md
    assert "Lost" in md
    assert "Protected" in md
    assert "Observatory Layer" in md


# --- 20: no private technical data in the public response ---


def test_result_schema_has_no_internal_technical_fields():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    field_names = set(type(result).model_fields.keys())
    for banned_field in ("embedding", "vector", "fluke_score", "prompt", "model_name", "chroma"):
        assert banned_field not in field_names


# --- Clarification questions ---


def test_clarification_questions_are_optional_and_bounded():
    questions = asyncio.run(generate_clarification_questions(JA_TEXT, "ja"))
    assert 0 <= len(questions) <= 4
    for q in questions:
        assert q.question.strip()
        assert _has_cjk(q.question)


def test_clarification_questions_skip_age_when_already_present():
    text_with_age = "25歳のとき、会社を辞める機会があったが、残ることにした。"
    questions = asyncio.run(generate_clarification_questions(text_with_age, "ja"))
    ids = [q.id for q in questions]
    assert "age" not in ids


def test_clarification_questions_english():
    questions = asyncio.run(generate_clarification_questions(EN_TEXT, "en"))
    for q in questions:
        assert not _has_cjk(q.question)


def test_clarification_questions_never_ask_for_identifying_info():
    questions = asyncio.run(generate_clarification_questions(JA_TEXT, "ja"))
    banned_terms = ["本名", "住所", "会社名", "病名", "full name", "address", "employer"]
    for q in questions:
        for term in banned_terms:
            assert term not in q.question


# =============================================================================
# Editorial quality pass: title validation, source-text leakage, truncation,
# Observatory Lens display names, and cross-lens synthesis.
# =============================================================================


# --- 1: malformed English title prevention -----------------------------------


def test_valid_english_titles_pass_validation():
    good_titles = [
        "The Path Not Chosen at Twenty-Four",
        "The Year I Chose Another Path",
        "The City I Did Not Return To",
        "The Work I Did Not Leave",
        "The Life That Remained Possible",
        "The Job Not Chosen at 24",
        "Leaving Tokyo at 24",
        "The Relationship Left Behind",
    ]
    for title in good_titles:
        assert _is_valid_english_title(title), f"Expected valid: {title!r}"


def test_malformed_english_titles_are_rejected():
    bad_titles = [
        "The that branch Not Chosen at 24",  # the exact reported bug
        "The this path Not Chosen",
        "The life not chose",
        "The branch did not chosen",
        "The The Path Not Chosen",  # duplicated identical word
        "",
        "Path",  # too short (< 3 words)
        "the path not chosen at twenty four and also many more words here today",  # too long
        'The "Path Not Chosen',  # unbalanced quote
        "The Path Not Chosen....",  # truncation marker
        "The Path Not Chosen…",
        "The {kw} Not Chosen",  # unfilled template placeholder
        "the path not chosen",  # not title case (first word lowercase)
    ]
    for title in bad_titles:
        assert not _is_valid_english_title(title), f"Expected invalid: {title!r}"


def test_heuristic_titles_are_always_valid_english_or_japanese():
    # A source text that matches no topic keyword — this is exactly the shape
    # of input that produced "The that branch Not Chosen at 24" before the
    # fix (default topic fallback + an age clarification).
    texts_en = [
        "Something happened when I was twenty four and I made a decision.",
        "At twenty, I ended a relationship and returned to my hometown for work.",
        "I quit writing novels in my twenties and became an office worker.",
    ]
    for text in texts_en:
        for age in (None, "24", "32"):
            result = _heuristic_parallel_life(
                ParallelLifeRequest(
                    source_text=text,
                    clarifications=ParallelLifeClarifications(age=age),
                    language="en",
                    depth="standard",
                )
            )
            assert _is_valid_english_title(result.title), f"Invalid title: {result.title!r}"

    texts_ja = [JA_TEXT, "20代で小説を書くのをやめて、会社員になった。"]
    for text in texts_ja:
        for age in (None, "24", "32"):
            result = _heuristic_parallel_life(
                ParallelLifeRequest(
                    source_text=text,
                    clarifications=ParallelLifeClarifications(age=age),
                    language="ja",
                    depth="standard",
                )
            )
            assert _is_valid_japanese_title(result.title), f"Invalid title: {result.title!r}"


def test_title_never_has_duplicated_adjacent_determiners():
    determiners = {"the", "a", "an", "that", "this", "these", "those"}
    for text in (
        "Something happened when I was twenty four and I made a decision.",
        EN_TEXT,
        "I quit writing novels in my twenties and became an office worker.",
    ):
        for age in (None, "24"):
            result = _heuristic_parallel_life(
                ParallelLifeRequest(
                    source_text=text,
                    clarifications=ParallelLifeClarifications(age=age),
                    language="en",
                )
            )
            words = [w.lower().strip(".,") for w in result.title.split()]
            for a, b in zip(words, words[1:]):
                assert not (a in determiners and b in determiners), result.title


def test_title_and_subtitle_no_topic_produces_grammatical_fallback():
    # Directly exercise the default ("no keyword matched") topic branch that
    # caused the original bug.
    topic = _match_topic("nothing matches any keyword here", ja=False)
    for age in (None, "24"):
        for seed in range(12):
            title, _subtitle = _title_and_subtitle(topic, age, ja=False, seed=seed)
            assert _is_valid_english_title(title), title


# --- 2/3: source-text meta-language and truncation ----------------------------

_META_LANGUAGE_PHRASES_EN = [
    "the branch appears inside",
    "the user wrote",
    "the input says",
    "this sentence suggests",
    "in the source text",
    "the user's statement is",
]
_META_LANGUAGE_PHRASES_JA = [
    "という入力の中には",
    "入力の中には",
    "ユーザーが書いた",
    "本文には",
]


def test_heuristic_output_never_describes_the_source_as_text():
    for text, lang in ((JA_TEXT, "ja"), (EN_TEXT, "en")):
        for depth in ("standard", "deep"):
            result = _heuristic_parallel_life(_req(text, lang, depth))
            text_blob = _all_text(result).lower()
            phrases = _META_LANGUAGE_PHRASES_JA if lang == "ja" else _META_LANGUAGE_PHRASES_EN
            for phrase in phrases:
                assert phrase.lower() not in text_blob, f"Found meta-language {phrase!r}"


def test_heuristic_output_never_quotes_raw_input_verbatim():
    long_input = (
        "I failed to get into my first-choice university and went to a different one instead, "
        "and I still wonder what would have happened."
    )
    result = _heuristic_parallel_life(_req(long_input, "en"))
    # None of the long, distinctive phrases from the raw input should be
    # quoted back verbatim inside quotation marks in the public document.
    assert '"i failed to get into my first-choice university' not in _all_text(result).lower()
    assert "went...." not in _all_text(result)


def test_no_mid_word_truncation_or_repeated_period_ellipsis():
    for text, lang in ((JA_TEXT, "ja"), (EN_TEXT, "en")):
        for depth in ("standard", "deep"):
            result = _heuristic_parallel_life(_req(text, lang, depth))
            blob = _all_text(result)
            assert "…" not in blob, blob
            assert "..." not in blob, blob
            assert ".." not in blob.replace("...", ""), blob


def test_validate_no_leakage_or_truncation_catches_meta_language():
    with pytest.raises(ValueError):
        _validate_no_leakage_or_truncation(
            ['The branch appears inside "I failed my first-choice university and went...."'],
            ja=False,
        )
    with pytest.raises(ValueError):
        _validate_no_leakage_or_truncation(
            ["「第一志望に落ちた」という入力の中には、分岐があります。"], ja=True
        )


def test_validate_no_leakage_or_truncation_catches_truncation_markers():
    with pytest.raises(ValueError):
        _validate_no_leakage_or_truncation(["It happened when I went...."], ja=False)
    with pytest.raises(ValueError):
        _validate_no_leakage_or_truncation(["そのまま帰った…"], ja=True)


def test_validate_no_leakage_or_truncation_allows_clean_text():
    _validate_no_leakage_or_truncation(
        ["At that age, a university rejection redirected the path into work and place."],
        ja=False,
    )
    _validate_no_leakage_or_truncation(
        ["第一志望に届かなかったことが、その後の進学や仕事を静かに変えていった。"], ja=True
    )


# --- 10: official Observatory Lens display names ------------------------------


def test_observatory_layer_title_is_always_the_official_english_name():
    for text, lang in ((JA_TEXT, "ja"), (EN_TEXT, "en")):
        result = _heuristic_parallel_life(_req(text, lang, "deep"))
        for layer in result.observatory_layers:
            assert layer.title == OBSERVATORY_LENSES[layer.id].name_en
            # Never a literal, inconsistent translation/transliteration.
            assert layer.title not in ("市場のシグナル", "プロトコル・パブリッシング", "書物")


def test_observatory_layer_descriptor_present_and_in_response_language():
    ja_result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    for layer in ja_result.observatory_layers:
        assert layer.descriptor.strip()
        assert _has_cjk(layer.descriptor)

    en_result = _heuristic_parallel_life(_req(EN_TEXT, "en"))
    for layer in en_result.observatory_layers:
        assert layer.descriptor.strip()
        assert not _has_cjk(layer.descriptor)


def test_all_lens_definitions_use_consistent_official_naming():
    for lens in OBSERVATORY_LENSES.values():
        assert lens.name_ja == lens.name_en, lens.id
        assert lens.descriptor_en.strip()
        assert lens.descriptor_ja.strip()


# --- 12: Cross-Lens Synthesis adds a conclusion, not just a lens list --------


def test_cross_lens_synthesis_adds_content_beyond_a_lens_list():
    topic = _match_topic(EN_TEXT, ja=False)
    lens_ids = ["intimacy", "city"]
    seen = set()
    for seed in range(6):
        synthesis = _cross_lens_synthesis(topic, lens_ids, seed, ja=False)
        # More than just "Intimacy, City" plus a single generic sentence.
        assert len(synthesis) > 220
        seen.add(synthesis)
    # Varying the seed should vary the concluding observation.
    assert len(seen) > 1


# --- 13: Closing varies and never repeats the same line every time ----------


def test_closing_varies_across_results():
    closings = set()
    for text in (EN_TEXT, "I moved to Tokyo instead of staying home.", "I left my job to raise a child."):
        result = _heuristic_parallel_life(_req(text, "en"))
        closings.add(result.closing)
    assert len(closings) > 1


# --- 16: "結び" in Japanese Markdown export, "Closing" in English -----------


def test_markdown_export_uses_japanese_closing_heading():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    md = export_parallel_life_markdown(result, "2026-08-06")
    assert "## 結び" in md
    assert "## Closing" not in md


def test_markdown_export_uses_english_closing_heading():
    result = _heuristic_parallel_life(_req(EN_TEXT, "en"))
    md = export_parallel_life_markdown(result, "2026-08-06")
    assert "## Closing" in md


def test_markdown_export_includes_lens_descriptor():
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja"))
    md = export_parallel_life_markdown(result, "2026-08-06")
    for layer in result.observatory_layers:
        assert layer.title in md
        if layer.descriptor:
            assert layer.descriptor in md


# --- 12 (LLM safety net): malformed title / leakage triggers a retry --------


def test_llm_output_with_malformed_title_is_rejected():
    from app.parallel_life_engine import _parse_and_validate_llm_output

    request = _req(EN_TEXT, "en")
    payload = {
        "title": "The that branch Not Chosen at 24",
        "subtitle": "s",
        "branch_point": "b",
        "chosen_path": "c",
        "unchosen_life": "u",
        "lost": ["a", "b", "c"],
        "protected": ["a", "b", "c"],
        "residue": "r",
        "observatory_layers": [
            {"id": "book", "title": "Book", "body": "body text"},
            {"id": "work", "title": "Work", "body": "body text"},
        ],
        "cross_lens_synthesis": "s",
        "rebranch": ["a", "b", "c"],
        "closing": "c",
    }
    import json as _json

    with pytest.raises(Exception):
        _parse_and_validate_llm_output(_json.dumps(payload), request)


# =============================================================================
# Editorial quality pass, round 2: Lost/Protected deduplication, Cross-Lens
# Synthesis prose, Re-branch concreteness, and Observatory Lens visibility.
# =============================================================================


# --- 1: Lost / Protected semantic deduplication --------------------------


def test_dedupe_semantically_collapses_keep_options_cluster_ja():
    items = _dedupe_semantically(
        ["選択肢を残しておけること", "将来の可能性を残せること", "次の道を選べる余地"], ja=True
    )
    assert len(items) == 1


def test_dedupe_semantically_collapses_life_base_cluster_ja():
    items = _dedupe_semantically(
        ["自分の生活を成立させること", "生活の基盤", "安定した暮らし"], ja=True
    )
    assert len(items) == 1


def test_dedupe_semantically_collapses_clusters_en():
    items = _dedupe_semantically(
        [
            "the ability to keep future options open",
            "keep choosing for oneself",
            "a foundation for daily life",
            "stable footing",
        ],
        ja=False,
    )
    # Two clusters ("keep_options", "life_base"), so at most 2 items survive.
    assert len(items) <= 2


def test_dedupe_semantically_keeps_unrelated_items():
    items = _dedupe_semantically(
        ["身軽に動き続けられるという感覚", "家族や既存の人間関係との連続性"], ja=True
    )
    assert len(items) == 2


def test_heuristic_lost_and_protected_have_no_duplicate_concepts():
    for text, lang in ((JA_TEXT, "ja"), (EN_TEXT, "en")):
        for depth in ("standard", "deep"):
            result = _heuristic_parallel_life(_req(text, lang, depth))
            assert result.lost == _dedupe_semantically(result.lost, lang == "ja")
            assert result.protected == _dedupe_semantically(result.protected, lang == "ja")


def test_lost_and_protected_item_counts_follow_depth_guidelines():
    # Standard: 3-4 items; Deep: 4-5 items (max-oriented guideline).
    for seed in range(20):
        assert 3 <= _target_count("standard", seed) <= 4
        assert 4 <= _target_count("deep", seed) <= 5


def test_lost_and_protected_counts_are_not_forced_equal():
    # Across many seeds, Lost and Protected should sometimes differ in
    # length — they must not be mechanically mirrored 1:1.
    from app.models import ParallelLifeClarifications

    saw_unequal = False
    for seed in range(30):
        lost, protected = _lost_and_protected("東京", ParallelLifeClarifications(), True, seed, "standard")
        if len(lost) != len(protected):
            saw_unequal = True
            break
    assert saw_unequal


def test_lost_and_protected_are_not_mechanically_mirrored_pairs():
    # Lost and Protected pools must not be simple parallel opposites at the
    # same index (e.g. always "freedom" vs "stability" at position 0).
    for seed in range(10):
        lost, protected = _heuristic_parallel_life(
            _req(EN_TEXT, "en", "standard")
        ).lost, _heuristic_parallel_life(_req(EN_TEXT, "en", "standard")).protected
        assert lost != protected


def test_lost_and_protected_are_category_specific():
    """Education must not inherit place-oriented wording; creativity must not
    inherit belonging-to-a-place items (editorial-quality pass round 2)."""
    education = "第一志望の大学に落ちて、別の大学へ進んだ。今でも、あの大学に行っていたらと思うことがある。"
    creativity = "20代で小説を書くのをやめて、会社員になった。生活は安定したが、あのまま書いていたらどうなったのかと思う。"
    place = "29歳のとき、海外で生活する機会があったが、日本に残った。今でも、あのとき海外を選んでいたらと思うことがある。"

    edu = _heuristic_parallel_life(_req(education, "ja"))
    cre = _heuristic_parallel_life(_req(creativity, "ja"))
    pla = _heuristic_parallel_life(_req(place, "ja"))

    # Education Lost should talk about school/subject/peers, not "別の土地で生活".
    assert not any("別の土地" in item for item in edu.lost)
    assert any(
        any(k in item for k in ("進学", "科目", "分野", "友人", "キャンパス", "進路", "第一志望"))
        for item in edu.lost
    )
    # Creativity Lost should talk about practice/work, not place belonging.
    assert any(
        any(k in item for k in ("創作", "作品", "表現", "作"))
        for item in cre.lost
    )
    # Place Lost keeps overseas / movement wording.
    assert any(any(k in item for k in ("海外", "移動", "土地", "場所")) for item in pla.lost)

    # Protected for education is grounded in the path taken, not generic "keep choosing".
    assert any(
        any(k in item for k in ("学び", "経験", "人", "仕事", "進路", "立て直"))
        for item in edu.protected
    )


def test_lost_does_not_repeat_possibility_noun_excessively():
    education = "第一志望の大学に落ちて、別の大学へ進んだ。今でも、あの大学に行っていたらと思うことがある。"
    result = _heuristic_parallel_life(_req(education, "ja", "deep"))
    possibility_hits = sum(1 for item in result.lost if "可能性" in item)
    assert possibility_hits <= 2


def test_dedupe_semantically_collapses_overseas_possibility_cluster():
    items = _dedupe_semantically(
        [
            "海外へ進む可能性",
            "海外で暮らす可能性",
            "海外に居続ける選択肢",
            "別の土地で生きる未来",
        ],
        ja=True,
    )
    assert len(items) == 1


# --- 2: Cross-Lens Synthesis prose quality --------------------------------


def test_cross_lens_synthesis_does_not_open_with_lens_name_list():
    topic = _match_topic(EN_TEXT, ja=False)
    for seed in range(6):
        synthesis = _cross_lens_synthesis(topic, ["education-employment", "intimacy", "book"], seed, ja=False)
        # Must not open with "Education-Employment, Intimacy, and Book..." —
        # the domain phrase, not the lens brand name, carries the sentence.
        assert not synthesis.startswith("Education")
        assert not synthesis.lower().startswith("placed together")


def test_cross_lens_synthesis_avoids_rigid_fallback_phrases():
    topic_en = _match_topic(EN_TEXT, ja=False)
    topic_ja = _match_topic(JA_TEXT, ja=True)
    banned_en = (
        "placed together,",
        "institutional, market, place-based, and historical conditions intersected",
        "these lenses reveal",
    )
    banned_ja = (
        "制度・市場・場所・時代の条件が交差する場所で生まれていた",
        "個人的な経験でありながら、それは個人だけによってつくられたものではない",
        "ということが分かる",
        "が可視化される",
    )
    for seed in range(6):
        text_en = _cross_lens_synthesis(topic_en, ["intimacy", "city"], seed, ja=False).lower()
        for phrase in banned_en:
            assert phrase not in text_en
        text_ja = _cross_lens_synthesis(topic_ja, ["intimacy", "city"], seed, ja=True)
        for phrase in banned_ja:
            assert phrase not in text_ja


def test_cross_lens_synthesis_is_not_only_a_lens_name_list():
    topic = _match_topic(JA_TEXT, ja=True)
    lens_ids = ["education-employment", "intimacy", "book"]
    for seed in range(6):
        synthesis = _cross_lens_synthesis(topic, lens_ids, seed, ja=True)
        # Domain phrases carry the prose; branded lens names must not dominate.
        assert "Education–Employment" not in synthesis
        assert "Intimacy" not in synthesis or "親密" in synthesis
        assert len(synthesis) >= 100


def test_cross_lens_synthesis_length_scales_with_depth():
    topic = _match_topic(JA_TEXT, ja=True)
    standard = _cross_lens_synthesis(topic, ["intimacy", "city"], 0, ja=True, depth="standard")
    deep = _cross_lens_synthesis(topic, ["intimacy", "city"], 0, ja=True, depth="deep")
    assert len(deep) > len(standard)


def test_validate_cross_lens_synthesis_quality_rejects_rigid_phrases():
    with pytest.raises(ValueError):
        _validate_cross_lens_synthesis_quality(
            "Placed together, Intimacy and City show that institutional, market, place-based, "
            "and historical conditions intersected here.",
            ["Intimacy", "City"],
            ja=False,
        )
    with pytest.raises(ValueError):
        _validate_cross_lens_synthesis_quality(
            "Intimacy、Cityを重ねてみると、制度・市場・場所・時代の条件が交差する場所で生まれていた。",
            ["Intimacy", "City"],
            ja=True,
        )


def test_validate_cross_lens_synthesis_quality_rejects_lens_list_only():
    with pytest.raises(ValueError):
        _validate_cross_lens_synthesis_quality("Intimacy, City, and Work.", ["Intimacy", "City", "Work"], ja=False)


def test_validate_cross_lens_synthesis_quality_allows_natural_prose():
    _validate_cross_lens_synthesis_quality(
        "The timing of a first job, the cost of housing, and the shape of a close relationship "
        "all shaped this branch at once, more than any single choice did.",
        ["Intimacy", "City"],
        ja=False,
    )


# --- 3: Re-branch concreteness --------------------------------------------


def test_rebranch_items_are_branch_category_specific():
    education_items = set(_rebranch_items(0, "standard", ja=True, category="education"))
    work_items = set(_rebranch_items(0, "standard", ja=True, category="work"))
    relationship_items = set(_rebranch_items(0, "standard", ja=True, category="relationship"))
    place_items = set(_rebranch_items(0, "standard", ja=True, category="place"))
    creativity_items = set(_rebranch_items(0, "standard", ja=True, category="creativity"))
    care_items = set(_rebranch_items(0, "standard", ja=True, category="care"))
    all_sets = [education_items, work_items, relationship_items, place_items, creativity_items, care_items]
    for i, a in enumerate(all_sets):
        for b in all_sets[i + 1 :]:
            assert a.isdisjoint(b)


def test_rebranch_items_never_contain_abstract_quality_placeholder():
    for category in ("education", "work", "relationship", "place", "creativity", "care", "default"):
        for ja in (True, False):
            for seed in range(8):
                items = _rebranch_items(seed, "deep", ja=ja, category=category)
                for item in items:
                    assert "「質」を、ひとつだけ名づけ" not in item
                    assert "the quality" not in item.lower()


def test_rebranch_item_counts_follow_depth_guidelines():
    for seed in range(20):
        standard = _rebranch_items(seed, "standard", ja=True, category="default")
        deep = _rebranch_items(seed, "deep", ja=True, category="default")
        assert 3 <= len(standard) <= 4
        assert 4 <= len(deep) <= 5


def test_validate_rebranch_items_rejects_discouraged_actions():
    with pytest.raises(ValueError):
        _validate_rebranch_items(["元恋人に連絡してみる。"], ja=True)
    with pytest.raises(ValueError):
        _validate_rebranch_items(["Contact your ex and explain how you feel."], ja=False)
    with pytest.raises(ValueError):
        _validate_rebranch_items(["Quit your job this week to pursue the unchosen path."], ja=False)


def test_validate_rebranch_items_rejects_abstract_placeholder():
    with pytest.raises(ValueError):
        _validate_rebranch_items(
            ["選ばなかった道が象徴していた「質」を、ひとつだけ名づけてみる。"], ja=True
        )
    with pytest.raises(ValueError):
        _validate_rebranch_items(
            ["Name, just once, the quality that the unchosen path seemed to represent."], ja=False
        )


def test_validate_rebranch_items_allows_concrete_actions():
    _validate_rebranch_items(
        ["当時やめた創作を、今週30分だけ再開してみる。", "その場所の音楽を今週の生活に取り入れる。"],
        ja=True,
    )
    _validate_rebranch_items(
        ["Resume that creative practice for 30 minutes this week.", "Write two sentences comparing both paths."],
        ja=False,
    )


def test_heuristic_rebranch_reflects_branch_category():
    education_text = "第一志望の大学に落ちて、別の大学へ進んだ。今でも、あの大学に行っていたらと思うことがある。"
    result = _heuristic_parallel_life(_req(education_text, "ja"))
    assert any("大学" in item or "分野" in item or "科目" in item or "講座" in item for item in result.rebranch)

    creative_text = "20代で小説を書くのをやめて、会社員になった。生活は安定したが、あのまま書いていたらどうなったのかと思う。"
    result2 = _heuristic_parallel_life(_req(creative_text, "ja"))
    assert any("創作" in item or "作品" in item or "ノート" in item for item in result2.rebranch)


# --- 4: Observatory Lens heading visibility (frontend-adjacent, backend data) --


def test_observatory_layer_title_and_descriptor_are_distinguishable():
    # The backend contract the frontend heading styling relies on: title is
    # always the official English name, descriptor is a separate, shorter
    # field — never merged into a single string.
    result = _heuristic_parallel_life(_req(JA_TEXT, "ja", "deep"))
    for layer in result.observatory_layers:
        assert layer.title != layer.descriptor
        assert len(layer.title) < 40


def test_llm_output_with_source_text_meta_language_is_rejected():
    from app.parallel_life_engine import _parse_and_validate_llm_output

    request = _req(EN_TEXT, "en")
    payload = {
        "title": "The Path Not Chosen at Twenty-Four",
        "subtitle": "s",
        "branch_point": 'The branch appears inside "I ended a relationship and moved home."',
        "chosen_path": "c",
        "unchosen_life": "u",
        "lost": ["a", "b", "c"],
        "protected": ["a", "b", "c"],
        "residue": "r",
        "observatory_layers": [
            {"id": "book", "title": "Book", "body": "body text"},
            {"id": "work", "title": "Work", "body": "body text"},
        ],
        "cross_lens_synthesis": "s",
        "rebranch": ["a", "b", "c"],
        "closing": "c",
    }
    import json as _json

    with pytest.raises(Exception):
        _parse_and_validate_llm_output(_json.dumps(payload), request)
