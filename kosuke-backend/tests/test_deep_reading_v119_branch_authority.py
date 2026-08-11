"""v1.1.9-exp BranchSemantics authority + clarification exit — deterministic tests."""

from __future__ import annotations

from app.parallel_life_deep_reading.branch_semantics import (
    CALL_1_PROMPT_VERSION_V119,
    RUNTIME_VERSION_V119_EXP,
    allows_career_product_logic,
    attach_branch_semantics,
    build_branch_semantics,
    career_template_leakage,
    detect_semantic_domain_leak,
)
from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
)
from app.parallel_life_deep_reading.models import (
    BranchStructure,
    Call1Result,
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
    build_section_contracts,
    section_contract_evidence_check,
)
from app.parallel_life_deep_reading.service import (
    MAX_CLARIFICATION_ROUNDS,
    DeepReadingService,
    _filter_low_value_questions,
)
from app.parallel_life_deep_reading.session_store import DeepReadingSessionStore


def _base(
    *,
    realized: str,
    unrealized: list[str],
    trigger: str,
    question: str,
    present: str,
    facts: list[GroundedFact],
    thesis: str = "",
) -> Call1Result:
    return Call1Result(
        status=GenerationStatus.ready_for_user_confirmation,
        prompt_version=CALL_1_PROMPT_VERSION_V119,
        grounded_input=GroundedInput(
            facts=facts,
            questions=[
                GroundedFact(
                    id="q1",
                    content=question,
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
            current_context=[present],
            confirmed_by_user=True,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="過去",
                triggering_event=trigger,
                realized_path=realized,
                unrealized_paths=unrealized,
                supporting_fact_ids=[f.id for f in facts[:1]],
            )
        ),
        central_thesis=CentralThesis(
            statement=thesis or f"{realized}という分岐を、いま読み直せる。",
            supported_by=[f.id for f in facts[:2]],
            validation_status="passed",
        ),
        meaning_compression=MeaningCompression(
            past_structure=trigger,
            present_structure=present,
            unresolved_question=question,
        ),
        user_confirmation_view=UserConfirmationView(present_questions=[question]),
    )


def test_active_pins_are_v119():
    # Historical v1.1.9-exp constants remain; active RC pin advanced past -exp label.
    assert CALL_1_PROMPT_VERSION_V119 == "parallel-life-call-1-v1.1.9-exp"
    assert RUNTIME_VERSION_V119_EXP == "parallel-life-runtime-v1.1.9-exp"
    assert CALL_1_PROMPT_VERSION_V11 == "parallel-life-call-1-v1.1.9"
    assert RUNTIME_VERSION_V11_EXP == "parallel-life-runtime-v1.1.11"


def test_education_with_pack_career_no_mobility_template():
    """Background employment must not rewrite education branch semantics."""
    call1 = _base(
        realized="家から通える大学へ進学した",
        unrealized=["別の大学へ進学すること"],
        trigger="どの大学へ進学するか",
        question="別の大学だったらいまの仕事の感じ方は違ったか",
        present="いまは別の仕事をしている",
        facts=[
            GroundedFact(
                id="f_edu_001",
                content="家から通える大学へ進学した",
                boundary_type=FactBoundaryType.explicit_fact,
            ),
            GroundedFact(
                id="pack_career_history_001",
                content="卒業後に会社員として働いた",
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                tags=["context_pack", "category:career_history"],
            ),
            GroundedFact(
                id="pack_current_work_004",
                content="現在は会社員として働いている",
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                tags=["context_pack", "category:current_work"],
            ),
        ],
    )
    sem = build_branch_semantics(call1)
    assert sem.domain == "education"
    assert not allows_career_product_logic(sem)
    assert sem.diagnostics.get("background_employment_context") is True
    assert not career_template_leakage(
        "\n".join(
            [
                sem.central_tension,
                sem.lost_verifiability,
                sem.protected_possibility,
                sem.present_residue,
            ]
        )
    )
    call1, _ = attach_branch_semantics(call1)
    ok, notes, _, contracts = section_contract_evidence_check(call1)
    chosen = contracts.by_id("chosen_path")
    assert chosen is not None
    assert "仕事を定義し直す" not in (chosen.structural_shift or "")
    assert "所属が変わるたびに" not in (chosen.interpretive_claim or "")
    leak = (contracts.diagnostics or {}).get("semantic_domain_leak") or {}
    assert leak.get("leaked") is False
    assert "semantic_domain_leak" not in ",".join(notes)


def test_creative_with_salary_job_no_career_redefinition():
    call1 = _base(
        realized="会社員を続けながら創作を副業として続けること",
        unrealized=["創作を本業にすること"],
        trigger="創作に専念するか勤めを続けるか",
        question="創作を本業にしていたらどうなっていたか",
        present="平日は会社で働き、夜に文章を書いている",
        facts=[
            GroundedFact(
                id="f_cre_001",
                content="小説を書き続けている",
                boundary_type=FactBoundaryType.explicit_fact,
            ),
            GroundedFact(
                id="pack_current_work_004",
                content="会社員として働いている",
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                tags=["context_pack", "category:current_work"],
            ),
        ],
    )
    sem = build_branch_semantics(call1)
    assert sem.domain == "creative"
    assert not allows_career_product_logic(sem)
    blob = "\n".join(
        [
            sem.central_tension,
            sem.lost_verifiability,
            sem.protected_possibility,
            sem.present_residue,
        ]
    )
    assert not career_template_leakage(blob)
    call1, _ = attach_branch_semantics(call1)
    _, _, _, contracts = section_contract_evidence_check(call1)
    chosen = contracts.by_id("chosen_path")
    assert chosen is not None
    assert "仕事を定義し直す" not in (chosen.structural_shift or "")
    leak = detect_semantic_domain_leak(
        sem,
        contract_texts=[
            c.interpretive_claim + "\n" + (c.structural_shift or "")
            for c in contracts.contracts
        ],
    )
    assert leak["leaked"] is False


def test_career_ntt_preserves_career_semantics():
    call1 = _base(
        realized="外資へ移る",
        unrealized=["一企業の内部で役割を積み上げ続けること"],
        trigger="NTTに残るか外資へ移るか",
        question="役職や年収はどうなったか",
        present="いまは自分の会社を経営している",
        facts=[
            GroundedFact(
                id="pack_career_history_001",
                content="NTT東日本で勤務した",
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                tags=["context_pack", "category:career_history"],
            ),
            GroundedFact(
                id="pack_career_history_002",
                content="外資系半導体企業へ転職した",
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="context_pack",
                tags=["context_pack", "category:career_history"],
            ),
        ],
        thesis=(
            "一企業の内部で役割を積み上げる道を離れたという個人の分岐を、"
            "日本型の長期雇用と企業間移動のキャリアモデルと並べて読むことができる。"
        ),
    )
    sem = build_branch_semantics(call1)
    assert sem.domain == "career"
    assert allows_career_product_logic(sem)
    call1, _ = attach_branch_semantics(call1)
    contracts = build_section_contracts(call1)
    chosen = contracts.by_id("chosen_path")
    assert chosen is not None
    assert "定義し直" in (chosen.structural_shift or "") or "移" in (
        chosen.structural_shift or ""
    )


def test_semantic_domain_leak_hard_fail_on_injected_career_copy():
    call1 = _base(
        realized="家から通える大学へ進学した",
        unrealized=["別の大学へ進学すること"],
        trigger="どの大学へ進学するか",
        question="別の大学だったら",
        present="いまは別の仕事をしている",
        facts=[
            GroundedFact(
                id="f_edu_001",
                content="家から通える大学へ進学した",
                boundary_type=FactBoundaryType.explicit_fact,
            ),
        ],
    )
    call1, sem = attach_branch_semantics(call1)
    leak = detect_semantic_domain_leak(
        sem,
        contract_texts=["所属が変わるたびに自分の仕事を定義し直す道へ移った"],
    )
    assert leak["leaked"] is True


def test_duplicate_clarification_filtered():
    asked = ["いまの生活の具体的な場面を教えてください。"]
    answers = ["平日は会社で働き、夜に文章を書いている"]
    qs = _filter_low_value_questions(
        ["いまの生活の具体的な場面を教えてください。", "いまも残る問いは何ですか？"],
        asked=asked,
        answers=answers,
    )
    assert "いまの生活の具体的な場面を教えてください。" not in qs


def test_clarification_exit_insufficient_terminal_no_loop():
    store = DeepReadingSessionStore()
    svc = DeepReadingService(store=store)
    # Structurally incomplete: missing unrealized / present
    call1 = Call1Result(
        status=GenerationStatus.needs_additional_input,
        prompt_version=CALL_1_PROMPT_VERSION_V119,
        grounded_input=GroundedInput(
            facts=[],
            questions=[],
            current_context=[],
            confirmed_by_user=False,
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="",
                triggering_event="よく覚えていない",
                realized_path="",
                unrealized_paths=[],
            )
        ),
        meaning_compression=MeaningCompression(),
        user_confirmation_view=UserConfirmationView(),
    )
    session = store.create(raw_user_input="曖昧な分岐", language="ja")
    session.call1 = call1
    session.status = GenerationStatus.needs_additional_input
    session.model_metadata = {
        "clarification_rounds": MAX_CLARIFICATION_ROUNDS,
        "clarification_asked_questions": [
            "いまの生活の具体的な場面を教えてください。",
            "いまも残る問いは何ですか？",
        ],
    }
    store.save(session)

    resp = svc.confirm(
        DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
    )
    assert resp.status == GenerationStatus.insufficient_for_deep_reading.value
    assert resp.clarification_required is False
    assert resp.questions == []
    assert resp.clarification_exit_reason
    # Second approve must stay terminal (no loop)
    resp2 = svc.confirm(
        DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
    )
    assert resp2.status == GenerationStatus.insufficient_for_deep_reading.value


