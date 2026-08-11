"""Production Candidate v1.0.2 — residue contract + unsupported personal detail."""

from __future__ import annotations

from app.parallel_life_deep_reading.fixtures import (
    CASE1_SOURCE,
    CASE2_SOURCE,
    build_case1_call1,
    build_case2_call1,
)
from app.parallel_life_deep_reading.models import (
    FactBoundaryType,
    GroundedFact,
    GroundedInput,
    ResidueCandidate,
)
from app.parallel_life_deep_reading.runtime_validation import (
    detect_unsupported_personal_details,
    detect_unsupported_scenes,
    filter_call1_rebranch_directions,
    filter_residue_candidates,
    residue_centrality_passes,
    validate_residue_candidate,
)
from app.parallel_life_deep_reading.models import RebranchDirection


def test_residue_requires_past_and_present_anchors():
    call1 = build_case1_call1()
    grounded = call1.grounded_input
    bad = ResidueCandidate(
        residue_statement="いまも大切だ",
        past_anchor_ids=[],
        present_anchor_ids=[],
        advances_manuscript=True,
    )
    ok, reason = validate_residue_candidate(bad, grounded, sensitive=True)
    assert ok is None
    assert "past" in reason or "present" in reason or "generic" in reason


def test_user_question_alone_cannot_be_residue():
    call1 = build_case1_call1()
    q = call1.grounded_input.questions[0]
    bad = ResidueCandidate(
        residue_statement=q.content,
        past_anchor_ids=[q.id],
        present_anchor_ids=["fact_005"],
        advances_manuscript=True,
        inference_distance="near",
    )
    ok, reason = validate_residue_candidate(bad, call1.grounded_input, sensitive=True)
    assert ok is None
    assert "question" in reason


def test_user_question_cannot_be_present_anchor():
    call1 = build_case1_call1()
    q = call1.grounded_input.questions[0]
    bad = ResidueCandidate(
        residue_statement="過去の分岐のあとで現在の生活構造が続いており未接続が残っている",
        past_anchor_ids=["fact_003"],
        present_anchor_ids=[q.id],
        advances_manuscript=True,
        inference_distance="near",
    )
    ok, reason = validate_residue_candidate(bad, call1.grounded_input, sensitive=True)
    assert ok is None
    assert "present" in reason


def test_valid_current_context_residue_passes():
    call1 = build_case1_call1()
    items, notes = filter_residue_candidates(
        call1.residue_candidates.items,
        call1.grounded_input,
        call1.branch_structure,
        source_text=CASE1_SOURCE,
    )
    assert len(items) >= 1
    assert items[0].past_anchor_ids
    assert items[0].present_anchor_ids


def test_zero_valid_residue_without_present_anchors():
    grounded = GroundedInput(
        facts=[
            GroundedFact(
                id="f1",
                content="19歳で合格した",
                boundary_type=FactBoundaryType.explicit_fact,
            )
        ],
        questions=[
            GroundedFact(
                id="q1",
                content="別の大学ならどう変わったか",
                boundary_type=FactBoundaryType.user_question,
            )
        ],
        current_context=[],
    )
    call1 = build_case2_call1()
    call1 = call1.model_copy(update={"grounded_input": grounded})
    items, notes = filter_residue_candidates(
        [],
        grounded,
        call1.branch_structure,
        source_text=CASE2_SOURCE,
    )
    assert items == []
    assert any("no_valid_residue" in n or "anchor" in n for n in notes)


def test_campus_scene_rejected_when_not_supplied():
    grounded = build_case2_call1().grounded_input
    body = "キャンパスで新しい友人に囲まれ、毎日が刺激的だった。"
    details = detect_unsupported_personal_details(body, grounded)
    scenes = detect_unsupported_scenes(body, grounded)
    assert details or scenes
    assert any(
        d.detail_type == "campus_scene" for d in details
    ) or any(s.scene_type == "campus_scene" for s in scenes)


def test_club_seminar_job_duration_rejected():
    grounded = build_case2_call1().grounded_input
    samples = [
        ("club", "サークル活動で多くの仲間と過ごした。"),
        ("seminar", "ゼミでのディスカッションが自分を変えた。"),
        ("job_function", "マーケティングや営業の現場を渡り歩いた。"),
        ("duration_unsupplied", "治療を何年も続けた末に子どもを授かった。"),
    ]
    for detail_type, sentence in samples:
        found = detect_unsupported_personal_details(sentence, grounded)
        assert any(d.detail_type == detail_type for d in found), detail_type


def test_invented_conversation_rejected_without_evidence():
    grounded = build_case1_call1().grounded_input
    # Case1 has no 話し合い evidence
    body = "妻にそっと話しかけ、返事をした夜のことを覚えている。"
    found = detect_unsupported_personal_details(body, grounded)
    assert any(d.detail_type == "invented_conversation" for d in found)


def test_generic_rebranch_removed():
    kept = filter_call1_rebranch_directions(
        [
            RebranchDirection(
                id="g",
                source_meaning="成長",
                current_receiver="生活",
                branch_specific_form="小さく始める",
                support_ids=["fact_005"],
                genericity_score=0,
            )
        ],
        grounded=build_case1_call1().grounded_input,
    )
    assert kept == []


def test_specific_rebranch_kept():
    call1 = build_case1_call1()
    kept = filter_call1_rebranch_directions(
        [
            RebranchDirection(
                id="ok",
                source_meaning="家庭らしさ",
                current_receiver="息子の友人が家に遊びに来る現在",
                branch_specific_form="友人来訪が示す家庭らしさを一度だけ言葉にする",
                support_ids=["fact_005"],
                genericity_score=0,
            )
        ],
        grounded=call1.grounded_input,
    )
    assert len(kept) == 1


def test_residue_centrality_not_satisfied_by_question_only():
    call1 = build_case1_call1()
    residues = call1.residue_candidates.items
    body = call1.grounded_input.questions[0].content + "\n" + ("あ" * 250)
    assert residue_centrality_passes(body, residues, call1.grounded_input) is False


def test_residue_centrality_with_present_and_meaning():
    call1 = build_case1_call1()
    residues = call1.residue_candidates.items
    body = (
        "45歳で子どもを授かり、妻と息子と三人で暮らす道を選んだ。"
        "現在も会社を経営し、息子の友人が家に遊びに来る日常が続いている。"
        "そのあいだにまだ接続しきれていないものが残っている。"
        + ("いまの生活を静かに見直す。" * 20)
    )
    assert residue_centrality_passes(body, residues, call1.grounded_input) is True
