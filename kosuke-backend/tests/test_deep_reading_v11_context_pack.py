"""v1.1-exp Context Pack: schema, mode resolution, pack inject, residue/lens allowlist."""

from __future__ import annotations

import os

from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
    ContextPack,
    ContextPackCategory,
    ContextPackItem,
    ContextPackItemSource,
    DeepReadingMode,
    approve_context_pack,
    inject_pack_into_grounded,
    pack_to_grounded_facts,
    resolve_effective_mode,
    seed_context_pack_from_text,
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
    ObservatoryLensCandidate,
    ObservatoryLensSelection,
    PrimaryBranch,
    ResidueCandidate,
    ResidueCandidates,
)
from app.parallel_life_deep_reading.prompts import (
    CALL_1_VERSION,
    call1_system_prompt,
    call1_system_prompt_v11,
)
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    filter_selected_lenses,
    validate_residue_candidate,
    _present_life_fact_ids,
    _past_branch_fact_ids,
)


NTT_BRANCH = """28歳のとき、NTTに残るか、外資へ移るかを選ぶ分岐があった。
実際に選んだ道はNTTを離れ、外資系企業へ移ること。
選ばなかった道は、一企業の内部で役割を積み上げ続けること。
いまは自分の会社を経営している。"""

NTT_PACK_TEXT = """NTTで働いていた。
その後、外資系企業で働いた。
現在は自分の会社を経営している。
観測所プロジェクトを進めている。
Protocol Publishing に関わっている。"""


def _approved_ntt_pack() -> ContextPack:
    pack = seed_context_pack_from_text(NTT_PACK_TEXT, source="imported_paste")
    items = []
    for item in pack.items:
        items.append(item.model_copy(update={"approved": True}))
    pack = pack.model_copy(update={"items": items})
    return approve_context_pack(pack)


def test_prod_call1_prompt_untouched():
    assert CALL_1_VERSION == "parallel-life-call-1-v1.0.3"
    assert "Context Pack" not in call1_system_prompt()
    assert CALL_1_PROMPT_VERSION_V11 == "parallel-life-call-1-v1.1.9"
    assert CALL_1_PROMPT_VERSION_V11 in call1_system_prompt_v11()
    assert "Context Pack" in call1_system_prompt_v11()
    assert "Observatory-Core" in call1_system_prompt_v11()
    assert "Section Contracts" in call1_system_prompt_v11()
    assert "BranchSemantics" in call1_system_prompt_v11()


def test_flag_off_forces_strict(monkeypatch):
    monkeypatch.delenv("DEEP_READING_CONTEXT_PACK_ENABLED", raising=False)
    pack = _approved_ntt_pack()
    assert (
        resolve_effective_mode(requested_mode="contextual", pack=pack) == DeepReadingMode.strict
    )


def test_flag_on_contextual_with_approved_facts(monkeypatch):
    monkeypatch.setenv("DEEP_READING_CONTEXT_PACK_ENABLED", "true")
    pack = _approved_ntt_pack()
    assert (
        resolve_effective_mode(requested_mode="contextual", pack=pack)
        == DeepReadingMode.contextual
    )
    unapproved = pack.model_copy(update={"approved_by_user": False})
    assert (
        resolve_effective_mode(requested_mode="contextual", pack=unapproved)
        == DeepReadingMode.strict
    )


def test_seed_never_auto_approves():
    pack = seed_context_pack_from_text(NTT_PACK_TEXT)
    assert pack.approved_by_user is False
    assert all(not i.approved for i in pack.items)
    assert len(pack.items) >= 3


def test_pack_facts_source_field_and_ids():
    pack = _approved_ntt_pack()
    facts = pack_to_grounded_facts(pack)
    assert facts
    assert all(f.source_field == "context_pack" for f in facts)
    assert all(f.id.startswith("pack_") for f in facts)
    assert all("context_pack" in f.tags for f in facts)


def test_inject_does_not_overwrite_branch_facts():
    pack = _approved_ntt_pack()
    grounded = GroundedInput(
        facts=[
            GroundedFact(
                id="fact_001",
                content="NTTを離れた",
                boundary_type=FactBoundaryType.explicit_fact,
            )
        ],
        current_context=["いまは自分の会社を経営している。"],
    )
    merged = inject_pack_into_grounded(grounded, pack)
    assert merged.facts[0].id == "fact_001"
    assert any(f.id.startswith("pack_") for f in merged.facts)
    assert len(merged.current_context) >= 1


