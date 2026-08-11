"""v1.1.10-exp deterministic realization — Observatory FN, labels, parser, clarification→draft."""

from __future__ import annotations

from app.parallel_life_deep_reading.branch_semantics import (
    CALL_1_PROMPT_VERSION_V1110,
    RUNTIME_VERSION_V1110_EXP,
)
from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
)
from app.parallel_life_deep_reading.models import (
    AdditionalQuestions,
    BranchStructure,
    Call1Result,
    Call1Validation,
    CentralThesis,
    DeepReadingConfirmRequest,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    MeaningCompression,
    PrimaryBranch,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.section_contracts import (
    LOCKED_PUBLIC_LABELS_JA,
    SectionContract,
    SectionContractSet,
    _observatory_realized,
    normalize_markdown_section_headings,
    parse_locked_sections,
    required_section_realization,
    restore_locked_section_manuscript,
)
from app.parallel_life_deep_reading.service import (
    MAX_CLARIFICATION_ROUNDS,
    DeepReadingService,
    _branch_structurally_sufficient,
)
from app.parallel_life_deep_reading.session_store import DeepReadingSessionStore


def test_pins_v1110():
    # Historical v1.1.10 pin kept; active Contextual pin is v1.1.0-rc1.
    assert CALL_1_PROMPT_VERSION_V11 == "parallel-life-call-1-v1.1.9"
    assert CALL_1_PROMPT_VERSION_V1110 == "parallel-life-call-1-v1.1.9-exp"
    assert RUNTIME_VERSION_V1110_EXP == "parallel-life-runtime-v1.1.10-exp"
    assert RUNTIME_VERSION_V11_EXP == "parallel-life-runtime-v1.1.11"


def test_observatory_realized_without_employment_keywords():
    family_body = (
        "個人の分岐の横に、似た条件で家庭とケアを抱えながら生きた人々の並びが薄く透けて見える。"
        "制度説明に還元しない身体経験として、問いが残る。"
    )
    claim = "個人の分岐の横に、似た条件で生きた人々の並びが薄く透けて見える"
    assert _observatory_realized(
        family_body,
        claim,
        variants=["ケア", "身体経験", "並びが薄く透けて"],
    )
    career_body = "長期雇用と企業間移動という社会の並びが透けて見える。"
    assert _observatory_realized(career_body, "長期雇用と企業間移動", variants=[])


def test_observatory_required_section_passes_non_career_prose():
    contracts = SectionContractSet(
        contracts=[
            SectionContract(
                section_id="observatory",
                structural_purpose="social parallel",
                required_meaning="似た条件の並び",
                interpretive_claim="個人の分岐の横に、似た条件で生きた人々の並びが薄く透けて見える",
                acceptable_semantic_variants=["ケア", "身体経験", "並置"],
                must_be_present=True,
                required_public_label="社会との接続",
                minimum_paragraphs=1,
            )
        ]
    )
    body = (
        "## 社会との接続\n\n"
        "似た条件でケアを抱えながら生きた人々の並びが透けて見える。"
        "制度説明に還元しない経験として問いが残る。\n"
    )
    ok, missing, _ = required_section_realization(body, contracts)
    assert ok, missing
    assert not any("observatory" in m for m in missing)


def test_zero_lens_observatory_not_required():
    contracts = SectionContractSet(
        contracts=[
            SectionContract(
                section_id="observatory",
                must_be_present=False,
                omission_allowed=True,
                omission_reason="zero_selected_observatory_lenses",
                required_public_label="社会との接続",
            )
        ]
    )
    ok, missing, details = required_section_realization("## 分岐点\n\n分かれ目。\n", contracts)
    assert ok, missing
    assert details["observatory"]["omission_reason"] == "zero_selected_observatory_lenses"


def test_normalize_inline_and_period_headings():
    messy = (
        "序文です ## 失ったもの。本文A\n"
        "##守られたもの\n本文B\n"
        "## 残されたもの\n本文C\n"
    )
    fixed = normalize_markdown_section_headings(messy)
    assert "## 失ったもの" in fixed
    assert "## 守られたもの" in fixed
    assert re_search_locked_heading(fixed, "守られたもの")
    parsed = parse_locked_sections(fixed)
    assert "失ったもの" in parsed
    assert "守られたもの" in parsed


def re_search_locked_heading(body: str, label: str) -> bool:
    import re

    return bool(re.search(rf"(?m)^##\s*{re.escape(label)}\s*$", body))


def test_restore_locked_labels_and_education_meaning():
    fallback = "\n".join(
        f"## {lab}\n\n"
        + (
            "教育の分岐で残った構造と測り方が、いまも問いとして残る。"
            if lab == "今に残った構造"
            else f"{lab}の解釈的核心。"
        )
        + "\n"
        for lab in LOCKED_PUBLIC_LABELS_JA
        if lab != "社会との接続"
    )
    edited = (
        "## 分岐点\n\n短い。\n\n"
        "## 残されたもの\n\n別名だけ。\n\n"
        "## 今に残る問い\n\n圧縮された。\n"
    )
    contracts = SectionContractSet(
        contracts=[
            SectionContract(
                section_id="protected",
                must_be_present=True,
                required_public_label="守られたもの",
                interpretive_claim="守られたものの解釈的核心",
                minimum_paragraphs=1,
            ),
            SectionContract(
                section_id="residue",
                must_be_present=True,
                required_public_label="今に残った構造",
                interpretive_claim="教育の分岐で残った構造と測り方が、いまも問いとして残る",
                minimum_paragraphs=1,
            ),
        ]
    )
    restored = restore_locked_section_manuscript(
        edited, fallback_body=fallback, contracts=contracts
    )
    assert "## 守られたもの" in restored
    assert "## 残されたもの" not in restored
    assert "## 今に残った構造" in restored
    assert "教育の分岐で残った構造" in restored


def test_branch_structurally_sufficient_helper():
    call1 = Call1Result(
        status=GenerationStatus.needs_additional_input,
        prompt_version=CALL_1_PROMPT_VERSION_V1110,
        schema_version=RUNTIME_VERSION_V1110_EXP,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="大学進学を選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                )
            ],
            questions=[],
            current_context=["いまも創作を続けている"],
            confirmed_by_user=False,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="過去",
                triggering_event="進路選択",
                realized_path="進学した",
                unrealized_paths=["就職した"],
                supporting_fact_ids=["f1"],
            )
        ),
        central_thesis=CentralThesis(
            statement="進路の分岐をいま読み直せる。",
            supported_by=["f1"],
            validation_status="passed",
        ),
        meaning_compression=MeaningCompression(),
        validation=Call1Validation(notes=[], branch_concreteness_ok=True),
        additional_questions=AdditionalQuestions(required=True, questions=["詳しく"]),
    )
    assert _branch_structurally_sufficient(call1)
    assert MAX_CLARIFICATION_ROUNDS == 2


