"""v1.1.1-exp Relevant Context Selection + Meaning Compression."""

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
from app.parallel_life_deep_reading.context_selection import (
    CALL_1_PROMPT_VERSION_V111,
    CALL_1_PROMPT_VERSION_V116,
    MAX_MANUSCRIPT_LOGIC_IDS,
    apply_selection_compression_gates,
    compute_resume_density,
    default_selection_from_pack,
    filter_grounded_pack_facts_for_draft,
    normalize_relevant_context_selection,
    selected_pack_corpus_text,
    thesis_soft_gate,
)
from app.parallel_life_deep_reading.models import (
    BranchStructure,
    Call1Result,
    Call1Validation,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    MeaningCompression,
    PrimaryBranch,
    RelevantContextSelection,
    ContextRelevanceClassification,
)
from app.parallel_life_deep_reading.prompts import (
    CALL_1_VERSION,
    call1_system_prompt,
    call1_system_prompt_v11,
)


def _ntt_pack() -> ContextPack:
    items = [
        ("career_history", "NTT東日本で勤務した"),
        ("career_history", "外資系半導体企業へ転職した"),
        ("career_history", "その後、複数業界・企業を経験した"),
        ("current_work", "現在は自分の会社を経営している"),
        ("current_projects", "現在、複数の観測・Protocol・文章制作を行っている"),
        ("career_history", "詳細な技術スタック履歴A"),
        ("career_history", "詳細な技術スタック履歴B"),
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
    pack = ContextPack(
        pack_id="pack_test_ntt",
        mode_intent=DeepReadingMode.contextual,
        approved_by_user=True,
        items=pack_items,
    )
    return approve_context_pack(pack)


def test_prod_prompt_untouched():
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert "meaning_compression" not in call1_system_prompt()
    # Active Contextual pin is v1.1.0-rc1; older pins remain historical A/B labels.
    assert CALL_1_PROMPT_VERSION_V11 == "parallel-life-call-1-v1.1.9"
    assert CALL_1_PROMPT_VERSION_V111 == "parallel-life-call-1-v1.1.1"
    assert "meaning_compression" in call1_system_prompt_v11()
    assert "Observatory-Core" in call1_system_prompt_v11()
    assert RUNTIME_VERSION_V11_EXP == "parallel-life-runtime-v1.1.11"


def test_selection_caps_at_five():
    pack = _ntt_pack()
    sel = default_selection_from_pack(pack)
    assert len(sel.manuscript_logic_ids) <= MAX_MANUSCRIPT_LOGIC_IDS
    assert len(sel.classifications) == len(pack.items)
    assert set(sel.withheld_ids).isdisjoint(set(sel.manuscript_logic_ids))


def test_normalize_trims_over_cap():
    pack = _ntt_pack()
    raw = RelevantContextSelection(
        manuscript_logic_ids=[i.id for i in pack.items],
        selected_ids=[i.id for i in pack.items],
        classifications=[
            ContextRelevanceClassification(id=i.id, relevance="essential", reason="x")
            for i in pack.items
        ],
    )
    norm = normalize_relevant_context_selection(raw, pack)
    assert len(norm.manuscript_logic_ids) <= 5
    assert len(norm.withheld_ids) >= 2


def test_resume_density_flags_enumeration():
    text = (
        "NTT東日本、外資系半導体、複数業界、Protocolプロジェクト、観測サイト。"
        "その後転職した。その後経験した。その後経営している。"
    )
    report = compute_resume_density(text)
    assert report.resume_density >= 6
    assert report.compression_required


def test_thesis_soft_gate_rejects_success_narrative():
    sel = RelevantContextSelection(manuscript_logic_ids=["pack_a"])
    mc = MeaningCompression(tension="制度内 vs 制度外", central_question="残るか")
    thesis, notes = thesis_soft_gate(
        CentralThesis(statement="転職のおかげで現在の成功を得た。"),
        selection=sel,
        compression=mc,
        branch_support_ids=["fact1"],
    )
    assert thesis.validation_status.startswith("failed_")
    assert any("success" in n for n in notes)


def test_draft_filters_withheld_pack_facts():
    pack = _ntt_pack()
    sel = default_selection_from_pack(pack)
    facts = [
        GroundedFact(
            id="fact_001",
            content="NTTを離れた",
            boundary_type=FactBoundaryType.explicit_fact,
        )
    ]
    for item in pack.items:
        facts.append(
            GroundedFact(
                id=item.id,
                content=item.content,
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                tags=["context_pack"],
            )
        )
    grounded = GroundedInput(facts=facts)
    filtered = filter_grounded_pack_facts_for_draft(grounded, sel)
    pack_ids = {f.id for f in filtered.facts if f.source_field == "context_pack"}
    assert pack_ids == set(sel.manuscript_logic_ids)
    assert "fact_001" in {f.id for f in filtered.facts}
    corpus = selected_pack_corpus_text(pack, sel)
    for wid in sel.withheld_ids:
        withheld_content = next(i.content for i in pack.items if i.id == wid)
        # withheld fine-detail lines should not appear in selected corpus
        if "技術スタック" in withheld_content:
            assert withheld_content not in corpus


def test_apply_selection_compression_gates(monkeypatch):
    monkeypatch.setenv("DEEP_READING_CONTEXT_PACK_ENABLED", "true")
    pack = _ntt_pack()
    call1 = Call1Result(
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="fact_001",
                    content="28歳でNTTを離れる道を選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                )
            ],
            current_context=["いまは自分の会社を経営している"],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="28歳",
                triggering_event="NTTに残るか外資へ",
                realized_path="外資へ",
                unrealized_paths=["NTT残留"],
                supporting_fact_ids=["fact_001"],
            )
        ),
        central_thesis=CentralThesis(
            statement="組織内で測る人生から、組織を越えて定義し直す人生へ移った分岐として読み直せる",
            supported_by=["fact_001"],
        ),
        meaning_compression=MeaningCompression(
            past_structure="一企業内部で役割を積み上げる",
            alternative_structure="NTTに残る人生",
            present_structure="自分で仕事を定義する",
            tension="制度内の蓄積 vs 持ち運ぶ蓄積",
            central_question="あのとき残っていたら",
            support_ids=["fact_001"],
        ),
        validation=Call1Validation(),
        status=GenerationStatus.ready_for_user_confirmation,
    )
    gated, diag = apply_selection_compression_gates(call1, pack=pack)
    assert gated.relevant_context_selection.manuscript_logic_ids
    assert len(gated.relevant_context_selection.manuscript_logic_ids) <= 5
    assert diag["prompt_pin"] == CALL_1_PROMPT_VERSION_V11
    assert CALL_1_PROMPT_VERSION_V111 == "parallel-life-call-1-v1.1.1"
    assert gated.resume_density_report is not None