def test_residue_present_anchors_include_pack(monkeypatch):
    monkeypatch.setenv("DEEP_READING_CONTEXT_PACK_ENABLED", "true")
    pack = _approved_ntt_pack()
    grounded = inject_pack_into_grounded(
        GroundedInput(
            facts=[
                GroundedFact(
                    id="fact_001",
                    content="28歳のときNTTを離れる道を選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                )
            ],
            current_context=[],
        ),
        pack,
    )
    present = set(_present_life_fact_ids(grounded))
    past = set(
        _past_branch_fact_ids(
            grounded,
            BranchStructure(
                primary_branch=PrimaryBranch(
                    period="28歳",
                    triggering_event="NTTに残るか外資へ移るか",
                    realized_path="外資へ移った",
                    unrealized_paths=["NTTに残る"],
                    supporting_fact_ids=["fact_001"],
                )
            ),
        )
    )
    pack_present = {
        f.id
        for f in grounded.facts
        if f.source_field == "context_pack"
        and any(
            t in (f.tags or [])
            for t in (
                "category:current_work",
                "category:current_projects",
            )
        )
    }
    pack_past = {
        f.id
        for f in grounded.facts
        if f.source_field == "context_pack"
        and "category:career_history" in (f.tags or [])
    }
    assert pack_present & present
    assert pack_past & past

    cand = ResidueCandidate(
        residue_statement="企業内部で積み上げる道を離れた経験は、現在の経営と並べて読むことができる",
        past_anchor_ids=["fact_001"],
        present_anchor_ids=[next(iter(pack_present))],
        support_ids=["fact_001", next(iter(pack_present))],
        inference_distance="near",
        advances_manuscript=True,
    )
    ok, reason = validate_residue_candidate(cand, grounded, sensitive=False)
    assert ok is not None, reason


def test_lens_allowlist_accepts_pack_ids(monkeypatch):
    monkeypatch.setenv("DEEP_READING_CONTEXT_PACK_ENABLED", "true")
    pack = _approved_ntt_pack()
    grounded = inject_pack_into_grounded(GroundedInput(facts=[]), pack)
    pack_id = next(f.id for f in grounded.facts if f.id.startswith("pack_"))
    allowed = {f.id for f in grounded.facts}
    evaluated, selected = filter_selected_lenses(
        [
            ObservatoryLensCandidate(
                lens_id="protocol_publishing",
                explicit_evidence_ids=[pack_id],
                residue_evidence_ids=["res_001"],
                new_meaning_added="出版という制度的枠組みから分岐を読む",
            ),
            ObservatoryLensCandidate(
                lens_id="bogus",
                explicit_evidence_ids=["not_a_real_id"],
                residue_evidence_ids=["res_001"],
                new_meaning_added="意味",
            ),
        ],
        allowed_explicit_ids=allowed,
    )
    assert any(c.lens_id == "protocol_publishing" and c.evidence_gate_passed for c in selected)
    assert any(c.lens_id == "bogus" and not c.evidence_gate_passed for c in evaluated)


def test_runtime_gates_contextual_injects_and_usage(monkeypatch):
    monkeypatch.setenv("DEEP_READING_CONTEXT_PACK_ENABLED", "true")
    pack = _approved_ntt_pack()
    call1 = Call1Result(
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="fact_001",
                    content="28歳のときNTTを離れる道を選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="triggering_event",
                )
            ],
            current_context=["いまは自分の会社を経営している。"],
            questions=[
                GroundedFact(
                    id="q1",
                    content="あのとき残っていたらどうなっていたか",
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="28歳",
                triggering_event="NTTに残るか外資へ移るか",
                realized_path="外資へ移った",
                unrealized_paths=["一企業の内部で役割を積み上げ続ける"],
                supporting_fact_ids=["fact_001"],
            )
        ),
        central_thesis=CentralThesis(statement="制度の内側から外へ移る選択"),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement="企業内部の道を離れた経験は、いまの経営と並べて読むことができる",
                    past_anchor_ids=["fact_001"],
                    present_anchor_ids=["ctx_001"],
                    support_ids=["fact_001", "ctx_001"],
                    inference_distance="near",
                    advances_manuscript=True,
                )
            ]
        ),
        selected_observatory_lenses=ObservatoryLensSelection(evaluated=[], selected=[]),
        validation=Call1Validation(),
        status=GenerationStatus.ready_for_user_confirmation,
    )
    gated = apply_call1_runtime_gates(
        call1,
        source_text=NTT_BRANCH,
        input_corpus=NTT_BRANCH,
        context_pack=pack,
        deep_reading_mode="contextual",
    )
    assert any(f.source_field == "context_pack" for f in gated.grounded_input.facts)
    assert gated.context_pack_usage is not None
    assert gated.context_pack_usage["mode"] == "contextual"
    assert any(f"runtime:{RUNTIME_VERSION_V11_EXP}" in n for n in gated.validation.notes)


def test_runtime_gates_strict_ignores_pack(monkeypatch):
    monkeypatch.setenv("DEEP_READING_CONTEXT_PACK_ENABLED", "true")
    pack = _approved_ntt_pack()
    call1 = Call1Result(
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="fact_001",
                    content="28歳のときNTTを離れる道を選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                )
            ],
            current_context=["いまは自分の会社を経営している。"],
            questions=[
                GroundedFact(
                    id="q1",
                    content="あのとき残っていたらどうなっていたか",
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="28歳",
                triggering_event="NTT分岐",
                realized_path="外資へ",
                unrealized_paths=["NTT残留"],
                supporting_fact_ids=["fact_001"],
            )
        ),
        central_thesis=CentralThesis(statement=""),
        residue_candidates=ResidueCandidates(items=[]),
        validation=Call1Validation(),
        status=GenerationStatus.ready_for_user_confirmation,
    )
    gated = apply_call1_runtime_gates(
        call1,
        source_text=NTT_BRANCH,
        input_corpus=NTT_BRANCH,
        context_pack=pack,
        deep_reading_mode="strict",
    )
    assert not any(f.source_field == "context_pack" for f in gated.grounded_input.facts)
    assert gated.context_pack_usage is None
