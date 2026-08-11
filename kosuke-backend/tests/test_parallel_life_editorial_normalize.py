"""Tests for Editorial Edition normalization, dedupe, and raw-reuse guards."""

from __future__ import annotations

import asyncio

from app.models import (
    EditorialContext,
    ParallelLifeClarifications,
    ParallelLifeEditorialRequest,
)
from app.parallel_life_editorial import (
    extract_editorial_branch_structure,
    generate_editorial_parallel_life,
)
from app.parallel_life_editorial_normalize import (
    assert_no_long_raw_reuse,
    dedupe_units,
    find_raw_reuse,
    is_near_duplicate,
    normalize_editorial_context,
    normalize_for_compare,
)

FERTILITY = """45歳のとき、不妊治療を経て子どもを授かった。
実際に選んだのは、妻と息子と三人で暮らす人生だった。
選ばなかった道は、不妊治療を諦めることだった。
今も、二人目を持っていたらどうだったかと考えることがある。"""

PRESENT_RAW = (
    "現在は、息子、嫁、との三人家族。仕事は自分の会社を経営している。"
    "広めのアパート（自己所有）に住んでいる。"
)
EMOTION_RAW = (
    "息子は可愛いし、子供の友達が家に遊びにくるし、楽しいですね。家庭という感じがします。"
)


def test_exact_and_near_duplicate_japanese_merge():
    units = [
        "現在は妻と息子との三人家族",
        "現在は、息子、嫁、との三人家族",
        "妻と息子と三人で暮らしている",
        "自分の会社を経営している",
        "会社経営をしている",
        "自社を運営している",
    ]
    merged = dedupe_units(units)
    # Family variants collapse; business variants collapse
    family = [u for u in merged if "三人" in normalize_for_compare(u) or "家族" in u]
    business = [u for u in merged if "経営" in u or "自社" in normalize_for_compare(u)]
    assert len(family) <= 2
    assert len(business) <= 2
    assert is_near_duplicate(
        "現在は妻と息子との三人家族",
        "現在は、息子、嫁、との三人家族",
    )


def test_normalize_stores_present_facts_once():
    clar = ParallelLifeClarifications(
        chosen_path="妻と息子と三人で暮らす人生",
        unchosen_path="不妊治療を諦めること",
    )
    ctx = EditorialContext(
        current_life_context=PRESENT_RAW + EMOTION_RAW,
        present_influence=PRESENT_RAW,  # intentional duplicate across fields
    )
    structure = extract_editorial_branch_structure(FERTILITY, clar, ctx, ja=True)
    normalized = normalize_editorial_context(FERTILITY, clar, ctx, structure, ja=True)

    # Compact facts — not three copies of the same paragraph
    joined = " ".join(normalized.present_life_facts + normalized.current_roles + normalized.current_conditions)
    assert joined.count("三人") <= 2
    assert joined.count(PRESENT_RAW) == 0
    assert "family_of_three" in normalized.signals
    assert "self_employed" in normalized.signals
    assert "owned_housing" in normalized.signals
    assert "child_friends_visit" in normalized.signals


def test_editorial_output_does_not_copy_raw_present_context(monkeypatch):
    """Essay path must not paste prep answers verbatim (model prompt + fact lock)."""
    from tests.editorial_essay_fixtures import patch_editorial_essay

    patch_editorial_essay(monkeypatch)
    clar = ParallelLifeClarifications(
        chosen_path="妻と息子と三人で暮らす人生",
        unchosen_path="不妊治療を諦めること",
    )
    ctx = EditorialContext(current_life_context=PRESENT_RAW + "\n" + EMOTION_RAW)
    resp = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY,
                clarifications=clar,
                editorial_context=ctx,
                language="ja",
            )
        )
    )
    r = resp.result
    prose = "".join(
        [
            r.branch_point,
            r.chosen_path,
            r.unchosen_life,
            r.residue,
            r.closing,
            r.cross_lens_synthesis,
            *r.lost,
            *r.protected,
            *r.rebranch,
            *(layer.body for layer in r.observatory_layers),
        ]
    )
    assert PRESENT_RAW not in prose
    assert EMOTION_RAW not in prose
    assert "楽しいですね" not in prose
    assert "家庭という感じがします" not in prose
    assert prose.count("自己所有") == 0
    assert prose.count("広めのアパート") == 0
    assert r.generation_mode == "llm"

    structure = extract_editorial_branch_structure(FERTILITY, clar, ctx, ja=True)
    normalized = normalize_editorial_context(FERTILITY, clar, ctx, structure, ja=True)
    leaks = assert_no_long_raw_reuse(r, normalized, ja=True)
    assert leaks == []


def test_structure_current_life_context_has_no_raw_paragraph():
    clar = ParallelLifeClarifications(chosen_path="妻と息子と三人で暮らす人生")
    ctx = EditorialContext(current_life_context=PRESENT_RAW)
    structure = extract_editorial_branch_structure(FERTILITY, clar, ctx, ja=True)
    assert PRESENT_RAW not in structure.current_life_context
    for item in structure.current_life_context:
        assert len(item) < 40 or "。" not in item


def test_find_raw_reuse_detects_long_japanese_copy():
    corpus = [EMOTION_RAW]
    copied = "前置き。" + EMOTION_RAW + "あと。"
    leaks = find_raw_reuse(copied, corpus, ja=True)
    assert leaks
    clean = "息子の友人たちが家を訪れることで、住まいは開かれた場所になっている。"
    assert find_raw_reuse(clean, corpus, ja=True) == []


def test_second_editorial_answers_replace_not_multiply():
    """Simulates regenerating with an edited answer — facts stay single."""
    clar = ParallelLifeClarifications(chosen_path="妻と息子と三人で暮らす人生")
    ctx1 = EditorialContext(current_life_context=PRESENT_RAW)
    ctx2 = EditorialContext(
        current_life_context="妻と息子の三人暮らし。自社を経営し、持ち家に住んでいる。"
    )
    structure = extract_editorial_branch_structure(FERTILITY, clar, ctx2, ja=True)
    n1 = normalize_editorial_context(FERTILITY, clar, ctx1, structure, ja=True)
    n2 = normalize_editorial_context(FERTILITY, clar, ctx2, structure, ja=True)
    # Second answer replaces meaning — still one family / one work / one housing fact
    assert len([f for f in n2.present_life_facts if "三人" in f or "家族" in f]) <= 1
    assert "self_employed" in n2.signals
    assert len(n2.present_life_facts) <= len(n1.present_life_facts) + 2
