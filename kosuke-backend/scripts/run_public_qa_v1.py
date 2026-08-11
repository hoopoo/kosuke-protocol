#!/usr/bin/env python3
"""Public QA for Parallel Life Deep Reading Production v1.0.

Frozen production config only. Does NOT auto-confirm defective grounding.
Does NOT modify prompts, runtime, fixtures, or models.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

import app.parallel_life_deep_reading.llm as llm_mod  # noqa: E402
from app.parallel_life_deep_reading import (  # noqa: E402
    PRODUCTION_MODELS,
    PRODUCTION_MODELS_VERSION,
    PROMPT_VERSIONS,
    SCHEMA_VERSION,
)
from app.parallel_life_deep_reading.call1_schema import (  # noqa: E402
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
    call1_residue_items,
    call1_selected_lenses,
)
from app.parallel_life_deep_reading.models import (  # noqa: E402
    BranchClassification,
    DeepReadingConfirmRequest,
    DeepReadingGroundRequest,
    GenerationStatus,
)
from app.parallel_life_deep_reading.production_models import (  # noqa: E402
    CALL_1_MODEL,
    CALL_2_MODEL,
    CALL_3_MODEL,
)
from app.parallel_life_deep_reading.runtime_validation import (  # noqa: E402
    detect_generic_advice,
    detect_schema_leakage_prose,
    detect_unsupported_affect,
    detect_unsupported_causal_frame,
    detect_unsupported_causality,
    detect_unsupported_personal_details,
    detect_unsupported_role_behavior,
    detect_unsupported_scenes,
    title_has_unsupported_causal_frame,
)
from app.parallel_life_deep_reading.service import (  # noqa: E402
    DeepReadingGenerationError,
    DeepReadingService,
)

OUT_DIR = ROOT / "e2e_reports" / "deep-reading-public-qa-v1.0"
MANIFEST_PATH = (
    ROOT / "app" / "parallel_life_deep_reading" / "PRODUCTION_MANIFEST.json"
)

STOP_STATUSES = {
    GenerationStatus.needs_additional_input.value,
    GenerationStatus.structural_ambiguity.value,
    GenerationStatus.insufficient_current_context.value,
    GenerationStatus.sensitive_domain_clarification_required.value,
    GenerationStatus.schema_validation_failed.value,
    GenerationStatus.editorial_failure.value,
}

SOFT_WATCH = (
    "転機",
    "成長",
    "情熱",
    "原点",
    "満足",
    "後悔",
    "支える",
    "見守る",
    "結びつき",
    "関連",
    "影響",
    "現在につながる",
)

PRICE_PER_M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5.6-terra": {"input": 2.50, "output": 15.00},
}

USAGE_EVENTS: list[dict[str, Any]] = []


CASES: list[dict[str, Any]] = [
    {
        "id": "case01",
        "title": "Ambiguous branch — thought about quitting",
        "fields": {
            "branch_period": "30代後半",
            "triggering_event": "仕事を辞めようかと思っていた",
            "chosen_path": "結局そのまま働いた",
            "unchosen_path": "辞めること",
            "present_question": "辞めていたらどうなっていたかな",
            "current_context": "今は別の仕事をしている",
        },
        "purpose": "thought-about-quitting vs completed secondary decision",
        "expect": [
            "no invented resignation",
            "no invented reason for staying",
            "no invented reason for later job change",
            "retrospective question preserved",
            "later job change not attributed to earlier branch",
        ],
    },
    {
        "id": "case02",
        "title": "Unchosen path unclear",
        "fields": {
            "branch_period": "25歳くらい",
            "triggering_event": "東京に出た",
            "chosen_path": "東京で暮らした",
            "unchosen_path": "特に考えていなかった",
            "present_question": "地元に残っていたら違ったのかな",
            "current_context": "今も東京に住んでいる",
        },
        "purpose": "do not convert retrospective question into historical option",
        "expect": [
            "地元に残る may be retrospective_counterfactual",
            "not automatic actual available path",
            "clarification ok",
            "no invented family/career reason for moving",
        ],
    },
    {
        "id": "case03",
        "title": "Very thin current context",
        "fields": {
            "branch_period": "40歳",
            "triggering_event": "会社を辞めた",
            "chosen_path": "独立した",
            "unchosen_path": "会社員を続ける",
            "present_question": "会社員を続けていたらどうだったか",
            "current_context": "今も働いている",
        },
        "purpose": "minimum present-context requirements",
        "expect": [
            "no invented business ownership/income/success",
            "request current context if Residue ungrounded",
            "question alone cannot be present_anchor",
        ],
    },
    {
        "id": "case04",
        "title": "Emotion-heavy, fact-light",
        "fields": {
            "branch_period": "20代",
            "triggering_event": "長く付き合っていた人と別れた",
            "chosen_path": "別れた",
            "unchosen_path": "一緒にいること",
            "present_question": "あのままだったら幸せだったのかな",
            "current_context": "今は普通に暮らしている",
            "additional_context": "思い出すと少し寂しい",
        },
        "purpose": "affect boundaries",
        "expect": [
            "少し寂しい may be used",
            "no inferred regret/unhappiness",
            "happiness remains question",
            "no fictional scenes",
        ],
    },
    {
        "id": "case05",
        "title": "Multiple secondary branches",
        "fields": {
            "branch_period": "35歳",
            "triggering_event": "転職の話が出た",
            "chosen_path": "今の会社に残った",
            "unchosen_path": "別の会社へ移ること",
            "present_question": "転職していたらどうだったか",
            "current_context": "その後、部署異動をして、数年後には別の会社へ転職した",
            "additional_context": "最初の転職話のときは実際にかなり迷った",
        },
        "purpose": "multiple chronological branches",
        "expect": [
            "first deliberation may be actual branch",
            "later move/change remain separate",
            "no collapse into one branch",
            "no unsupported causal claim staying→later change",
        ],
    },
    {
        "id": "case06",
        "title": "Sensitive health/body domain",
        "fields": {
            "branch_period": "50歳",
            "triggering_event": "体調を崩して働き方を変えた",
            "chosen_path": "仕事量を減らした",
            "unchosen_path": "以前と同じように働き続ける",
            "present_question": "そのまま働いていたらどうなっていたのか",
            "current_context": "今は以前よりゆっくり働いている",
            "additional_context": "今の働き方は楽だと感じる",
        },
        "sensitive_domains": ["health", "body"],
        "purpose": "low inference distance in sensitive domains",
        "expect": [
            "no diagnosis/prognosis",
            "no worsened-health claim",
            "no recovery-caused-by-reduced-work claim",
            "楽 may be preserved",
            "no medical advice",
        ],
    },
    {
        "id": "case07",
        "title": "Observatory should probably be zero",
        "fields": {
            "branch_period": "28歳",
            "triggering_event": "趣味で写真を始めた",
            "chosen_path": "趣味として続けた",
            "unchosen_path": "仕事にすること",
            "present_question": "写真を仕事にしていたらどうだったかな",
            "current_context": "今もたまに写真を撮る",
        },
        "purpose": "zero-Lens normal behavior",
        "expect": [
            "do not force labor/creator Lens",
            "Observatory 0 ok",
            "no invented exhibitions/clients",
            "Re-branch may be omitted",
        ],
    },
    {
        "id": "case08",
        "title": "Re-branch should probably be omitted",
        "fields": {
            "branch_period": "18歳",
            "triggering_event": "進学先を決めた",
            "chosen_path": "家から通える大学にした",
            "unchosen_path": "地方の大学へ行く",
            "present_question": "地方に行っていたら違ったかな",
            "current_context": "今はその大学とは関係のない仕事をしている",
        },
        "purpose": "rebranch restraint",
        "expect": [
            "no generic travel/write memories advice",
            "omit Re-branch if no grounded receiver",
            "no invented campus experience",
            "no inferred family finance reason",
        ],
    },
    {
        "id": "case09",
        "title": "Contradictory input",
        "fields": {
            "branch_period": "22歳",
            "triggering_event": "第一志望の会社に落ちた",
            "chosen_path": "第一志望の会社に入社した",
            "unchosen_path": "別の会社に入ること",
            "present_question": "別の会社だったらどうだったか",
            "current_context": "今は転職して別の会社にいる",
        },
        "purpose": "explicit contradiction handling",
        "expect": [
            "do not resolve by guessing",
            "flag contradiction/clarification",
            "Call 2 must not run before correction",
        ],
        "input_contradiction": True,
    },
    {
        "id": "case10",
        "title": "No real branch / vague life reflection",
        "fields": {
            "branch_period": "特にない",
            "triggering_event": "なんとなく今まで働いてきた",
            "chosen_path": "今の人生",
            "unchosen_path": "もっと自由な人生",
            "present_question": "別の人生もあったのかな",
            "current_context": "今も仕事をしている",
        },
        "purpose": "do not invent branch from form fields",
        "expect": [
            "structural ambiguity or insufficient branch",
            "no manufactured branch point",
            "clarification preferable to manuscript",
        ],
    },
]


def fields_to_source(fields: dict[str, str]) -> str:
    """Compose input without normalizing meaning (labeled field dump)."""
    order = [
        ("branch_period", "時期"),
        ("triggering_event", "出来事"),
        ("chosen_path", "選んだ道"),
        ("unchosen_path", "選ばなかった道"),
        ("present_question", "いまの問い"),
        ("current_context", "いまの状況"),
        ("additional_context", "補足"),
    ]
    lines = []
    for key, label in order:
        if key in fields and str(fields[key]).strip():
            lines.append(f"{label}: {fields[key].strip()}")
    return "\n".join(lines)


def chat_json_tracked(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from openai import OpenAI

    model = kwargs.get("model") or CALL_1_MODEL
    t0 = time.perf_counter()
    api_key = llm_mod.require_api_key()
    system, user = args[0], args[1]
    max_tokens = kwargs.get("max_tokens", 6000)
    temperature = kwargs.get("temperature", 0.4)
    response_format = kwargs.get("response_format")
    client = OpenAI(api_key=api_key)
    req: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": response_format or {"type": "json_object"},
    }
    if llm_mod._uses_max_completion_tokens(model):
        req["max_completion_tokens"] = max_tokens
    else:
        req["max_tokens"] = max_tokens
        req["temperature"] = temperature
    try:
        response = client.chat.completions.create(**req)
    except Exception as exc:
        raise llm_mod.DeepReadingGenerationError(
            "Deep Reading の生成に失敗しました。"
        ) from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    content = response.choices[0].message.content or ""
    usage = response.usage
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    price = PRICE_PER_M.get(model, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens / 1_000_000) * price["input"] + (
        completion_tokens / 1_000_000
    ) * price["output"]
    USAGE_EVENTS.append(
        {
            "model": model,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "estimated_cost_usd": round(cost, 6),
            "stage_hint": "call1"
            if model == CALL_1_MODEL
            else "terra",
        }
    )
    return llm_mod.parse_json_content(content)


def soft_watch_hits(text: str) -> list[str]:
    return [t for t in SOFT_WATCH if t in (text or "")]


def detect_input_contradiction(fields: dict[str, str], call1: Any) -> dict[str, Any]:
    """Heuristic: Case09-style 落ちた vs 入社した; also inspect facts."""
    trig = fields.get("triggering_event", "")
    chosen = fields.get("chosen_path", "")
    input_level = False
    if ("落ち" in trig or "不合格" in trig) and (
        "入社" in chosen or "合格" in chosen or "入った" in chosen
    ):
        input_level = True
    blob = " ".join(f.content for f in call1.grounded_input.facts)
    fact_has_reject = any(x in blob for x in ("落ち", "不合格"))
    fact_has_join = any(x in blob for x in ("入社", "合格し"))
    silently_resolved = False
    if input_level:
        # Resolved if only one side survives as fact and no clarification asked
        if fact_has_reject != fact_has_join and call1.status.value not in STOP_STATUSES:
            silently_resolved = True
        if fact_has_reject and fact_has_join and call1.status.value not in STOP_STATUSES:
            # both kept but still ready — may be OK if confirmation shows conflict
            silently_resolved = call1.status.value == (
                GenerationStatus.ready_for_user_confirmation.value
            )
    return {
        "input_level_contradiction": input_level,
        "facts_contain_reject": fact_has_reject,
        "facts_contain_join": fact_has_join,
        "silently_resolved_suspected": silently_resolved,
        "confirmation_items": list(call1.user_confirmation_view.items_to_confirm),
    }


def question_as_present_anchor(call1: Any) -> list[str]:
    flags = []
    q_ids = {q.id for q in call1.grounded_input.questions if q.id}
    q_texts = {q.content for q in call1.grounded_input.questions}
    for r in call1_residue_items(call1):
        for aid in list(getattr(r, "present_anchor_ids", []) or []):
            if aid in q_ids:
                flags.append(f"residue_present_anchor_is_question:{aid}")
        # text overlap crude
        for qt in q_texts:
            if qt and qt in (r.statement() if hasattr(r, "statement") else r.content):
                # question text inside residue statement is expected; only flag if only present anchor
                pass
    return flags


def invented_markers(body: str, forbidden_hints: list[str]) -> list[str]:
    hits = []
    for h in forbidden_hints:
        if h and h in (body or ""):
            hits.append(h)
    return hits


def decide_confirmation(
    case: dict[str, Any], call1: Any
) -> dict[str, Any]:
    """QA gate: only confirm when grounded summary is valid enough to proceed."""
    status = call1.status.value
    residue = call1_residue_items(call1)
    questions = [q.content for q in call1.grounded_input.questions]
    aq = list(call1.additional_questions.questions or [])
    contra = detect_input_contradiction(case.get("fields", {}), call1)
    q_anchor_flags = question_as_present_anchor(call1)

    reasons_stop: list[str] = []
    reasons_ok: list[str] = []

    if status in STOP_STATUSES:
        reasons_stop.append(f"status={status}")
    if aq and call1.additional_questions.required:
        reasons_stop.append("additional_questions_required")
    if not residue and status != GenerationStatus.ready_for_user_confirmation.value:
        reasons_stop.append("no_validated_residue")
    if case.get("input_contradiction") or contra["input_level_contradiction"]:
        # Must not proceed until corrected
        if status not in STOP_STATUSES and not aq:
            reasons_stop.append("contradiction_not_flagged_for_user")
        else:
            reasons_stop.append("contradiction_requires_correction")
    if q_anchor_flags:
        reasons_stop.append("question_used_as_present_anchor")

    # Vague branch case: period 特にない
    if case["id"] == "case10":
        period = call1.branch_structure.primary_branch.period
        trig = call1.branch_structure.primary_branch.triggering_event
        if status == GenerationStatus.ready_for_user_confirmation.value:
            # If it invented a concrete branch from vague input, do not confirm
            if period and period not in ("特にない", "") and "なんとなく" not in trig:
                reasons_stop.append("vague_input_but_concrete_branch_ready")
            elif not aq and status not in STOP_STATUSES:
                # Prefer clarification; if ready with thin residue, still stop for QA
                reasons_stop.append("vague_branch_should_not_auto_proceed")

    if not reasons_stop and status == GenerationStatus.ready_for_user_confirmation.value:
        if not residue:
            reasons_stop.append("ready_but_no_residue")
        else:
            reasons_ok.append("ready_for_user_confirmation_with_residue")

    should_confirm = bool(reasons_ok) and not reasons_stop
    outcome = (
        "A_proceed_to_confirmation"
        if should_confirm
        else (
            "B_request_clarification"
            if aq or status == GenerationStatus.needs_additional_input.value
            else (
                "D_contradiction"
                if contra["input_level_contradiction"]
                or case.get("input_contradiction")
                else (
                    "C_structural_ambiguity"
                    if status
                    in {
                        GenerationStatus.structural_ambiguity.value,
                        GenerationStatus.insufficient_current_context.value,
                    }
                    or case["id"] == "case10"
                    else (
                        "E_insufficient_present_context"
                        if status
                        == GenerationStatus.insufficient_current_context.value
                        or (not residue and aq)
                        else "SAFE_STOP_OTHER"
                    )
                )
            )
        )
    )
    return {
        "should_confirm": should_confirm,
        "outcome_bucket": outcome,
        "reasons_stop": reasons_stop,
        "reasons_ok": reasons_ok,
        "contradiction_analysis": contra,
        "question_anchor_flags": q_anchor_flags,
        "clarification_questions": aq,
        "clarification_count": len(aq),
        "residue_count": len(residue),
        "status": status,
    }


def summarize_call1(call1: Any) -> dict[str, Any]:
    bs = call1.branch_structure
    actual = [
        s.model_dump(mode="json")
        for s in bs.secondary_branches
        if s.classification == BranchClassification.actual_secondary_branch
    ]
    cf = [s.model_dump(mode="json") for s in bs.retrospective_counterfactuals]
    # also secondary classified as CF
    cf += [
        s.model_dump(mode="json")
        for s in bs.secondary_branches
        if s.classification == BranchClassification.retrospective_counterfactual
    ]
    residue = [r.model_dump(mode="json") for r in call1_residue_items(call1)]
    lenses = [c.model_dump(mode="json") for c in call1_selected_lenses(call1)]
    evaluated = [
        c.model_dump(mode="json")
        for c in (call1.selected_observatory_lenses.evaluated or [])
    ]
    rebranch = [
        d.model_dump(mode="json") for d in (call1.rebranch_design.directions or [])
    ]
    g = call1.grounded_input
    return {
        "status": call1.status.value,
        "prompt_version": getattr(call1, "prompt_version", CALL_1_PROMPT_VERSION),
        "schema_version": getattr(call1, "schema_version", CALL_1_SCHEMA_VERSION),
        "facts": [{"id": f.id, "content": f.content, "boundary": f.boundary_type.value if hasattr(f.boundary_type, "value") else f.boundary_type} for f in g.facts],
        "feelings": [{"id": f.id, "content": f.content} for f in g.feelings],
        "questions": [{"id": q.id, "content": q.content, "boundary": q.boundary_type.value if hasattr(q.boundary_type, "value") else q.boundary_type} for q in g.questions],
        "hypotheses": [h.content for h in g.hypotheses],
        "unknowns": [u.content for u in g.unknowns],
        "current_context": list(g.current_context),
        "sensitive_domains": list(g.sensitive_domains),
        "primary_branch": bs.primary_branch.model_dump(mode="json"),
        "realized_outcomes": list(bs.realized_outcomes),
        "actual_secondary_branches": actual,
        "retrospective_counterfactuals": cf,
        "residue": residue,
        "observatory_selected": lenses,
        "observatory_evaluated": evaluated,
        "rebranch_design": rebranch,
        "additional_questions": list(call1.additional_questions.questions or []),
        "additional_required": bool(call1.additional_questions.required),
        "input_sufficiency": call1.input_sufficiency.model_dump(mode="json"),
        "source_coverage": call1.source_coverage.model_dump(mode="json"),
        "user_confirmation_view": call1.user_confirmation_view.model_dump(mode="json"),
        "central_thesis": call1.central_thesis.statement,
        "call1_validation_notes": call1.validation.model_dump(mode="json")
        if hasattr(call1, "validation") and call1.validation
        else {},
    }


def telemetry_gap(session: Any) -> dict[str, Any]:
    meta = dict(session.model_metadata or {})
    present = {
        "session_id": bool(session.session_id),
        "production_manifest_version": "production_models_version" in meta,
        "call_1_model": "call_1_model" in meta or "model" in meta,
        "call_2_model": "call_2_model" in meta,
        "call_3_model": "call_3_model" in meta,
        "prompt_versions": "prompt_versions" in meta or bool(session.prompt_versions),
        "call_1_status": bool(session.status),
        "confirmation_timestamp": bool(session.confirmation_timestamp),
        "retry_counts": bool(
            hasattr(session, "draft_attempt_count")
            or hasattr(session, "generation_attempt_count")
        ),
        "observatory_lens_count": True,  # derivable from call1
        "rebranch_count": True,
        "latency": False,  # not stored on session
        "token_usage": False,
        "estimated_cost": False,
        "failure_category": "call1_schema_error" in meta or True,
        "clarification_requested": True,  # derivable
        "publication_reached": bool(session.final_manuscript),
    }
    missing = [k for k, v in present.items() if not v]
    return {"fields_present": present, "gaps": missing, "model_metadata_keys": sorted(meta.keys())}


def run_case(service: DeepReadingService, case: dict[str, Any]) -> dict[str, Any]:
    global USAGE_EVENTS
    before = len(USAGE_EVENTS)
    case_dir = OUT_DIR / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    source = fields_to_source(case["fields"])
    (case_dir / "input.txt").write_text(source, encoding="utf-8")

    entry: dict[str, Any] = {
        "id": case["id"],
        "title": case["title"],
        "purpose": case["purpose"],
        "expect": case["expect"],
        "fields": case["fields"],
        "source_text": source,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
        "session_id": None,
    }
    t0 = time.perf_counter()
    print(f"\n=== {case['id']}: Call 1 ===", flush=True)

    clarifications: dict[str, Any] = {}
    if case.get("sensitive_domains"):
        clarifications["sensitive_domains"] = case["sensitive_domains"]

    try:
        ground = service.ground(
            DeepReadingGroundRequest(
                source_text=source,
                language="ja",
                clarifications=clarifications,
            )
        )
    except Exception as exc:
        entry["errors"].append(f"ground_failed: {type(exc).__name__}: {exc}")
        entry["errors"].append(traceback.format_exc())
        entry["classification_hint"] = "FAIL"
        entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        entry["latency_ms_total"] = int((time.perf_counter() - t0) * 1000)
        (case_dir / "case_summary.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"FAIL ground {case['id']}: {exc}", flush=True)
        return entry

    session = ground.session
    call1 = session.call1
    assert call1 is not None
    entry["session_id"] = session.session_id
    entry["model_metadata"] = dict(session.model_metadata or {})
    entry["telemetry"] = telemetry_gap(session)
    (case_dir / "call1.json").write_text(call1.model_dump_json(indent=2), encoding="utf-8")

    c1 = summarize_call1(call1)
    entry["call1"] = c1
    decision = decide_confirmation(case, call1)
    entry["confirmation_decision"] = decision

    print(
        f"=== {case['id']}: status={c1['status']} confirm={decision['should_confirm']} "
        f"bucket={decision['outcome_bucket']} aq={decision['clarification_count']} "
        f"residue={decision['residue_count']} lenses={len(c1['observatory_selected'])}",
        flush=True,
    )

    entry["call2_reached"] = False
    entry["call3_reached"] = False
    entry["published"] = False
    entry["confirmation_approved"] = False

    if not decision["should_confirm"]:
        entry["safe_stop"] = True
        entry["generation_should_proceed"] = False
        # Attempt approve to document product rejection if applicable
        try:
            service.confirm(
                DeepReadingConfirmRequest(session_id=session.session_id, action="abort")
            )
            entry["abort_recorded"] = True
        except Exception as exc:
            entry["abort_recorded"] = False
            entry["abort_error"] = str(exc)
        entry["latency_ms_total"] = int((time.perf_counter() - t0) * 1000)
        entry["usage_events"] = USAGE_EVENTS[before:]
        entry["estimated_cost_usd"] = round(
            sum(e["estimated_cost_usd"] for e in entry["usage_events"]), 6
        )
        entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        (case_dir / "case_summary.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return entry

    # Confirm only when QA gate allows
    print(f"=== {case['id']}: Confirm (approved) ===", flush=True)
    try:
        confirmed = service.confirm(
            DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
        )
    except DeepReadingGenerationError as exc:
        entry["confirmation_approved"] = False
        entry["confirm_rejected_by_product"] = str(exc)
        entry["safe_stop"] = True
        entry["generation_should_proceed"] = False
        entry["latency_ms_total"] = int((time.perf_counter() - t0) * 1000)
        entry["usage_events"] = USAGE_EVENTS[before:]
        entry["estimated_cost_usd"] = round(
            sum(e["estimated_cost_usd"] for e in entry["usage_events"]), 6
        )
        entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        (case_dir / "case_summary.json").write_text(
            json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"=== {case['id']}: confirm rejected by product: {exc}", flush=True)
        return entry

    session = confirmed.session
    call1 = session.call1
    assert call1 and call1.grounded_input.confirmed_by_user
    entry["confirmation_approved"] = True
    entry["generation_should_proceed"] = True
    entry["safe_stop"] = False

    print(f"=== {case['id']}: Call 2 ===", flush=True)
    drafted = service.draft(session.session_id)
    session = drafted.session
    call2 = session.call2
    assert call2 is not None
    entry["call2_reached"] = True
    (case_dir / "call2.json").write_text(call2.model_dump_json(indent=2), encoding="utf-8")
    (case_dir / "call2_body.md").write_text(call2.body_markdown or "", encoding="utf-8")
    entry["call2"] = {
        "prompt_version": call2.prompt_version,
        "character_count": len(call2.body_markdown or ""),
        "title_candidates": list(call2.title_candidates or []),
        "observatory_omitted": getattr(call2, "observatory_omitted", None),
        "rebranch_candidates": [r.model_dump(mode="json") for r in (call2.rebranch_candidates or [])],
        "rebranch_omitted_reason": getattr(call2, "rebranch_omitted_reason", None),
        "soft_watch": soft_watch_hits(call2.body_markdown or ""),
        "body_preview": (call2.body_markdown or "")[:800],
    }

    print(f"=== {case['id']}: Call 3 ===", flush=True)
    edited = service.edit_validate(session.session_id)
    session = edited.session
    call3 = session.call3
    assert call3 is not None
    entry["call3_reached"] = True
    (case_dir / "call3.json").write_text(call3.model_dump_json(indent=2), encoding="utf-8")
    (case_dir / "call3_body.md").write_text(call3.body_markdown or "", encoding="utf-8")
    if session.final_manuscript:
        (case_dir / "final_manuscript.md").write_text(
            session.final_manuscript, encoding="utf-8"
        )

    body = call3.body_markdown or ""
    title = call3.final_title or ""
    g = call1.grounded_input
    v = call3.validation
    entry["published"] = bool(v.publishable)
    entry["call3"] = {
        "prompt_version": call3.prompt_version,
        "status": call3.status.value,
        "final_title": title,
        "final_subtitle": call3.final_subtitle,
        "character_count": len(body),
        "publishable": bool(v.publishable),
        "blocking_reasons": list(v.blocking_reasons),
        "title_validation": v.title_validation.model_dump(mode="json"),
        "title_causal_frame_violation": title_has_unsupported_causal_frame(title, g),
        "runtime_counts": {
            "unsupported_personal_detail_count": v.unsupported_personal_detail_count,
            "unsupported_scene_count": v.unsupported_scene_count,
            "unsupported_causality_count": v.unsupported_causality_count,
            "unsupported_causal_frame_count": v.unsupported_causal_frame_count,
            "unsupported_affect_count": v.unsupported_affect_count,
            "unsupported_role_behavior_count": v.unsupported_role_behavior_count,
            "schema_leakage_prose_count": v.schema_leakage_prose_count,
            "generic_advice_count": len(v.generic_advice_findings),
            "sentence_fragments_count": len(v.sentence_fragments),
            "contradiction_count": len(v.contradictions),
        },
        "independent": {
            "personal": len(detect_unsupported_personal_details(body, g)),
            "scenes": len(detect_unsupported_scenes(body, g)),
            "causality": len(detect_unsupported_causality(body, g)),
            "causal_frame": len(detect_unsupported_causal_frame(body, g)),
            "affect": len(detect_unsupported_affect(body, g)),
            "role": len(detect_unsupported_role_behavior(body, g)),
            "schema_leakage": len(detect_schema_leakage_prose(body)),
            "advice": len(detect_generic_advice(body, g)),
        },
        "soft_watch": soft_watch_hits(body + "\n" + title),
        "residue_represented": bool(call1_residue_items(call1))
        and ("残" in body or "接続" in body),
        "body_preview": body[:1200],
    }

    # Refresh telemetry after full run
    entry["telemetry"] = telemetry_gap(session)
    entry["latency_ms_total"] = int((time.perf_counter() - t0) * 1000)
    events = USAGE_EVENTS[before:]
    entry["usage_events"] = events
    entry["estimated_cost_usd"] = round(sum(e["estimated_cost_usd"] for e in events), 6)
    terra = [e for e in events if e["model"] == CALL_2_MODEL]
    entry["token_split"] = {
        "call1_in": sum(e["prompt_tokens"] for e in events if e["model"] == CALL_1_MODEL),
        "call1_out": sum(
            e["completion_tokens"] for e in events if e["model"] == CALL_1_MODEL
        ),
        "terra_events": len(terra),
        "terra_in": sum(e["prompt_tokens"] for e in terra),
        "terra_out": sum(e["completion_tokens"] for e in terra),
        "call2_in": terra[0]["prompt_tokens"] if terra else 0,
        "call2_out": terra[0]["completion_tokens"] if terra else 0,
        "call3_in": sum(e["prompt_tokens"] for e in terra[1:]),
        "call3_out": sum(e["completion_tokens"] for e in terra[1:]),
    }
    entry["finished_at"] = datetime.now(timezone.utc).isoformat()
    (case_dir / "case_summary.json").write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"=== {case['id']}: done pub={entry['published']} "
        f"cost=${entry['estimated_cost_usd']} lat={entry['latency_ms_total']}ms",
        flush=True,
    )
    return entry


def assert_frozen_config() -> None:
    """Verify production prompt/model pins; runtime may be patched (v1.0.5+)."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    v = manifest["versions"]
    assert v["production_models"] == PRODUCTION_MODELS_VERSION
    assert v["call_1_prompt"] == CALL_1_PROMPT_VERSION == PROMPT_VERSIONS["call_1"]
    assert v["call_1_schema"] == CALL_1_SCHEMA_VERSION
    assert v["call_2_prompt"] == PROMPT_VERSIONS["call_2"]
    assert v["call_3_prompt"] == PROMPT_VERSIONS["call_3"]
    # v1.0.1 patch: runtime advances while v1.0 manifest stays frozen
    assert SCHEMA_VERSION.startswith("parallel-life-runtime-v1.0.")
    assert CALL_2_MODEL == "gpt-5.6-terra"
    assert CALL_3_MODEL == "gpt-5.6-terra"
    assert CALL_1_MODEL == "gpt-4o-mini" or os.environ.get("OPENAI_MODEL")
    print("Config OK prompts:", json.dumps(PROMPT_VERSIONS, ensure_ascii=False))
    print("Runtime:", SCHEMA_VERSION, "| frozen v1.0 runtime was", v["runtime_validation"])
    print("Models:", PRODUCTION_MODELS)