def test_clarification_soft_exit_reaches_ready_for_draft(monkeypatch):
    """After max-round soft bounce, approve must reach ready_for_draft (no dead-end)."""
    from app.parallel_life_deep_reading import service as svc_mod
    from app.parallel_life_deep_reading import v101_gates

    store = DeepReadingSessionStore()
    service = DeepReadingService(store=store)

    call1 = Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V1110,
        schema_version=RUNTIME_VERSION_V1110_EXP,
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="f1",
                    content="恋愛関係を続けた",
                    boundary_type=FactBoundaryType.explicit_fact,
                )
            ],
            questions=[
                GroundedFact(
                    id="q1",
                    content="別の関係を選んでいたら",
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
            current_context=["いまも同じ街にいる"],
            confirmed_by_user=False,
            present_questions=["あのとき別の道を選んでいたら"],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="過去",
                triggering_event="関係の分岐",
                realized_path="関係を続けた",
                unrealized_paths=["離れた"],
                supporting_fact_ids=["f1"],
            )
        ),
        central_thesis=CentralThesis(
            statement="関係の分岐をいま読み直せる。",
            supported_by=["f1"],
            validation_status="soft_fail",
        ),
        meaning_compression=MeaningCompression(
            past_structure="関係を続けた",
            alternative_structure="離れた",
            present_structure="いまも同じ街にいる",
            tension="近さの測り方",
            unresolved_question="問いが残る",
        ),
        validation=Call1Validation(
            notes=["unsupported_causal_framing"],
            branch_concreteness_ok=True,
            material_contradiction_count=0,
        ),
        additional_questions=AdditionalQuestions(required=False, questions=[]),
        user_confirmation_view=UserConfirmationView(
            triggering_event="関係の分岐",
            chosen_path="関係を続けた",
            unchosen_path="離れた",
            current_context=["いまも同じ街にいる"],
            present_questions=["あのとき別の道を選んでいたら"],
        ),
    )

    session = store.create(raw_user_input="恋愛の分岐について", language="ja")
    session.call1 = call1
    session.status = GenerationStatus.ready_for_user_confirmation
    session.model_metadata = {
        "clarification_rounds": MAX_CLARIFICATION_ROUNDS,
        "clarification_exit": "max_rounds_proceed",
        "runtime_validation_version": RUNTIME_VERSION_V1110_EXP,
    }
    store.save(session)

    def _fake_gates(c1, **_kwargs):
        return c1.model_copy(
            update={
                "status": GenerationStatus.needs_additional_input,
                "validation": c1.validation.model_copy(
                    update={
                        "notes": ["unsupported_causal_framing"],
                        "material_contradiction_count": 0,
                        "branch_concreteness_ok": True,
                    }
                ),
            }
        )

    monkeypatch.setattr(svc_mod, "apply_call1_runtime_gates", _fake_gates)
    monkeypatch.setattr(v101_gates, "approval_blocked_reason", lambda *_a, **_k: None)
    monkeypatch.setattr(v101_gates, "detect_material_contradictions", lambda *_a, **_k: [])
    monkeypatch.setattr(svc_mod, "call1_residue_items", lambda _c: ["問いが残る"])

    resp = service.confirm(
        DeepReadingConfirmRequest(
            session_id=session.session_id,
            action="approve",
            confirmation_view_overrides=UserConfirmationView(
                current_context=["いまも同じ街にいる"],
                present_questions=["あのとき別の道を選んでいたら"],
                triggering_event="関係の分岐",
                chosen_path="関係を続けた",
                unchosen_path="離れた",
            ),
        )
    )
    st = resp.session.status
    st_val = st.value if hasattr(st, "value") else str(st)
    assert st_val == "ready_for_draft"
    meta = resp.session.model_metadata or {}
    assert meta.get("clarification_exit") == "sufficient_for_deep_reading"
