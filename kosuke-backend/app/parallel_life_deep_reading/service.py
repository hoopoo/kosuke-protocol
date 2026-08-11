"""Deep Reading service: ground → confirm → draft → edit-validate."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.parallel_life_deep_reading.draft import parse_call2_payload, run_call2_draft
from app.parallel_life_deep_reading.edit_validate import export_markdown, run_call3_edit_validate
from app.parallel_life_deep_reading.call1_schema import (
    AdditionalQuestions,
    Call1SchemaError,
    call1_additional_question_list,
    call1_evaluated_lenses,
    call1_rebranch_directions,
    call1_residue_items,
    call1_selected_lenses,
)
from app.parallel_life_deep_reading.grounding import parse_call1_payload, run_call1_grounding
from app.parallel_life_deep_reading.llm import (
    DeepReadingGenerationError,
    DeepReadingLLMRequiredError,
)
from app.parallel_life_deep_reading.models import (
    Call1Result,
    DeepReadingConfirmRequest,
    DeepReadingGroundRequest,
    DeepReadingSession,
    DeepReadingSessionResponse,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    UserConfirmationView,
)
from app.parallel_life_deep_reading.prompts import PROMPT_VERSIONS
from app.parallel_life_deep_reading.runtime_validation import (
    apply_call1_runtime_gates,
    build_input_corpus,
    is_generic_current_context_label,
    looks_like_internal_ui_token,
    progress_label_for_status,
)
from app.parallel_life_deep_reading.session_store import (
    SessionStoreProtocol,
    StaleSessionRevisionError,
    get_session_store,
)

MAX_DRAFT_ATTEMPTS = 3
MAX_EDIT_ATTEMPTS = 3
MAX_GROUND_ATTEMPTS = 5
# v1.1.9: bounded clarification — no infinite equivalent-question loops
MAX_CLARIFICATION_ROUNDS = 2

_CLARIFYING_STATUSES = frozenset(
    {
        GenerationStatus.needs_additional_input.value,
        GenerationStatus.structural_ambiguity.value,
        GenerationStatus.insufficient_current_context.value,
        GenerationStatus.sensitive_domain_clarification_required.value,
    }
)


def _norm_question(text: str) -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    t = re.sub(r"[？?。．!！]+$", "", t)
    return t


def _branch_structurally_sufficient(call1: Call1Result) -> bool:
    pb = call1.branch_structure.primary_branch
    has_fork = bool(
        (pb.triggering_event or "").strip()
        and (pb.realized_path or "").strip()
        and (pb.unrealized_paths or [])
    )
    has_present = bool(
        any((c or "").strip() for c in (call1.grounded_input.current_context or []))
        or any((q.content or "").strip() for q in (call1.grounded_input.questions or []))
        or any(
            (q or "").strip()
            for q in (call1.user_confirmation_view.present_questions or [])
        )
    )
    return has_fork and has_present


def _answers_already_satisfy(question: str, answers: list[str]) -> bool:
    """Heuristic: existing answer already covers the question's intent."""
    qn = _norm_question(question)
    if not qn:
        return True
    keys: list[str] = []
    if re.search(r"(?:いま|生活|場面|現在)", question):
        keys.extend(["いま", "生活", "会社", "家族", "仕事", "創作", "治療"])
    if re.search(r"(?:問い|残る|気になる)", question):
        keys.extend(["？", "?", "どう", "もし", "たら"])
    if not keys:
        return False
    for ans in answers:
        a = ans or ""
        if len(a.strip()) < 4:
            continue
        if any(k in a for k in keys):
            return True
    return False


def _filter_low_value_questions(
    questions: list[str],
    *,
    asked: list[str],
    answers: list[str],
) -> list[str]:
    asked_n = {_norm_question(q) for q in asked if q}
    out: list[str] = []
    for q in questions:
        n = _norm_question(q)
        if not n:
            continue
        if n in asked_n:
            continue
        # Near-duplicate: shared long stem
        if any(n[:12] and n[:12] in a for a in asked_n if len(a) >= 12):
            continue
        if _answers_already_satisfy(q, answers):
            continue
        out.append(q)
        asked_n.add(n)
    return out