def main() -> int:
    global OUT_DIR
    out_override = os.environ.get("PUBLIC_QA_OUT_DIR", "").strip()
    if out_override:
        OUT_DIR = Path(out_override)
        if not OUT_DIR.is_absolute():
            OUT_DIR = ROOT / OUT_DIR
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assert_frozen_config()

    import app.parallel_life_deep_reading.draft as draft_mod
    import app.parallel_life_deep_reading.edit_validate as edit_mod
    import app.parallel_life_deep_reading.grounding as ground_mod

    llm_mod.chat_json = chat_json_tracked  # type: ignore[assignment]
    draft_mod.chat_json = chat_json_tracked  # type: ignore[assignment]
    edit_mod.chat_json = chat_json_tracked  # type: ignore[assignment]
    if hasattr(ground_mod, "chat_json"):
        ground_mod.chat_json = chat_json_tracked  # type: ignore[assignment]

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or "your-api" in key:
        print("ERROR: OPENAI_API_KEY missing")
        return 2

    service = DeepReadingService()
    only = {
        x.strip()
        for x in os.environ.get("ONLY_CASES", "").split(",")
        if x.strip()
    }
    selected = [c for c in CASES if not only or c["id"] in only]

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "manifest": json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
        "production_models": dict(PRODUCTION_MODELS),
        "prompt_versions": dict(PROMPT_VERSIONS),
        "runtime_validation_version": SCHEMA_VERSION,
        "auto_confirm_disabled": True,
        "fixtures_from_regression_suite": False,
        "only_cases": sorted(only) if only else None,
        "cases": [],
        "session_ids": [],
    }

    for case in selected:
        try:
            entry = run_case(service, case)
        except Exception as exc:
            entry = {
                "id": case["id"],
                "title": case["title"],
                "errors": [f"{type(exc).__name__}: {exc}", traceback.format_exc()],
                "classification_hint": "FAIL",
            }
            print(f"FAIL {case['id']}: {exc}", flush=True)
            (OUT_DIR / case["id"]).mkdir(parents=True, exist_ok=True)
            (OUT_DIR / case["id"] / "error.txt").write_text(
                "\n".join(entry["errors"]), encoding="utf-8"
            )
        report["cases"].append(entry)
        if entry.get("session_id"):
            report["session_ids"].append(entry["session_id"])

    # Isolation: unique session ids
    ids = report["session_ids"]
    report["session_isolation"] = {
        "count": len(ids),
        "unique": len(set(ids)),
        "all_unique": len(ids) == len(set(ids)) and len(ids) == len(selected),
        "ids": ids,
    }

    latencies = [c.get("latency_ms_total") for c in report["cases"] if c.get("latency_ms_total")]
    report["cost_latency"] = {
        "total_estimated_cost_usd": round(
            sum(c.get("estimated_cost_usd", 0) or 0 for c in report["cases"]), 6
        ),
        "average_latency_ms": int(statistics.mean(latencies)) if latencies else None,
        "p50_latency_ms": int(statistics.median(latencies)) if latencies else None,
        "latencies_ms": latencies,
    }
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    raw_path = OUT_DIR / "PUBLIC_QA_RAW.json"
    raw_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nWrote", raw_path, flush=True)
    print("session_isolation", report["session_isolation"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
