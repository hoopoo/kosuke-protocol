"""Primary-event lock and domain consistency tests."""

from __future__ import annotations

import asyncio

from app.models import (
    EditorialContext,
    ParallelLifeClarifications,
    ParallelLifeEditorialRequest,
    ParallelLifeRequest,
)
from app.parallel_life_domain import (
    classify_primary_domain,
    detect_child_polarity,
    domain_consistency_issues,
    extract_grounded_primary_branch,
)
from app.parallel_life_editorial import generate_editorial_parallel_life
from app.parallel_life_engine import _heuristic_parallel_life, _match_topic
from app.parallel_life_seed import seed_line_for_domain

FERTILITY = """45歳のとき、不妊治療を経て子どもを授かった。
実際に選んだのは、妻と息子と三人で暮らす人生だった。
選ばなかった道は、不妊治療を諦めることだった。
今も、二人目を持っていたらどうだったかと考えることがある。"""

CREATIVITY = """30歳のとき、小説を書くことをやめ、会社員として働く道を選んだ。
選ばなかった道は、創作を続けることだった。"""


def _fertility_clar() -> ParallelLifeClarifications:
    return ParallelLifeClarifications(
        age="45",
        chosen_path="妻と息子との三人家族で暮らす",
        unchosen_path="不妊治療を諦める",
    )


def test_primary_event_and_domain_for_fertility():
    grounded = extract_grounded_primary_branch(FERTILITY, _fertility_clar(), None, ja=True)
    assert grounded.primary_domain == "family-formation"
    assert "授かった" in grounded.primary_event or "不妊" in grounded.primary_event
    assert grounded.child_polarity == "had_child"
    assert any("二人目" in s for s in grounded.secondary_branches)
    assert "creativity" not in grounded.inferred_themes
    assert "創作" not in grounded.primary_event


def test_child_polarity_had_child():
    assert detect_child_polarity(FERTILITY, _fertility_clar(), ja=True) == "had_child"


def test_topic_match_family_outranks_creativity_even_if_both_present():
    # Contaminated blob must still lock to family when fertility facts exist
    contaminated = FERTILITY + "\n創作について考えることもある。"
    topic = _match_topic(contaminated, True)
    assert topic.category == "family_formation"


def test_standard_heuristic_family_title_not_rejection_or_creativity():
    result = _heuristic_parallel_life(
        ParallelLifeRequest(
            source_text=FERTILITY,
            clarifications=_fertility_clar(),
            language="ja",
            depth="standard",
        )
    )
    assert "創作" not in result.title
    assert "残らなかった" not in result.title
    assert "離れた" not in result.title
    assert "選ばなかった" not in result.title or "二人目" in result.title
    blob = result.title + result.branch_point + result.chosen_path + result.residue
    assert "家族" in blob or "息子" in blob or "授かった" in blob
    assert blob.count("創作") == 0


def test_editorial_fertility_regression_no_creativity_takeover(monkeypatch):
    from tests.editorial_essay_fixtures import patch_editorial_essay

    patch_editorial_essay(monkeypatch)
    ctx = EditorialContext(
        current_life_context=(
            "息子は可愛い。息子の友人が家に遊びに来る。家庭らしい楽しさを感じている。"
            "自分の会社を経営している。自己所有の広めの住まいで暮らしている。"
        )
    )
    resp = asyncio.run(
        generate_editorial_parallel_life(
            ParallelLifeEditorialRequest(
                source_text=FERTILITY,
                clarifications=_fertility_clar(),
                editorial_context=ctx,
                language="ja",
            )
        )
    )
    r = resp.result
    assert r.depth == "editorial"
    assert "創作" not in r.title
    assert "執筆" not in r.title
    prose = r.title + r.branch_point + r.chosen_path + r.unchosen_life + r.residue + r.closing
    assert "創作を続け" not in prose
    assert "作品をつく" not in prose
    assert "執筆" not in prose
    assert "息子" in prose or "三人" in prose or "家族" in prose
    assert "不妊" in resp.branch_structure.primary_branch or "授かった" in resp.branch_structure.primary_branch
    assert any("二人目" in s for s in resp.branch_structure.secondary_branches)


def test_creativity_case_stays_creativity():
    clar = ParallelLifeClarifications(
        chosen_path="会社員として働く",
        unchosen_path="創作を続ける",
    )
    domain, _ = classify_primary_domain(CREATIVITY, clar, None, ja=True)
    assert domain == "creativity"
    result = _heuristic_parallel_life(
        ParallelLifeRequest(source_text=CREATIVITY, clarifications=clar, language="ja")
    )
    assert "不妊" not in result.title
    assert "授かった" not in result.branch_point


def test_seed_corpus_filtered_for_family_domain():
    allowed = {
        "timing",
        "unchosen-path",
        "constraint",
        "continuity",
        "care",
        "possibility",
        "intimacy",
        "stability",
        "historical-conditions",
        "recovery-vs-reversal",
        "belonging",
        "work",
    }
    line = seed_line_for_domain("ja", "unrealized-creativity", 0, allowed_domains=allowed)
    assert "創作" not in line
    assert line  # falls back inside allowed set


def test_domain_consistency_rejects_creativity_title_on_family_result():
    from app.models import ParallelLifeResult

    grounded = extract_grounded_primary_branch(FERTILITY, _fertility_clar(), None, ja=True)
    bad = ParallelLifeResult(
        title="創作に残らなかった45歳",
        subtitle="x",
        branch_point="創作を続けるかどうか",
        chosen_path="執筆をやめた",
        unchosen_life="作品をつくる道",
        lost=["創作の時間"],
        protected=["安定"],
        residue="書く習慣が残った",
        observatory_layers=[],
        cross_lens_synthesis="創作について",
        rebranch=["小説を再開する"],
        closing="作品へ戻る",
        language="ja",
        depth="standard",
    )
    issues = domain_consistency_issues(bad, grounded, ja=True)
    assert any("title_creativity" in i or "creativity_dominates" in i for i in issues)


def test_education_does_not_become_fertility():
    text = "第一志望の早稲田大学第一文学部に受かった。実際に選んだのは進学することだった。"
    clar = ParallelLifeClarifications(chosen_path="早稲田大学へ進学する")
    domain, _ = classify_primary_domain(text, clar, None, ja=True)
    assert domain == "education"
