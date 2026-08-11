"""v1.1.8-exp General Branch Semantics — deterministic matrix + negative tests."""

from __future__ import annotations

from app.parallel_life_deep_reading.branch_semantics import (
    CALL_1_PROMPT_VERSION_V118,
    RUNTIME_VERSION_V118_EXP,
    attach_branch_semantics,
    build_branch_semantics,
    career_template_leakage,
)
from app.parallel_life_deep_reading.context_pack import (
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
)
from app.parallel_life_deep_reading.models import (
    BranchStructure,
    Call1Result,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    MeaningCompression,
    PrimaryBranch,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.section_contracts import (
    _has_employment_regime,
    build_rebranch_decision,
    build_section_contracts,
    section_contract_evidence_check,
)


def _base(
    *,
    domain_hint: str,
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
        prompt_version=CALL_1_PROMPT_VERSION_V118,
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


def _matrix_cases() -> dict[str, Call1Result]:
    return {
        "A_career": _base(
            domain_hint="career",
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
                GroundedFact(
                    id="pack_current_work_004",
                    content="現在は自分の会社を経営している",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="context_pack",
                    tags=["context_pack", "category:current_work"],
                ),
            ],
            thesis=(
                "一企業の内部で役割を積み上げる道を離れたという個人の分岐を、"
                "日本型の長期雇用と企業間移動のキャリアモデルと並べて読むことができる。"
            ),
        ),
        "B_family": _base(
            domain_hint="family",
            realized="二人目を目指して治療を続ける",
            unrealized=["治療を止め、三人家族のまま暮らす"],
            trigger="二人目を目指すかどうか",
            question="あのとき治療を止めていたら",
            present="いまは三人家族で暮らしている",
            facts=[
                GroundedFact(
                    id="f_family_001",
                    content="妻と息子と三人家族で暮らしている",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f_family_002",
                    content="二人目の不妊治療を続けた",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "C_education": _base(
            domain_hint="education",
            realized="家から通える大学へ進学した",
            unrealized=["別の大学へ進学すること"],
            trigger="どの大学へ進学するか",
            question="別の大学だったらどうなっていたか",
            present="いまは別の仕事をしている",
            facts=[
                GroundedFact(
                    id="f_edu_001",
                    content="家から通える大学へ進学した",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "D_romance": _base(
            domain_hint="romance",
            realized="別れを選んだ",
            unrealized=["関係を続ける"],
            trigger="別れるか続けるか",
            question="あのとき別れていなかったら",
            present="いまは一人で暮らしている",
            facts=[
                GroundedFact(
                    id="f_rom_001",
                    content="当時のパートナーと別れた",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "E_health": _base(
            domain_hint="health",
            realized="働き方を落として療養した",
            unrealized=["以前と同じペースで働き続ける"],
            trigger="体調を崩したあとの働き方",
            question="無理をして働き続けていたら",
            present="いまは短い時間で働いている",
            facts=[
                GroundedFact(
                    id="f_health_001",
                    content="体調を崩して入院した",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "F_entrepreneurship": _base(
            domain_hint="entrepreneurship",
            realized="自分の会社を立ち上げた",
            unrealized=["安定した勤めを続ける"],
            trigger="起業するか勤めを続けるか",
            question="勤めを続けていたら",
            present="いまは自分の会社を経営している",
            facts=[
                GroundedFact(
                    id="f_ent_001",
                    content="安定した勤めを辞めて起業した",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
                GroundedFact(
                    id="f_ent_002",
                    content="現在は自分の会社を経営している",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "G_creative": _base(
            domain_hint="creative",
            realized="会社勤めを続けながら小説を書き続けた",
            unrealized=["創作に専念する"],
            trigger="創作に専念するか勤めを続けるか",
            question="小説だけにしていたら",
            present="いまも仕事のあとに小説を書いている",
            facts=[
                GroundedFact(
                    id="f_cre_001",
                    content="小説を書き続けている",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "H_vague": _base(
            domain_hint="vague",
            realized="",
            unrealized=[],
            trigger="よく覚えていない分かれ道",
            question="あのとき別の道を選んでいたら",
            present="いまの生活",
            facts=[],
        ),
        "I_zero_lens": _base(
            domain_hint="place",
            realized="地元に残った",
            unrealized=["都会へ出る"],
            trigger="地元に残るか都会へ出るか",
            question="都会へ出ていたら",
            present="いまも地元で暮らしている",
            facts=[
                GroundedFact(
                    id="f_place_001",
                    content="地元に残って暮らしている",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
        "J_sensitive": _base(
            domain_hint="health",
            realized="仕事を休んで治療に入った",
            unrealized=["症状を抱えたまま働き続ける"],
            trigger="病のあとにどう働くか",
            question="働き続けていたら体はどうなっていたか",
            present="いまは治療を続けながら短い時間働いている",
            facts=[
                GroundedFact(
                    id="f_sens_001",
                    content="病気の治療のために仕事を休んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                ),
            ],
        ),
    }


def test_historical_v118_pins_stable():
    assert CALL_1_PROMPT_VERSION_V118 == "parallel-life-call-1-v1.1.8-exp"
    assert RUNTIME_VERSION_V118_EXP == "parallel-life-runtime-v1.1.8-exp"
    # Active Contextual pin may advance (v1.1.9+); v118 constants remain frozen.
    assert CALL_1_PROMPT_VERSION_V11 != ""
    assert RUNTIME_VERSION_V11_EXP != ""


def test_semantics_matrix_domains_and_no_career_leak():
    cases = _matrix_cases()
    expected_domain = {
        "A_career": "career",
        "B_family": "family",
        "C_education": "education",
        "D_romance": "romance",
        "E_health": "health",
        "F_entrepreneurship": {"entrepreneurship", "career", "mixed"},
        "G_creative": "creative",
        "H_vague": {"unknown", "mixed"},
        "I_zero_lens": "place",
        "J_sensitive": "health",
    }
    for key, call1 in cases.items():
        sem = build_branch_semantics(call1)
        exp = expected_domain[key]
        if isinstance(exp, set):
            assert sem.domain in exp, f"{key}: domain={sem.domain}"
        else:
            assert sem.domain == exp, f"{key}: domain={sem.domain}"
        assert (sem.changed_dimension or "").strip(), f"{key}: empty changed_dimension"
        blob = "\n".join(
            [
                sem.lost_verifiability,
                sem.protected_possibility,
                sem.present_residue,
                sem.central_tension,
                " ".join(sem.possible_rebranch_modes),
            ]
        )
        # Career / entrepreneurship may use employment-regime templates intentionally.
        if key not in {"A_career", "F_entrepreneurship"}:
            assert not career_template_leakage(blob), f"{key}: career leak in semantics\n{blob}"
        # Required semantic fields for non-vague
        if key != "H_vague":
            assert sem.lost_verifiability
            assert sem.protected_possibility
            assert sem.present_residue
            assert sem.possible_rebranch_modes
        if key == "J_sensitive":
            assert "no_unsupported_causality" in sem.sensitive_boundaries


def test_negative_family_no_salary_or_redefine_work():
    call1, _ = attach_branch_semantics(_matrix_cases()["B_family"])
    _, _, updated, contracts = section_contract_evidence_check(call1)
    text = "\n".join(
        [
            c.required_meaning + "\n" + c.interpretive_claim
            for c in contracts.contracts
        ]
    )
    assert "役職や年収" not in text
    assert "仕事を定義し直す" not in text
    assert not _has_employment_regime(updated)


def test_negative_romance_no_accumulation_institution():
    call1, _ = attach_branch_semantics(_matrix_cases()["D_romance"])
    _, _, _, contracts = section_contract_evidence_check(call1)
    text = "\n".join(c.interpretive_claim for c in contracts.contracts)
    assert "蓄積" not in text
    assert "制度内評価" not in text
    assert "役職や年収" not in text


def test_negative_education_not_auto_career_mobility():
    call1, _ = attach_branch_semantics(_matrix_cases()["C_education"])
    sem = build_branch_semantics(call1)
    assert sem.domain == "education"
    assert "所属が変わるたびに自分の仕事" not in (sem.protected_possibility or "")
    _, _, _, contracts = section_contract_evidence_check(call1)
    chosen = contracts.by_id("chosen_path")
    assert chosen is not None
    assert "仕事を定義し直す" not in (chosen.interpretive_claim or "")


def test_negative_creative_not_auto_entrepreneur_self_definition():
    call1, _ = attach_branch_semantics(_matrix_cases()["G_creative"])
    sem = build_branch_semantics(call1)
    assert sem.domain == "creative"
    decision = build_rebranch_decision(call1)
    assert "役職や年収" not in (decision.what_is_no_longer_required or "")
    assert "長期の積み重ね" not in (decision.what_can_now_be_chosen or "")


def test_negative_health_no_causality_invention_in_semantics():
    call1 = _matrix_cases()["E_health"]
    sem = build_branch_semantics(call1)
    blob = f"{sem.lost_verifiability}\n{sem.protected_possibility}\n{sem.present_residue}"
    assert not re_search_causal(blob)


def re_search_causal(text: str) -> bool:
    import re

    return bool(re.search(r"(?:引き起こ|のせいだ|が原因で|させた|強いた)", text or ""))


def test_employment_regime_not_triggered_by_bare_stay_leave():
    call1 = _matrix_cases()["I_zero_lens"]
    call1, _ = attach_branch_semantics(call1)
    assert not _has_employment_regime(call1)


def test_ntt_regression_career_semantics_available():
    call1, sem = attach_branch_semantics(_matrix_cases()["A_career"])
    assert sem.domain == "career"
    assert _has_employment_regime(call1)
    assert "制度" in sem.lost_verifiability or "確か" in sem.lost_verifiability
    decision = build_rebranch_decision(call1)
    # Career + salary question may still use metric redefinition
    assert decision.present_choice
    _, _, _, contracts = section_contract_evidence_check(call1)
    lost = contracts.by_id("lost")
    protected = contracts.by_id("protected")
    re_b = contracts.by_id("re_branch")
    assert lost and lost.must_be_present and lost.interpretive_claim
    assert protected and protected.must_be_present and protected.interpretive_claim
    assert re_b and re_b.must_be_present and re_b.interpretive_claim


def test_clarification_approve_returns_200_state_not_error():
    from app.parallel_life_deep_reading.models import DeepReadingConfirmRequest
    from app.parallel_life_deep_reading.service import DeepReadingService
    from app.parallel_life_deep_reading.session_store import DeepReadingSessionStore

    store = DeepReadingSessionStore()
    svc = DeepReadingService(store=store)
    call1 = _matrix_cases()["D_romance"].model_copy(
        update={
            "status": GenerationStatus.needs_additional_input,
            "grounded_input": _matrix_cases()["D_romance"].grounded_input.model_copy(
                update={"confirmed_by_user": False, "current_context": []}
            ),
        }
    )
    session = store.create(raw_user_input="別れの分岐", language="ja")
    session.call1 = call1
    session.status = GenerationStatus.needs_additional_input
    store.save(session)

    resp = svc.confirm(
        DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
    )
    assert resp.status == GenerationStatus.needs_additional_input.value
    assert resp.clarification_required is True
    assert resp.session.call1 is not None
    assert resp.session.call1.grounded_input.confirmed_by_user is False