def test_clarification_exit_proceed_when_structurally_sufficient():
    store = DeepReadingSessionStore()
    svc = DeepReadingService(store=store)
    call1 = _base(
        realized="創作を副業として続ける",
        unrealized=["創作を本業にする"],
        trigger="創作に専念するか",
        question="創作を本業にしていたら",
        present="平日は会社、夜は文章を書いている",
        facts=[
            GroundedFact(
                id="f1",
                content="小説を書いている",
                boundary_type=FactBoundaryType.explicit_fact,
            )
        ],
    ).model_copy(
        update={
            "status": GenerationStatus.needs_additional_input,
            "grounded_input": _base(
                realized="創作を副業として続ける",
                unrealized=["創作を本業にする"],
                trigger="創作に専念するか",
                question="創作を本業にしていたら",
                present="平日は会社、夜は文章を書いている",
                facts=[
                    GroundedFact(
                        id="f1",
                        content="小説を書いている",
                        boundary_type=FactBoundaryType.explicit_fact,
                    )
                ],
            ).grounded_input.model_copy(update={"confirmed_by_user": False}),
        }
    )
    session = store.create(raw_user_input="創作の分岐", language="ja")
    session.call1 = call1
    session.status = GenerationStatus.needs_additional_input
    session.model_metadata = {
        "clarification_rounds": MAX_CLARIFICATION_ROUNDS,
        "clarification_asked_questions": [
            "いまの生活の具体的な場面を教えてください。"
        ],
        "clarification_answer_texts": ["平日は会社、夜は文章を書いている"],
    }
    store.save(session)

    call1_out, session_out, reason = svc._apply_clarification_exit(
        session, call1, increment_round=True
    )
    assert reason is None
    assert call1_out.status == GenerationStatus.ready_for_user_confirmation
    assert session_out.model_metadata.get("clarification_exit") in {
        "max_rounds_proceed",
        "proceed_structurally_sufficient",
    }
