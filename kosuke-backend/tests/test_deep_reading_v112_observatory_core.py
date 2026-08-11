"""v1.1.2-exp Observatory-Core: pre-thesis lenses, evidence, CrossLensRelations."""

from __future__ import annotations

from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
    ContextPack,
    ContextPackCategory,
    ContextPackItem,
    ContextPackItemSource,
    DeepReadingMode,
    approve_context_pack,
)
from app.parallel_life_deep_reading.observatory_core import (
    CALL_1_PROMPT_VERSION_V112,
    RUNTIME_VERSION_V112_EXP,
    build_observatory_core_bundle,
    curated_evidence_store,
    detect_structures,
    relation_density_score,
    select_candidate_lenses,
    should_omit_observatory_section,
)
from app.parallel_life_deep_reading.prompts import (
    CALL_1_VERSION,
    call1_system_prompt,
    call1_system_prompt_v11,
    call1_user_prompt_v11,
)


NTT_BRANCH = (
    "28歳のとき、NTTに残るか、外資へ移るかを選ぶ分岐があった。"
    "実際に選んだ道はNTTを離れ、外資系企業へ移ること。"
    "選ばなかった道は、一企業の内部で役割を積み上げ続けること。"
    "いまは自分の会社を経営している。"
    "いまも「あのとき残っていたら」と考えることがある。"
)


def _ntt_pack() -> ContextPack:
    items = [
        ("career_history", "NTTで働いていた"),
        ("career_history", "外資系企業で働いた"),
        ("current_work", "現在は自分の会社を経営している"),
        ("current_projects", "観測所（Observatory）プロジェクトを進めている"),
        ("current_projects", "Protocol Publishing に関わっている"),
    ]
    pack_items = []
    for i, (cat, content) in enumerate(items):
        pack_items.append(
            ContextPackItem(
                id=f"pack_{cat}_{i+1:03d}",
                content=content,
                category=ContextPackCategory(cat),
                source=ContextPackItemSource.user_typed,
                confidence=1.0,
                approved=True,
                allowed_for_fact=True,
                chronology_rank=10 + i,
            )
        )
    return approve_context_pack(
        ContextPack(
            pack_id="pack_v112_ntt",
            mode_intent=DeepReadingMode.contextual,
            approved_by_user=True,
            items=pack_items,
        )
    )


def test_versions_and_strict_untouched():
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert "Observatory-Core" not in call1_system_prompt()
    # Active Contextual pin may advance; Observatory-Core rules remain in v11 prompt.
    assert "Observatory-Core" in call1_system_prompt_v11()
    assert CALL_1_PROMPT_VERSION_V112 == "parallel-life-call-1-v1.1.2-exp"
    assert RUNTIME_VERSION_V112_EXP == "parallel-life-runtime-v1.1.2-exp"
    assert "cross_lens_relations" in call1_user_prompt_v11(
        "x", {}, {}, {}, context_pack_approved_items=[], observatory_core_prefill={}
    )


def test_curated_store_grounded_and_compact():
    store = curated_evidence_store()
    assert len(store) >= 6
    for e in store:
        assert e.evidence_source
        assert e.structural_pattern
        assert len(e.structural_pattern) < 200
        assert e.lens_id in {
            "education-employment",
            "market-signals",
            "clean-society",
            "body",
            "after-success",
            "protocol-publishing",
        }
        assert "essay" not in e.structural_pattern.lower()


def test_ntt_structural_selection_not_promo():
    pack = _ntt_pack()
    structures = detect_structures(NTT_BRANCH, pack)
    assert "employment_regime_boundary" in structures
    sel = select_candidate_lenses(NTT_BRANCH, pack)
    ids = [c.lens_id for c in sel.candidates]
    assert "education-employment" in ids
    assert "protocol-publishing" not in ids  # pack project names must not select
    assert 1 <= len(ids) <= 4
    bundle = build_observatory_core_bundle(NTT_BRANCH, pack)
    assert bundle.retrieved_observatory_evidence
    assert len(bundle.retrieved_observatory_evidence) <= 6
    assert bundle.cross_lens_relations
    assert all(r.causality_status == "non_causal_parallel" for r in bundle.cross_lens_relations)
    assert "追いや" not in " ".join(r.interpretation for r in bundle.cross_lens_relations)
    assert relation_density_score(bundle.cross_lens_relations) >= 7
    assert should_omit_observatory_section(bundle.cross_lens_relations, 1) is True


def test_zero_lens_case_valid():
    bundle = build_observatory_core_bundle(
        "昨日、青いペンを買った。いまもその色が好きだ。",
        None,
    )
    assert bundle.candidate_lens_selection.candidates == []
    assert bundle.retrieved_observatory_evidence == []
    assert bundle.cross_lens_relations == []
    assert bundle.candidate_lens_selection.zero_lens_reason


def test_fertility_selects_body_not_forced_employment():
    text = (
        "不妊治療を続けるか止めるかの分岐があった。"
        "いまは妻と息子と三人で暮らしている。"
    )
    bundle = build_observatory_core_bundle(text, None)
    ids = [c.lens_id for c in bundle.candidate_lens_selection.candidates]
    assert "body" in ids
    assert "protocol-publishing" not in ids


def test_education_case_selects_education_employment():
    text = (
        "第一志望の大学に進学するか、別の学部に行くかの分岐があった。"
        "選んだ道は第一志望への進学。いまも別の選択を考えることがある。"
    )
    bundle = build_observatory_core_bundle(text, None)
    ids = [c.lens_id for c in bundle.candidate_lens_selection.candidates]
    assert "education-employment" in ids


def test_privacy_store_has_no_user_facts():
    for e in curated_evidence_store():
        assert "NTT" not in e.structural_pattern
        assert "ユーザー" not in e.structural_pattern
        assert e.allowed_for_interpretation is True