def _clean_view_texts(texts: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in texts or []:
        text = (raw or "").strip()
        if not text or text == "なし":
            continue
        if looks_like_internal_ui_token(text) or is_generic_current_context_label(text):
            continue
        out.append(text)
    return out


def _facts_from_view_texts(
    texts: list[str],
    *,
    prefix: str,
    boundary: FactBoundaryType,
) -> list[GroundedFact]:
    return [
        GroundedFact(
            id=f"{prefix}_{i + 1:03d}",
            content=text,
            boundary_type=boundary,
            source_field="user_confirmation_view",
            source_text=text,
        )
        for i, text in enumerate(texts)
    ]


def apply_confirmation_view_to_call1(
    call1: Call1Result,
    view: UserConfirmationView,
) -> Call1Result:
    """Sync confirmation-view edits into grounded_input before runtime gates.

    Without this, present_questions / feelings edited in the UI never reach
    coverage/residue checks, so approve stays blocked as needs_additional_input.
    """
    primary = call1.branch_structure.primary_branch.model_copy(
        update={
            "period": (view.branch_period or "").strip()
            or call1.branch_structure.primary_branch.period,
            "triggering_event": (view.triggering_event or "").strip()
            or call1.branch_structure.primary_branch.triggering_event,
            "realized_path": (view.chosen_path or "").strip()
            or call1.branch_structure.primary_branch.realized_path,
            "unrealized_paths": (
                [view.unchosen_path.strip()]
                if (view.unchosen_path or "").strip()
                else call1.branch_structure.primary_branch.unrealized_paths
            ),
        }
    )

    questions = _facts_from_view_texts(
        _clean_view_texts(view.present_questions),
        prefix="q_confirm",
        boundary=FactBoundaryType.user_question,
    )
    feelings = _facts_from_view_texts(
        _clean_view_texts(view.feelings),
        prefix="feel_confirm",
        boundary=FactBoundaryType.user_feeling,
    )
    hypotheses = _facts_from_view_texts(
        _clean_view_texts(view.hypotheses),
        prefix="hyp_confirm",
        boundary=FactBoundaryType.user_hypothesis,
    )
    unknowns = _facts_from_view_texts(
        _clean_view_texts(view.unknowns),
        prefix="unk_confirm",
        boundary=FactBoundaryType.unknown,
    )
    current_context = _clean_view_texts(view.current_context)
    thesis_preview = (view.central_thesis_preview or "").strip()

    # If the thesis preview is itself a lingering question, keep coverage.present_question true.
    if thesis_preview and (
        "？" in thesis_preview
        or "?" in thesis_preview
        or thesis_preview.endswith("か")
        or "どう" in thesis_preview
    ):
        if not any(thesis_preview == q.content for q in questions):
            questions.append(
                GroundedFact(
                    id="q_confirm_thesis",
                    content=thesis_preview,
                    boundary_type=FactBoundaryType.user_question,
                    source_field="user_confirmation_view",
                    source_text=thesis_preview,
                )
            )

    grounded = call1.grounded_input.model_copy(
        update={
            "current_context": current_context or call1.grounded_input.current_context,
            "questions": questions or call1.grounded_input.questions,
            "feelings": feelings or call1.grounded_input.feelings,
            "hypotheses": hypotheses or call1.grounded_input.hypotheses,
            "unknowns": unknowns or call1.grounded_input.unknowns,
        }
    )
    return call1.model_copy(
        update={
            "grounded_input": grounded,
            "branch_structure": call1.branch_structure.model_copy(
                update={"primary_branch": primary}
            ),
            "user_confirmation_view": view,
            "central_thesis": call1.central_thesis.model_copy(
                update={
                    "statement": thesis_preview or call1.central_thesis.statement
                }
            ),
        }
    )


class DeepReadingService:
    def __init__(self, store: Optional[SessionStoreProtocol] = None) -> None:
        self.store = store or get_session_store()

    def _save(self, session: DeepReadingSession) -> DeepReadingSession:
        """Persist with optimistic concurrency; return store-authoritative copy."""
        try:
            return self.store.save(session, expected_revision=session.session_revision)
        except StaleSessionRevisionError as exc:
            raise DeepReadingGenerationError(
                "セッションが更新されています。画面を再読み込みしてから再試行してください。"
            ) from exc

    def _diagnostics(self, session: DeepReadingSession) -> dict[str, Any]:
        call1 = session.call1
        call3 = session.call3
        return {
            "session_id": session.session_id,
            "prompt_versions": dict(session.prompt_versions or PROMPT_VERSIONS),
            "schema_version": session.schema_version,
            "status": session.status.value if session.status else None,
            "branch_classifications": {
                "actual_secondary": [
                    b.classification.value
                    for b in (call1.branch_structure.secondary_branches if call1 else [])
                ],
                "retrospective_counterfactual": [
                    b.classification.value
                    for b in (
                        call1.branch_structure.retrospective_counterfactuals if call1 else []
                    )
                ],
            },
            "selected_lens_evidence_gates": [
                {
                    "lens_id": c.lens_id,
                    "evidence_gate_passed": c.evidence_gate_passed,
                    "explicit_evidence_ids": c.explicit_evidence_ids,
                    "residue_evidence_ids": c.residue_evidence_ids,
                    "rejection_reason": c.rejection_reason,
                }
                for c in (call1_selected_lenses(call1) if call1 else [])
            ],
            "evaluated_lens_gates": [
                {
                    "lens_id": c.lens_id,
                    "evidence_gate_passed": c.evidence_gate_passed,
                    "rejection_reason": c.rejection_reason,
                }
                for c in (call1_evaluated_lenses(call1) if call1 else [])
            ],
            "rebranch_genericity_scores": [
                {
                    "id": r.id,
                    "genericity_score": r.genericity_score,
                    "publishable": r.publishable,
                }
                for r in (
                    (session.call2.rebranch_candidates if session.call2 else None)
                    or (call1_rebranch_directions(call1) if call1 else [])
                )
            ],
            "source_coverage": (
                call1.source_coverage.model_dump(mode="json")
                if call1 and getattr(call1, "source_coverage", None)
                else None
            ),
            "parse_diagnostics": (
                call1.parse_diagnostics.model_dump(mode="json")
                if call1 and getattr(call1, "parse_diagnostics", None)
                else None
            ),
            "unsupported_scene_count": len(call3.validation.unsupported_scenes)
            if call3
            else 0,
            "validation_result": call3.validation.model_dump(mode="json") if call3 else None,
            "generation_attempt_count": session.generation_attempt_count,
            "draft_attempt_count": session.draft_attempt_count,
            "edit_attempt_count": session.edit_attempt_count,
        }

    def _session_corpus(self, session: DeepReadingSession) -> str:
        corpus = build_input_corpus(
            session.raw_user_input,
            clarifications=session.clarifications,
            editorial_context=session.editorial_context,
            answers=session.clarifications,
        )
        if session.deep_reading_mode == "contextual" and session.context_pack:
            from app.parallel_life_deep_reading.context_pack import (
                ContextPack,
                pack_corpus_text,
            )

            try:
                pack = ContextPack.model_validate(session.context_pack)
            except Exception:
                return corpus
            pack_text = pack_corpus_text(pack)
            if pack_text:
                return f"{corpus}\n{pack_text}".strip()
        return corpus

    def _session_pack_and_mode(
        self, session: DeepReadingSession
    ) -> tuple[Any | None, str]:
        mode = session.deep_reading_mode or "strict"
        pack = None
        if mode == "contextual" and session.context_pack:
            from app.parallel_life_deep_reading.context_pack import ContextPack

            try:
                pack = ContextPack.model_validate(session.context_pack)
            except Exception:
                pack = None
                mode = "strict"
        return pack, mode

    def _approve_incomplete_message(self, call1: Call1Result) -> str:
        missing = list(
            getattr(call1.validation, "source_coverage_missing", None)
            or (call1.source_coverage.missing() if call1.source_coverage else [])
        )
        if call1.validation.material_contradiction_count > 0:
            return (
                "入力内容に矛盾があります。"
                "確認事項を直し、追加の質問に答えてから再度お進みください。"
            )
        if call1.status == GenerationStatus.structural_ambiguity:
            return (
                "分岐として読むための具体情報が不足しています。"
                "追加の質問に答えてから再度お進みください。"
            )
        if missing == ["present_question"] or set(missing) == {"present_question"}:
            return (
                "今も残る問いがまだ確認できていません。"
                "下の追加質問に答えてから再度お進みください。"
            )
        if "current_context" in missing or not call1.input_sufficiency.current_context_requirement_met:
            return (
                "今の生活の具体的な場面が不足しています。"
                "家族構成だけでなく、いまの暮らしの様子を書いてから再度お進みください。"
            )
        if not call1_residue_items(call1):
            return (
                "過去の分岐と今の生活をつなぐ論点がまだ足りません。"
                "今の生活の具体的な場面を足してから再度お進みください。"
            )
        if call1.additional_questions.required and call1.additional_questions.questions:
            return (
                "確認の前に、追加質問への回答が必要です。"
                "下の質問に答えてから再度お進みください。"
            )
        return (
            "確認を完了できません。不足している情報を補ってから再度お進みください。"
        )

    def _clarification_questions(
        self,
        call1: Call1Result | None,
        *,
        session: DeepReadingSession | None = None,
    ) -> list[str]:
        if not call1:
            return []
        qs = list(call1.additional_questions.questions or [])
        missing = list(
            getattr(call1.validation, "source_coverage_missing", None)
            or (call1.source_coverage.missing() if call1.source_coverage else [])
        )
        if "present_question" in missing and not qs:
            qs.append("いまも残る問いは何ですか？")
        if "current_context" in missing and not any("いま" in q or "生活" in q for q in qs):
            qs.append("いまの生活の具体的な場面を教えてください。")
        meta = dict((session.model_metadata if session else None) or {})
        asked = list(meta.get("clarification_asked_questions") or [])
        answers = list(meta.get("clarification_answer_texts") or [])
        if session and session.user_corrections:
            answers.extend([a for a in session.user_corrections if isinstance(a, str)])
        if call1.grounded_input.current_context:
            answers.extend(list(call1.grounded_input.current_context))
        return _filter_low_value_questions(qs, asked=asked, answers=answers)

    def _bump_clarification_meta(
        self,
        session: DeepReadingSession,
        *,
        questions: list[str],
        answers: list[str] | None = None,
        increment_round: bool = False,
    ) -> dict[str, Any]:
        meta = dict(session.model_metadata or {})
        asked = list(meta.get("clarification_asked_questions") or [])
        for q in questions:
            n = _norm_question(q)
            if n and n not in {_norm_question(x) for x in asked}:
                asked.append(q)
        meta["clarification_asked_questions"] = asked
        if answers:
            texts = list(meta.get("clarification_answer_texts") or [])
            for a in answers:
                if a and a.strip() and a.strip() not in texts:
                    texts.append(a.strip())
            meta["clarification_answer_texts"] = texts
        if increment_round:
            meta["clarification_rounds"] = int(meta.get("clarification_rounds") or 0) + 1
        session.model_metadata = meta
        return meta

    def _apply_clarification_exit(
        self,
        session: DeepReadingSession,
        call1: Call1Result,
        *,
        increment_round: bool = False,
    ) -> tuple[Call1Result, DeepReadingSession, str | None]:
        """Bounded clarification policy (max 2 rounds). Returns exit_reason if terminal."""
        questions = self._clarification_questions(call1, session=session)
        # Persist filtered questions onto call1 so UI/API stay consistent
        if call1.additional_questions.required or questions:
            status_for_req = (
                call1.status.value
                if hasattr(call1.status, "value")
                else str(call1.status)
            )
            call1 = call1.model_copy(
                update={
                    "additional_questions": AdditionalQuestions(
                        required=bool(questions) and status_for_req in _CLARIFYING_STATUSES,
                        questions=questions,
                    )
                }
            )
        meta = self._bump_clarification_meta(
            session, questions=questions, increment_round=increment_round
        )
        rounds = int(meta.get("clarification_rounds") or 0)
        status_val = (
            call1.status.value if hasattr(call1.status, "value") else str(call1.status)
        )
        clarifying = status_val in _CLARIFYING_STATUSES

        if not clarifying:
            return call1, session, None

        # No new material question and branch is enough → proceed with known facts
        if not questions and _branch_structurally_sufficient(call1):
            call1 = call1.model_copy(
                update={
                    "status": GenerationStatus.ready_for_user_confirmation,
                    "additional_questions": AdditionalQuestions(
                        required=False, questions=[]
                    ),
                }
            )
            meta["clarification_exit"] = "proceed_structurally_sufficient"
            session.model_metadata = meta
            session.status = call1.status
            return call1, session, None

        if rounds < MAX_CLARIFICATION_ROUNDS and questions:
            return call1, session, None

        # Max rounds reached (or no useful question left)
        if _branch_structurally_sufficient(call1):
            call1 = call1.model_copy(
                update={
                    "status": GenerationStatus.ready_for_user_confirmation,
                    "additional_questions": AdditionalQuestions(
                        required=False, questions=[]
                    ),
                }
            )
            meta["clarification_exit"] = "max_rounds_proceed"
            session.model_metadata = meta
            session.status = call1.status
            return call1, session, None

        reason = (
            "深読みに必要な分岐の骨格（分かれ目・選んだ道・選ばなかった道）または"
            "いまの生活の手がかりが足りません。分岐の入力を編集してから再度お試しください。"
        )
        notes = list(call1.validation.notes or [])
        notes.append("clarification_exit:insufficient_for_deep_reading")
        call1 = call1.model_copy(
            update={
                "status": GenerationStatus.insufficient_for_deep_reading,
                "additional_questions": AdditionalQuestions(required=False, questions=[]),
                "validation": call1.validation.model_copy(update={"notes": notes}),
            }
        )
        meta["clarification_exit"] = "insufficient_for_deep_reading"
        meta["clarification_exit_reason"] = reason
        session.model_metadata = meta
        session.status = call1.status
        return call1, session, reason

    def _response(
        self,
        session: DeepReadingSession,
        *,
        include_diagnostics: bool | None = None,
        clarification_exit_reason: str | None = None,
    ) -> DeepReadingSessionResponse:
        if include_diagnostics is None:
            include_diagnostics = os.environ.get("DEEP_READING_DEV_DIAGNOSTICS", "").lower() in {
                "1",
                "true",
                "yes",
            } or os.environ.get("ENV", "").lower() in {"dev", "development", "test"}
        status_val = (
            session.status.value if hasattr(session.status, "value") else str(session.status)
        )
        clarifying = status_val in _CLARIFYING_STATUSES
        exit_reason = clarification_exit_reason or (
            (session.model_metadata or {}).get("clarification_exit_reason")
            if status_val == GenerationStatus.insufficient_for_deep_reading.value
            else None
        )
        return DeepReadingSessionResponse(
            session=session,
            progress_label=progress_label_for_status(session.status),
            diagnostics=self._diagnostics(session) if include_diagnostics else None,
            status=status_val,
            questions=self._clarification_questions(session.call1, session=session)
            if clarifying
            else [],
            clarification_required=clarifying,
            clarification_exit_reason=exit_reason,
        )

    def ground(
        self,
        request: DeepReadingGroundRequest,
        *,
        inject_call1: Call1Result | None = None,
    ) -> DeepReadingSessionResponse:
        from app.parallel_life_deep_reading.context_pack import (
            CALL_1_PROMPT_VERSION_V11,
            ContextPack,
            DeepReadingMode,
            RUNTIME_VERSION_V11_EXP,
            approve_context_pack,
            pack_corpus_text,
            resolve_effective_mode,
        )

        pack: ContextPack | None = None
        if request.context_pack:
            try:
                pack = ContextPack.model_validate(request.context_pack)
            except Exception:
                pack = None
            if pack is not None and pack.approved_by_user:
                pack = approve_context_pack(pack)

        mode = resolve_effective_mode(
            requested_mode=request.deep_reading_mode, pack=pack
        )
        use_v11 = mode == DeepReadingMode.contextual

        session = self.store.create(
            raw_user_input=request.source_text,
            language=request.language,
            clarifications=request.clarifications,
            editorial_context=request.editorial_context,
        )
        session.generation_attempt_count = 1
        session.prompt_versions = dict(PROMPT_VERSIONS)
        if use_v11:
            session.prompt_versions = {
                **session.prompt_versions,
                "call_1": CALL_1_PROMPT_VERSION_V11,
            }
        session.deep_reading_mode = mode.value
        session.context_pack = (
            pack.model_dump(mode="json") if use_v11 and pack is not None else None
        )
        from app.parallel_life_deep_reading import SCHEMA_VERSION
        from app.parallel_life_deep_reading.production_models import (
            PRODUCTION_MODELS_VERSION,
            production_model_metadata,
        )

        runtime_pin = RUNTIME_VERSION_V11_EXP if use_v11 else SCHEMA_VERSION
        session.schema_version = runtime_pin
        session.model_metadata = {
            **production_model_metadata(),
            "runtime_validation_version": runtime_pin,
            "prompt_versions": dict(session.prompt_versions),
            "candidate": (
                "Deep Reading v1.1.0-exp Contextual"
                if use_v11
                else "Production Candidate v1.0"
            ),
            # Back-compat single field: Call 1 model (stable).
            "model": production_model_metadata()["call_1_model"],
            "production_models_version": PRODUCTION_MODELS_VERSION,
            "deep_reading_mode": mode.value,
            "context_pack_enabled": use_v11,
        }

        try:
            ground_corpus = build_input_corpus(
                request.source_text,
                clarifications=request.clarifications,
                editorial_context=request.editorial_context,
                answers=request.answers_to_additional_questions,
            )
            if use_v11 and pack is not None:
                pack_text = pack_corpus_text(pack)
                if pack_text:
                    ground_corpus = f"{ground_corpus}\n{pack_text}".strip()
            if inject_call1 is not None:
                call1 = apply_call1_runtime_gates(
                    inject_call1,
                    source_text=request.source_text,
                    input_corpus=ground_corpus,
                    context_pack=pack if use_v11 else None,
                    deep_reading_mode=mode.value,
                )
            else:
                call1 = run_call1_grounding(
                    request.source_text,
                    clarifications=request.clarifications,
                    editorial_context=request.editorial_context,
                    answers_to_additional_questions=request.answers_to_additional_questions,
                    deep_reading_mode=mode.value,
                    context_pack=pack if use_v11 else None,
                )
        except DeepReadingLLMRequiredError:
            self.store.delete(session.session_id)
            raise
        except Call1SchemaError as exc:
            # Surface typed schema failure to the client without crashing the flow.
            session.call1 = exc.partial
            session.status = GenerationStatus.schema_validation_failed
            session.model_metadata["call1_schema_error"] = {
                "validation_errors": exc.diagnostics.validation_errors,
                "offending_paths": exc.diagnostics.offending_paths,
                "repair_attempted": exc.diagnostics.repair_attempted,
                "repair_succeeded": exc.diagnostics.repair_succeeded,
            }
            session = self._save(session)
            return self._response(session, include_diagnostics=True)
        except DeepReadingGenerationError:
            session.status = GenerationStatus.editorial_failure
            session = self._save(session)
            raise

        # Stamp source_text onto facts for copy detection
        facts = [
            f.model_copy(update={"source_text": f.source_text or request.source_text})
            for f in call1.grounded_input.facts
        ]
        call1 = call1.model_copy(
            update={
                "grounded_input": call1.grounded_input.model_copy(update={"facts": facts})
            }
        )
        call1 = apply_call1_runtime_gates(
            call1,
            source_text=request.source_text,
            input_corpus=ground_corpus,
            context_pack=pack if use_v11 else None,
            deep_reading_mode=mode.value,
        )

        session.schema_version = runtime_pin
        meta = dict(session.model_metadata or {})
        meta["call_1_model"] = meta.get("call_1_model") or meta.get("model")
        meta["call_1_prompt_version"] = getattr(call1, "prompt_version", None)
        meta["call_1_schema_version"] = getattr(call1, "schema_version", None)
        meta["context_pack_usage"] = getattr(call1, "context_pack_usage", None)
        meta["selection_compression"] = getattr(
            call1, "selection_compression_diagnostics", None
        )
        meta["resume_density_report"] = getattr(call1, "resume_density_report", None)
        meta["manuscript_logic_ids"] = list(
            getattr(
                getattr(call1, "relevant_context_selection", None),
                "manuscript_logic_ids",
                None,
            )
            or []
        )
        session.model_metadata = meta
        status_val = (
            call1.status.value if hasattr(call1.status, "value") else str(call1.status)
        )
        exit_reason = None
        if status_val in _CLARIFYING_STATUSES:
            call1, session, exit_reason = self._apply_clarification_exit(
                session, call1, increment_round=True
            )
        session.call1 = call1
        session.status = call1.status
        session = self._save(session)
        return self._response(
            session,
            include_diagnostics=True,
            clarification_exit_reason=exit_reason,
        )

    def confirm(self, request: DeepReadingConfirmRequest) -> DeepReadingSessionResponse:
        session = self.store.get(request.session_id)
        if not session or not session.call1:
            raise KeyError("session_not_found")

        if request.action == "abort":
            session.status = GenerationStatus.editorial_failure
            session = self._save(session)
            return self._response(session)

        pack, mode = self._session_pack_and_mode(session)
        call1 = session.call1
        grounded = call1.grounded_input

        if request.action == "answer":
            # Merge answers into current_context / questions lightly; re-run gates
            extras = [
                v.strip()
                for v in request.answers_to_additional_questions.values()
                if v and v.strip()
            ]
            ctx = list(grounded.current_context)
            questions = list(grounded.questions)
            q_seen = {q.content.strip() for q in questions}
            for ans in extras:
                if any(
                    tok in ans
                    for tok in ("？", "?", "考える", "気になる", "どう", "もし")
                ):
                    if ans not in q_seen:
                        questions.append(
                            GroundedFact(
                                id=f"q_answer_{len(questions)+1:03d}",
                                content=ans,
                                boundary_type=FactBoundaryType.user_question,
                                source_field="additional_answer",
                                source_text=ans,
                                allowed_as_fact=False,
                            )
                        )
                        q_seen.add(ans)
                else:
                    ctx.append(ans)
            grounded = grounded.model_copy(
                update={"current_context": ctx, "questions": questions}
            )
            call1 = call1.model_copy(
                update={
                    "grounded_input": grounded,
                    "additional_questions": AdditionalQuestions(required=False, questions=[]),
                    "input_sufficiency": call1.input_sufficiency.model_copy(
                        update={
                            "additional_questions": [],
                            "current_context_requirement_met": len(ctx) >= 1,
                        }
                    ),
                }
            )
            call1 = apply_call1_runtime_gates(
                call1,
                source_text=session.raw_user_input,
                input_corpus=self._session_corpus(session),
                context_pack=pack,
                deep_reading_mode=mode,
            )
            session.user_corrections.extend(extras)
            self._bump_clarification_meta(
                session, questions=[], answers=extras, increment_round=False
            )
            call1, session, exit_reason = self._apply_clarification_exit(
                session, call1, increment_round=True
            )
            session.call1 = call1
            session.status = call1.status
            session = self._save(session)
            return self._response(session, clarification_exit_reason=exit_reason)

        if request.action == "edit":
            view = request.confirmation_view_overrides or call1.user_confirmation_view
            corrections = request.corrections or {}
            session.user_corrections.append(str(corrections))
            # Optional re-ground with corrections via inject-friendly update
            if corrections.get("reground") and corrections.get("source_text"):
                try:
                    call1 = run_call1_grounding(
                        str(corrections["source_text"]),
                        clarifications=session.clarifications,
                        editorial_context=session.editorial_context,
                        answers_to_additional_questions=request.answers_to_additional_questions,
                        deep_reading_mode=mode,
                        context_pack=pack,
                    )
                except DeepReadingGenerationError:
                    raise
            else:
                call1 = apply_confirmation_view_to_call1(call1, view)
                call1 = call1.model_copy(
                    update={
                        "grounded_input": call1.grounded_input.model_copy(
                            update={"requested_corrections": list(corrections.keys())}
                        )
                    }
                )
                call1 = apply_call1_runtime_gates(
                    call1,
                    source_text=session.raw_user_input,
                    input_corpus=self._session_corpus(session),
                    context_pack=pack,
                    deep_reading_mode=mode,
                )
            session.call1 = call1
            session.status = GenerationStatus.ready_for_user_confirmation
            session = self._save(session)
            return self._response(session)

        # approve
        from app.parallel_life_deep_reading.v101_gates import (
            approval_blocked_reason,
            detect_material_contradictions,
        )

        corpus = self._session_corpus(session)

        # Apply confirmation-view edits before any approve gate so coverage/residue
        # see present_questions and enriched current_context from the UI.
        if request.confirmation_view_overrides:
            call1 = apply_confirmation_view_to_call1(
                call1, request.confirmation_view_overrides
            )
            call1 = apply_call1_runtime_gates(
                call1,
                source_text=session.raw_user_input,
                input_corpus=corpus,
                context_pack=pack,
                deep_reading_mode=mode,
            )

        block = approval_blocked_reason(call1, source_text=session.raw_user_input)
        if block:
            raise DeepReadingGenerationError(block)
        if call1.validation.material_contradiction_count > 0 or detect_material_contradictions(
            call1, source_text=session.raw_user_input
        ):
            raise DeepReadingGenerationError(
                "入力内容に矛盾があります。確認事項を直し、追加の質問に答えてから再度お進みください。"
            )
        if call1.status in {
            GenerationStatus.structural_ambiguity,
            GenerationStatus.needs_additional_input,
            GenerationStatus.insufficient_current_context,
            GenerationStatus.sensitive_domain_clarification_required,
        }:
            # Normal intermediate clarification — HTTP 200; bounded exit policy
            call1, session, exit_reason = self._apply_clarification_exit(
                session, call1, increment_round=True
            )
            if call1.status == GenerationStatus.insufficient_for_deep_reading:
                session.call1 = call1
                session.status = call1.status
                session = self._save(session)
                return self._response(
                    session, clarification_exit_reason=exit_reason
                )
            if call1.status != GenerationStatus.ready_for_user_confirmation:
                session.call1 = call1
                session.status = call1.status
                session = self._save(session)
                return self._response(session, clarification_exit_reason=exit_reason)
            # Structurally sufficient after exit — continue approve with known facts
            session.call1 = call1
            session.status = call1.status
        if not call1_residue_items(call1):
            # Keep session in clarification UX rather than hard-erroring approve
            call1 = call1.model_copy(
                update={"status": GenerationStatus.needs_additional_input}
            )
            call1, session, exit_reason = self._apply_clarification_exit(
                session, call1, increment_round=True
            )
            session.call1 = call1
            session.status = call1.status
            session = self._save(session)
            return self._response(session, clarification_exit_reason=exit_reason)

        grounded = call1.grounded_input.model_copy(update={"confirmed_by_user": True})
        call1 = call1.model_copy(
            update={
                "grounded_input": grounded,
                "status": GenerationStatus.ready_for_draft,
            }
        )
        call1 = apply_call1_runtime_gates(
            call1,
            source_text=session.raw_user_input,
            input_corpus=corpus,
            context_pack=pack,
            deep_reading_mode=mode,
        )
        # v1.0.1 / v1.1.10: hard blockers still stop; soft clarification bounce
        # after exhausted rounds must not dead-end confirm — proceed to draft.
        reblock = approval_blocked_reason(call1, source_text=session.raw_user_input)
        hard_block = bool(reblock) or (
            call1.validation.material_contradiction_count > 0
        ) or (not call1.validation.branch_concreteness_ok)
        soft_status_block = call1.status in {
            GenerationStatus.needs_additional_input,
            GenerationStatus.structural_ambiguity,
        }
        meta = dict(session.model_metadata or {})
        rounds = int(meta.get("clarification_rounds") or 0)
        clar_exit = meta.get("clarification_exit")
        proceed_known = _branch_structurally_sufficient(call1) and (
            clar_exit
            in {
                "proceed_structurally_sufficient",
                "max_rounds_proceed",
                "sufficient_for_deep_reading",
            }
            or rounds >= MAX_CLARIFICATION_ROUNDS
        )

        if hard_block or (soft_status_block and not proceed_known):
            call1 = call1.model_copy(
                update={
                    "grounded_input": call1.grounded_input.model_copy(
                        update={"confirmed_by_user": False}
                    ),
                    "status": (
                        call1.status
                        if call1.status
                        in {
                            GenerationStatus.needs_additional_input,
                            GenerationStatus.structural_ambiguity,
                        }
                        else GenerationStatus.needs_additional_input
                    ),
                }
            )
            call1, session, exit_reason = self._apply_clarification_exit(
                session, call1, increment_round=True
            )
            # Soft clarification exit only: structurally sufficient → draft on this approve.
            # Hard blocks (contradiction / concreteness / approval_blocked) never auto-draft.
            if (
                not hard_block
                and call1.status == GenerationStatus.ready_for_user_confirmation
                and _branch_structurally_sufficient(call1)
            ):
                call1 = call1.model_copy(
                    update={
                        "grounded_input": call1.grounded_input.model_copy(
                            update={"confirmed_by_user": True}
                        ),
                        "status": GenerationStatus.ready_for_draft,
                    }
                )
                meta = dict(session.model_metadata or {})
                meta["clarification_exit"] = "sufficient_for_deep_reading"
                meta["draft_progression"] = "clarification_exit_to_ready_for_draft"
                session.model_metadata = meta
            elif call1.status == GenerationStatus.insufficient_for_deep_reading:
                session.call1 = call1
                session.status = call1.status
                session = self._save(session)
                return self._response(
                    session, clarification_exit_reason=exit_reason
                )
            else:
                session.call1 = call1
                session.status = call1.status
                session = self._save(session)
                return self._response(session, clarification_exit_reason=exit_reason)
        elif soft_status_block and proceed_known:
            # Soft thesis/coverage bounce after max clarification — proceed with known facts
            call1 = call1.model_copy(
                update={
                    "grounded_input": call1.grounded_input.model_copy(
                        update={"confirmed_by_user": True}
                    ),
                    "status": GenerationStatus.ready_for_draft,
                }
            )
            meta["clarification_exit"] = "sufficient_for_deep_reading"
            meta["draft_progression"] = "soft_gate_bypass_after_clarification"
            session.model_metadata = meta

        call1 = call1.model_copy(
            update={
                "grounded_input": call1.grounded_input.model_copy(
                    update={"confirmed_by_user": True}
                ),
                "status": GenerationStatus.ready_for_draft,
            }
        )
        session.call1 = call1
        session.confirmation_timestamp = datetime.now(timezone.utc).isoformat()
        session.status = GenerationStatus.ready_for_draft
        # Minimal ops metadata (no raw content)
        meta = dict(session.model_metadata or {})
        meta["runtime_version"] = meta.get("runtime_validation_version")
        meta["final_status"] = session.status.value
        meta["clarification_count"] = len(
            call1.additional_questions.questions or []
        )
        meta["failure_category"] = None
        if meta.get("clarification_exit") in {
            "proceed_structurally_sufficient",
            "max_rounds_proceed",
        }:
            meta["clarification_exit"] = "sufficient_for_deep_reading"
        session.model_metadata = meta
        session = self._save(session)
        return self._response(session)

    def draft(
        self,
        session_id: str,
        *,
        inject_draft: Any = None,
        idempotency_key: str | None = None,
    ) -> DeepReadingSessionResponse:
        session = self.store.get(session_id)
        if not session or not session.call1:
            raise KeyError("session_not_found")
        if not session.call1.grounded_input.confirmed_by_user:
            raise DeepReadingGenerationError(
                "Call 2 rejected: grounded_input.confirmed_by_user must be true."
            )
        keys = dict(session.idempotency_keys or {})
        if idempotency_key and keys.get(f"draft:{idempotency_key}") == "complete" and session.call2:
            return self._response(session)
        if session.draft_attempt_count >= MAX_DRAFT_ATTEMPTS:
            raise DeepReadingGenerationError("下書き再試行の上限に達しました。")

        session.draft_attempt_count += 1
        session.generation_attempt_count += 1
        session.status = GenerationStatus.ready_for_draft
        session = self._save(session)

        try:
            if inject_draft is not None:
                draft = parse_call2_payload(inject_draft, session.call1) if isinstance(
                    inject_draft, dict
                ) else inject_draft
            else:
                draft = run_call2_draft(session.call1)
        except DeepReadingLLMRequiredError:
            raise
        except DeepReadingGenerationError:
            session.status = GenerationStatus.editorial_failure
            session = self._save(session)
            raise

        session.call2 = draft
        session.status = GenerationStatus.draft_generated
        from app.parallel_life_deep_reading.production_models import CALL_2_MODEL

        meta = dict(session.model_metadata or {})
        meta["call_2_model"] = CALL_2_MODEL
        meta["call_2_prompt_version"] = draft.prompt_version
        session.model_metadata = meta
        if idempotency_key:
            keys = dict(session.idempotency_keys or {})
            keys[f"draft:{idempotency_key}"] = "complete"
            session.idempotency_keys = keys
        session = self._save(session)
        return self._response(session)

    def edit_validate(
        self,
        session_id: str,
        *,
        inject_call3: Any = None,
        idempotency_key: str | None = None,
    ) -> DeepReadingSessionResponse:
        session = self.store.get(session_id)
        if not session or not session.call1 or not session.call2:
            raise KeyError("session_not_found")
        if not session.call1.grounded_input.confirmed_by_user:
            raise DeepReadingGenerationError(
                "Call 3 rejected: grounded_input.confirmed_by_user must be true."
            )
        keys = dict(session.idempotency_keys or {})
        if (
            idempotency_key
            and keys.get(f"edit:{idempotency_key}") == "complete"
            and session.call3
        ):
            return self._response(session, include_diagnostics=True)
        if session.edit_attempt_count >= MAX_EDIT_ATTEMPTS:
            raise DeepReadingGenerationError("編集検証の再試行上限に達しました。")

        session.edit_attempt_count += 1
        session.generation_attempt_count += 1
        session = self._save(session)

        try:
            if inject_call3 is not None:
                call3 = inject_call3
            else:
                call3 = run_call3_edit_validate(session.call1, session.call2)
        except DeepReadingLLMRequiredError:
            raise
        except DeepReadingGenerationError:
            session.status = GenerationStatus.editorial_failure
            session = self._save(session)
            raise

        session.call3 = call3
        from app.parallel_life_deep_reading import SCHEMA_VERSION
        from app.parallel_life_deep_reading.production_models import CALL_3_MODEL

        meta = dict(session.model_metadata or {})
        meta["call_3_model"] = CALL_3_MODEL
        meta["call_3_prompt_version"] = call3.prompt_version
        meta["runtime_validation_version"] = SCHEMA_VERSION
        session.model_metadata = meta
        if call3.validation.publishable and call3.status == GenerationStatus.complete:
            session.final_manuscript = (
                f"# {call3.final_title}\n\n"
                + (f"*{call3.final_subtitle}*\n\n" if call3.final_subtitle else "")
                + call3.body_markdown
            )
            session.status = GenerationStatus.complete
        else:
            session.status = GenerationStatus.validation_failed
        if idempotency_key:
            keys = dict(session.idempotency_keys or {})
            keys[f"edit:{idempotency_key}"] = "complete"
            session.idempotency_keys = keys
        session = self._save(session)
        return self._response(session, include_diagnostics=True)

    def get_session(self, session_id: str) -> DeepReadingSessionResponse:
        session = self.store.get(session_id)
        if not session:
            raise KeyError("session_not_found")
        return self._response(session, include_diagnostics=True)

    def regenerate(
        self,
        session_id: str,
        from_stage: str = "draft",
    ) -> DeepReadingSessionResponse:
        session = self.store.get(session_id)
        if not session:
            raise KeyError("session_not_found")

        if from_stage == "ground":
            req = DeepReadingGroundRequest(
                source_text=session.raw_user_input,
                clarifications=session.clarifications,
                editorial_context=session.editorial_context,
                language=session.language,
            )
            # New session id to prevent stale reuse
            return self.ground(req)

        if from_stage == "draft":
            if not session.call1 or not session.call1.grounded_input.confirmed_by_user:
                raise DeepReadingGenerationError("確認済みセッションが必要です。")
            session.call2 = None
            session.call3 = None
            session.final_manuscript = None
            session = self._save(session)
            return self.draft(session_id)

        if from_stage == "edit-validate":
            if not session.call2:
                raise DeepReadingGenerationError("下書きがありません。")
            session.call3 = None
            session.final_manuscript = None
            session = self._save(session)
            return self.edit_validate(session_id)

        raise DeepReadingGenerationError(f"unknown from_stage: {from_stage}")

    def export(self, session_id: str, *, include_diagnostics: bool = False) -> str:
        session = self.store.get(session_id)
        if not session or not session.call3:
            raise KeyError("session_not_found")
        if session.status != GenerationStatus.complete and not session.final_manuscript:
            raise DeepReadingGenerationError("完成または保存済みの原稿のみエクスポートできます。")
        meta = {
            "generated_at": session.updated_at,
            "prompt_version": ",".join(
                f"{k}:{v}" for k, v in (session.prompt_versions or {}).items()
            ),
            "validation_status": session.call3.validation.publishable,
            "schema_version": session.schema_version,
        }
        return export_markdown(
            session.call3,
            metadata=meta,
            include_diagnostics=include_diagnostics,
        )


_SERVICE: DeepReadingService | None = None


def get_deep_reading_service() -> DeepReadingService:
    global _SERVICE
    if _SERVICE is None:
        _SERVICE = DeepReadingService()
    return _SERVICE
