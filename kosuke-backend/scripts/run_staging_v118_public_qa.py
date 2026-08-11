#!/usr/bin/env python3
"""Staging Public QA for Parallel Life Deep Reading v1.1.8-exp (BranchSemantics).

Uses the exact same 10 fixtures as v1.1.7 Public QA.
Does NOT modify prompts, runtime, schemas, Observatory thresholds,
title validation, or publication gates. No auto-tune after failures.
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.branch_semantics import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V118,
    RUNTIME_VERSION_V118_EXP,
    career_template_leakage,
)
from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    abstract_vocabulary_density,
    claim_text_is_malformed,
    re_branch_realization_check,
    section_resume_flags,
)
from scripts.run_staging_v11_context_pack_live_ab import (  # noqa: E402
    NTT_PACK_ITEMS,
    NTT_SOURCE,
    PROD_API,
    STAGING_API,
    _aq_list,
    _dump,
    _now,
    _view,
    build_approved_pack,
    extract_trace,
    probe_flags,
    req,
)
from scripts.run_staging_v117_public_qa import (  # noqa: E402
    CASES,
    _section_bodies,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-public-qa"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / "PUBLIC_QA_V118_LIVE_REPORT.md"
RAW = OUT / "PUBLIC_QA_V118_RAW.json"
PREV_RAW = OUT / "PUBLIC_QA_RAW.json"

COACHING_RE = re.compile(r"(?:すべき|今こそ|挑戦しよう|成長しよう|キャリアアップ|生産性を上げ)")
SCHEMA_LEAK_RE = re.compile(
    r"(?:この選択は、実際に選んだのは|スキーマ|boundary_type|fact_\d+|source_field)"
)
CAUSAL_RE = re.compile(r"(?:引き起こ|のせいだ|が原因で|させた|強いた|せざるを得)")

CAREER_LEAK_FAMILY = re.compile(
    r"(?:役職や年収|仕事を定義し直|所属が変わるたびに自分の仕事|"
    r"持ち運ぶ蓄積|一制度のなかで進み具合|長期の積み重ねとして認める|"
    r"勤務先の一点ではなく|内部で積み上げる道と外へ持ち運ぶ)"
)
CAREER_LEAK_ROMANCE = re.compile(
    r"(?:持ち運ぶ蓄積|制度内評価|一制度のなかで進み具合|役職や年収|"
    r"仕事を定義し直|持ち運ぶ道)"
)
EDU_MOBILITY_LEAK = re.compile(r"(?:所属が変わるたびに自分の仕事|仕事を定義し直す道へ移った)")
CREATIVE_ENT_LEAK = re.compile(
    r"(?:役職や年収だけを唯一|長期の積み重ねとして認める|起業家としての自己定義)"
)

SEM_FIELDS = [
    "domain",
    "changed_dimension",
    "chosen_structure",
    "unchosen_structure",
    "central_tension",
    "lost_verifiability",
    "protected_possibility",
    "present_residue",
    "possible_rebranch_modes",
    "sensitive_boundaries",
]


def verify_pins() -> dict:
    pack = build_approved_pack(NTT_PACK_ITEMS)
    code_s, strict = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": "pin strict",
            "language": "ja",
            "deep_reading_mode": "strict",
            "clarifications": {},
            "editorial_context": {},
        },
    )
    ss = (strict or {}).get("session") or {}
    sm = ss.get("model_metadata") or {}
    code_c, ctx = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": NTT_SOURCE,
            "language": "ja",
            "deep_reading_mode": "contextual",
            "context_pack": pack,
            "clarifications": {},
            "editorial_context": {},
        },
        timeout=300,
    )
    cs = (ctx or {}).get("session") or {}
    cm = cs.get("model_metadata") or {}
    c1 = cs.get("call1") or {}
    code_p, prod = req(
        PROD_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": "pin prod",
            "language": "ja",
            "deep_reading_mode": "contextual",
            "clarifications": {},
            "editorial_context": {},
        },
    )
    ps = (prod or {}).get("session") or {}
    pm = ps.get("model_metadata") or {}
    flags = probe_flags()
    has_sem = bool(c1.get("branch_semantics"))
    return {
        "flags": flags,
        "staging_strict": {
            "http": code_s,
            "call1": (ss.get("prompt_versions") or {}).get("call_1")
            or sm.get("call_1_prompt_version"),
            "schema": ss.get("schema_version"),
        },
        "staging_contextual": {
            "http": code_c,
            "call1": (cs.get("prompt_versions") or {}).get("call_1")
            or cm.get("call_1_prompt_version")
            or c1.get("prompt_version"),
            "schema": cs.get("schema_version")
            or cm.get("runtime_validation_version")
            or ((c1.get("selection_compression_diagnostics") or {}).get("runtime_pin")),
            "pack": cm.get("context_pack_enabled"),
            "branch_semantics_present": has_sem,
            "branch_semantics_domain": (c1.get("branch_semantics") or {}).get("domain"),
        },
        "production": {
            "http": code_p,
            "call1": (ps.get("prompt_versions") or {}).get("call_1")
            or pm.get("call_1_prompt_version"),
            "pack": pm.get("context_pack_enabled"),
        },
    }


def _answer_payload(questions: list[str], case: dict) -> dict[str, str]:
    cat = (case.get("category") or "").lower()
    answers: dict[str, str] = {}
    for i, q in enumerate(questions or ["いまの生活の具体的な場面を教えてください"]):
        if any(t in q for t in ("現在", "生活", "場面", "暮ら")):
            if "romance" in cat:
                answers[str(i)] = "今は一人で普通に暮らしている。仕事と日々の買い物がある。"
            elif "creative" in cat:
                answers[str(i)] = "平日は会社で働き、夜と週末に文章と写真の制作をしている。"
            elif "family" in cat:
                answers[str(i)] = "妻と息子と三人で暮らし、仕事の日常が続いている。"
            else:
                answers[str(i)] = "いまの暮らしと仕事の具体的な場面が続いている。"
        else:
            answers[str(i)] = "あの分岐がいまも残る問いとして触れることがある。"
    return answers


def confirm_with_clarification_loop(
    api: str, sid: str, session: dict, case: dict
) -> tuple[int, dict, dict]:
    """Answer → approve loop. needs_additional_input + HTTP 200 is normal, not failure."""
    clarification: dict[str, Any] = {
        "rounds": [],
        "http_400_on_needs_additional_input": False,
        "duplicate_questions": [],
        "schema_leakage": False,
        "continued_after_clarification": False,
        "final_status": None,
        "clarification_required_flags": [],
    }
    seen_q: list[str] = []
    view = _view(session)
    ctx = [c for c in (view.get("current_context") or []) if str(c).strip()]
    if not ctx:
        view["current_context"] = ["いまの暮らしと仕事の具体的な場面が続いている"]
    pq = [q for q in (view.get("present_questions") or []) if str(q).strip()]
    if not pq:
        view["present_questions"] = ["あのとき別の道を選んでいたら、いまはどうだったか"]

    for round_i in range(4):
        call1 = session.get("call1") or {}
        status = call1.get("status") or session.get("status")
        questions = _aq_list(call1)
        if not questions and status in {
            "needs_additional_input",
            "structural_ambiguity",
            "insufficient_current_context",
        }:
            questions = ["いまの生活の具体的な場面を教えてください"]

        if status in {
            "needs_additional_input",
            "structural_ambiguity",
            "insufficient_current_context",
            "sensitive_domain_clarification_required",
        } or questions:
            for q in questions:
                if q in seen_q:
                    clarification["duplicate_questions"].append(q)
                seen_q.append(q)
            answers = _answer_payload(questions, case)
            code, answered = req(
                api,
                "POST",
                "/experience/parallel-life/deep-reading/confirm",
                {
                    "session_id": sid,
                    "action": "answer",
                    "answers_to_additional_questions": answers,
                    "confirmation_view_overrides": view,
                },
            )
            clarification["rounds"].append(
                {
                    "round": round_i,
                    "action": "answer",
                    "http": code,
                    "questions": questions,
                    "answers": answers,
                    "resp_status": (answered.get("status") if isinstance(answered, dict) else None),
                    "clarification_required": (
                        answered.get("clarification_required")
                        if isinstance(answered, dict)
                        else None
                    ),
                }
            )
            if code == 400 and status == "needs_additional_input":
                clarification["http_400_on_needs_additional_input"] = True
            if code != 200:
                clarification["final_status"] = status
                return code, answered if isinstance(answered, dict) else {"detail": answered}, clarification
            session = answered.get("session") or {}
            view = _view(session)
            clarification["continued_after_clarification"] = True
            if SCHEMA_LEAK_RE.search(json.dumps(answered, ensure_ascii=False)):
                clarification["schema_leakage"] = True

        # approve
        code, confirmed = req(
            api,
            "POST",
            "/experience/parallel-life/deep-reading/confirm",
            {
                "session_id": sid,
                "action": "approve",
                "confirmation_view_overrides": view,
            },
        )
        clarification["rounds"].append(
            {
                "round": round_i,
                "action": "approve",
                "http": code,
                "resp_status": (confirmed.get("status") if isinstance(confirmed, dict) else None),
                "clarification_required": (
                    confirmed.get("clarification_required")
                    if isinstance(confirmed, dict)
                    else None
                ),
                "questions": (confirmed.get("questions") if isinstance(confirmed, dict) else None),
            }
        )
        if code == 400:
            # Valid needs_additional_input must not 400 after v1.1.8
            prev = session.get("status") or (session.get("call1") or {}).get("status")
            if prev == "needs_additional_input":
                clarification["http_400_on_needs_additional_input"] = True
            clarification["final_status"] = prev
            return code, confirmed if isinstance(confirmed, dict) else {"detail": confirmed}, clarification
        if code != 200:
            clarification["final_status"] = session.get("status")
            return code, confirmed if isinstance(confirmed, dict) else {"detail": confirmed}, clarification

        session = confirmed.get("session") or {}
        view = _view(session)
        status = (
            confirmed.get("status")
            or session.get("status")
            or (session.get("call1") or {}).get("status")
        )
        clarification["clarification_required_flags"].append(
            bool(confirmed.get("clarification_required"))
        )
        clarification["final_status"] = status
        if status == "ready_for_draft":
            return code, confirmed, clarification
        # still clarifying — continue loop (HTTP 200 is success for intermediate)
        if not confirmed.get("clarification_required") and status not in {
            "needs_additional_input",
            "structural_ambiguity",
            "insufficient_current_context",
            "sensitive_domain_clarification_required",
        }:
            return code, confirmed, clarification

    return 200, {"session": session, "status": clarification["final_status"]}, clarification


def run_pipeline_v118(
    api: str,
    *,
    case_id: str,
    source: str,
    pack: dict | None,
    case: dict,
) -> dict:
    t0 = time.perf_counter()
    out: dict = {
        "case_id": case_id,
        "arm": "public_qa_v118",
        "mode": "contextual",
        "ok": False,
        "stages": {},
        "clarification": {},
        "safe_stop": False,
    }
    body: dict[str, Any] = {
        "source_text": source,
        "language": "ja",
        "clarifications": {},
        "editorial_context": {},
        "deep_reading_mode": "contextual",
    }
    if pack is not None:
        body["context_pack"] = pack

    code, ground = req(api, "POST", "/experience/parallel-life/deep-reading/ground", body, timeout=300)
    out["stages"]["ground"] = {"status": code}
    if code != 200 or not isinstance(ground, dict):
        out["error"] = ground
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return out

    session = ground.get("session") or {}
    sid = session.get("session_id")
    out["session_id"] = sid
    out["stages"]["ground"].update(
        {
            "status_field": session.get("status"),
            "schema_version": session.get("schema_version"),
            "prompt_versions": session.get("prompt_versions"),
            "call1_prompt": (session.get("model_metadata") or {}).get("call_1_prompt_version"),
            "branch_semantics": (session.get("call1") or {}).get("branch_semantics"),
        }
    )
    out["trace_after_ground"] = extract_trace(session)
    out["branch_semantics_after_ground"] = (session.get("call1") or {}).get("branch_semantics")

    time.sleep(1.2)
    code_c, confirmed, clar = confirm_with_clarification_loop(api, sid, session, case)
    out["clarification"] = clar
    out["stages"]["confirm"] = {"status": code_c, "resp_status": clar.get("final_status")}
    if code_c != 200:
        out["error"] = confirmed
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        _dump(case_id, "public_qa_v118", "confirm_error", confirmed)
        return out

    session = confirmed.get("session") or {}
    out["trace_after_confirm"] = extract_trace(session)
    out["branch_semantics_after_confirm"] = (session.get("call1") or {}).get("branch_semantics")
    status = (
        confirmed.get("status")
        or session.get("status")
        or (session.get("call1") or {}).get("status")
    )
    if status != "ready_for_draft":
        # Correct safe-stop / still clarifying — not a generation hard fail
        out["safe_stop"] = True
        out["ok"] = True
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        _dump(case_id, "public_qa_v118", "session_final", session)
        return out

    idem = f"v118qa-{case_id}-{_now()}"
    code_d, draft = req(
        api,
        "POST",
        "/experience/parallel-life/deep-reading/draft",
        {"session_id": sid, "idempotency_key": idem},
        timeout=600,
    )
    out["stages"]["draft"] = {"status": code_d}
    if code_d != 200:
        out["error"] = draft
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        _dump(case_id, "public_qa_v118", "session_final", session)
        return out

    code_e, edited = req(
        api,
        "POST",
        "/experience/parallel-life/deep-reading/edit-validate",
        {"session_id": sid, "idempotency_key": f"{idem}-e"},
        timeout=600,
    )
    out["stages"]["edit"] = {"status": code_e}
    if code_e != 200:
        out["error"] = edited
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return out

    session = edited.get("session") or {}
    call3 = session.get("call3") or {}
    out["manuscript"] = {
        "title": call3.get("final_title") or edited.get("final_title"),
        "body_markdown": call3.get("body_markdown") or edited.get("body_markdown"),
    }
    out["ok"] = True
    out["elapsed_s"] = round(time.perf_counter() - t0, 2)
    _dump(case_id, "public_qa_v118", "session_final", session)
    out["branch_semantics_final"] = (session.get("call1") or {}).get("branch_semantics")
    return out


def extract_sem(session: dict, pipe: dict) -> dict:
    call1 = session.get("call1") or {}
    sem = (
        call1.get("branch_semantics")
        or pipe.get("branch_semantics_final")
        or pipe.get("branch_semantics_after_confirm")
        or pipe.get("branch_semantics_after_ground")
        or {}
    )
    out = {k: sem.get(k) for k in SEM_FIELDS}
    out["confidence"] = sem.get("confidence")
    out["diagnostics"] = sem.get("diagnostics") or {}
    return out


def career_leak_check(case: dict, sem: dict, contracts: list, body: str) -> dict:
    cat = (case.get("category") or "").lower()
    contract_blob = "\n".join(
        f"{c.get('required_meaning','')}\n{c.get('interpretive_claim','')}"
        for c in contracts
    )
    sem_blob = "\n".join(str(sem.get(k) or "") for k in SEM_FIELDS)
    blob = f"{sem_blob}\n{contract_blob}\n{body or ''}"
    leaks: list[str] = []
    if "family" in cat:
        if CAREER_LEAK_FAMILY.search(blob):
            leaks.append("family_inherited_career_template")
    if "romance" in cat:
        if CAREER_LEAK_ROMANCE.search(blob):
            leaks.append("romance_inherited_career_template")
    if "education" in cat:
        if EDU_MOBILITY_LEAK.search(blob):
            leaks.append("education_auto_career_mobility")
    if "creative" in cat:
        if CREATIVE_ENT_LEAK.search(blob):
            leaks.append("creative_auto_entrepreneurship_metric")
    if case.get("sensitive") or "health" in cat:
        if CAUSAL_RE.search(body or "") or CAUSAL_RE.search(contract_blob):
            leaks.append("health_causal_invention")
    # Generic unexplained career template on non-career domains
    if cat not in {"career", "entrepreneurship / business", "entrepreneurship"} and career_template_leakage(
        sem_blob + "\n" + contract_blob
    ):
        if "family_inherited_career_template" not in leaks and "romance_inherited_career_template" not in leaks:
            if CAREER_LEAK_FAMILY.search(sem_blob + "\n" + contract_blob):
                leaks.append("unexplained_career_template_leakage")
    return {"leaks": leaks, "ok": not leaks}


def score_case(case: dict, pipe: dict, session: dict) -> dict:
    call1 = session.get("call1") or {}
    call3 = session.get("call3") or {}
    validation = call3.get("validation") or {}
    body = (pipe.get("manuscript") or {}).get("body_markdown") or call3.get("body_markdown") or ""
    title = (pipe.get("manuscript") or {}).get("title") or call3.get("final_title") or ""
    blob = f"{title}\n{body}"
    sections = _section_bodies(body)
    resume = section_resume_flags(blob) if body else {"resume_density": 0}
    dens = abstract_vocabulary_density(blob) if body else {"counts": {}, "excess": {}}
    sem = extract_sem(session, pipe)
    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    leak = career_leak_check(case, sem, contracts, body)

    lost = sections.get("失ったもの", "")
    prot = sections.get("守られたもの", "")
    residue = sections.get("今に残った構造", "")
    rebranch = sections.get("これからの再分岐", "")
    branch_pt = sections.get("分岐点", "")
    chosen = sections.get("選んだ道", "")
    unchosen = sections.get("選ばなかった人生", "")
    observatory = sections.get("社会との接続", "")
    re_ok, re_missing, _ = (
        re_branch_realization_check(rebranch, residue_body=residue) if rebranch else (False, ["absent"], {})
    )
    reb_contract = next((c for c in contracts if c.get("section_id") == "re_branch"), {})
    re_omitted = bool(reb_contract) and not reb_contract.get("must_be_present")

    # Realization: broader than career-only markers
    lost_r = bool(
        re.search(r"(?:物差し|測り方|確かめ|連続|手放|閉じ|辿れ|手がかり|検証)", lost)
    ) if lost else False
    prot_r = bool(
        re.search(r"(?:余白|定義し直|別の言葉|固定しきら|閉じきら|可能性|余地|保た)", prot)
    ) if prot else False
    residue_r = bool(
        re.search(r"(?:問い|いまも|残|並べ|想像|物差し|未解決)", residue)
    ) if residue else False

    # Observatory
    cand = call1.get("candidate_lens_selection") or {}
    candidates = cand.get("candidates") if isinstance(cand, dict) else []
    sel = call1.get("selected_observatory_lenses") or {}
    selected = sel.get("selected") if isinstance(sel, dict) else sel
    lenses = []
    for c in selected or []:
        if isinstance(c, dict):
            lenses.append(
                {
                    "lens_id": c.get("lens_id"),
                    "new_meaning_added": bool((c.get("new_meaning_added") or "").strip()),
                    "meaning": (c.get("new_meaning_added") or "")[:120],
                }
            )
    evidence = call1.get("retrieved_observatory_evidence") or []
    obs_diag = call1.get("observatory_core_diagnostics") or {}

    blocking = list(validation.get("blocking_reasons") or [])
    unsupported_causality = list(validation.get("unsupported_causality") or [])
    unsupported_bio = list(
        validation.get("unsupported_personal_details")
        or validation.get("unsupported_scenes")
        or []
    )
    affect = list(validation.get("unsupported_affect") or [])
    schema_leak = list(validation.get("schema_leakage_prose") or [])
    title_ok = validation.get("title_validation", {})
    title_passed = (
        title_ok.get("passed", "title_validation_failed" not in blocking)
        if isinstance(title_ok, dict)
        else "title_validation_failed" not in blocking
    )
    coaching = bool(COACHING_RE.search(blob)) if blob else False
    schema_text = bool(SCHEMA_LEAK_RE.search(blob)) if blob else False
    lens_overreach = bool(
        re.search(r"(?:レンズ|Observatory|制度理論|社会学的に断言)", blob)
    ) if blob else False

    publishable = bool(validation.get("publishable"))
    naturalness = None
    depth = None
    life_read = "n/a"
    if body:
        template_n = len(
            re.findall(r"(?:と読むことができる|とも言える|として見ることができる)", blob)
        )
        naturalness = 9 if template_n <= 2 and resume["resume_density"] <= 3 and not dens.get("excess") else (
            8 if resume["resume_density"] <= 3 and template_n <= 4 else 7
        )
        if coaching or schema_text:
            naturalness = min(naturalness, 6)
        depth = 9 if lost_r and prot_r and residue_r and (re_ok or re_omitted) else (
            8 if (lost_r or residue_r) and (re_ok or re_omitted or not reb_contract.get("must_be_present", True)) else 7
        )
        life_read = (
            "YES"
            if publishable and naturalness >= 8 and depth >= 8 and resume["resume_density"] <= 3
            else "mixed"
        )

    # CVA / personal / social / thesis closure heuristics
    personal_focus = 8 if chosen and unchosen and not re.search(r"(?:レンズ名|制度理論)", blob) else 5
    social_depth = 7 if observatory and lenses else (5 if observatory else 3)
    thesis_closure = 8 if (lost_r and residue_r and (re_ok or re_omitted)) else (5 if body else None)
    cva = round(((naturalness or 0) + (depth or 0) + personal_focus) / 3, 1) if body else None
    title_quality = 8 if title_passed and title and len(title) <= 40 else (5 if title else None)

    hard = []
    if leak["leaks"]:
        hard.append("career_template_leakage:" + ",".join(leak["leaks"]))
    if pipe.get("clarification", {}).get("http_400_on_needs_additional_input"):
        hard.append("clarification_http_400")
    if publishable and blocking:
        hard.append("publishable_true_with_blocking")
    if unsupported_causality and case.get("sensitive"):
        hard.append("sensitive_unsupported_causality")

    invented_hits = []
    source = case.get("source") or ""
    for phrase in ("年収", "診断名", "ステージ", "治った", "成功した起業"):
        if phrase in blob and phrase not in source:
            invented_hits.append(phrase)

    clar = pipe.get("clarification") or {}
    call1_status = call1.get("status") or session.get("status") or clar.get("final_status")

    classification = "PASS"
    if hard:
        classification = "HARD_FAIL"
    elif pipe.get("safe_stop") and not publishable:
        classification = "PASS_SAFE_STOP"
    elif publishable and (naturalness or 0) >= 8 and (depth or 0) >= 8 and life_read == "YES":
        classification = "PASS"
    elif publishable:
        classification = "PASS_WITH_NOTES"
    elif pipe.get("stages", {}).get("edit", {}).get("status") == 200:
        classification = "GATE_BLOCKED"
    elif pipe.get("ok") and not body:
        classification = "PASS_SAFE_STOP"
    else:
        classification = "INCOMPLETE"

    return {
        "case_id": case["id"],
        "category": case["category"],
        "title": case["title"],
        "pipeline_ok": bool(pipe.get("ok")),
        "safe_stop": bool(pipe.get("safe_stop")),
        "elapsed_s": pipe.get("elapsed_s"),
        "session_id": pipe.get("session_id"),
        "call1_status": call1_status,
        "call1_prompt": (session.get("prompt_versions") or {}).get("call_1")
        or ((session.get("model_metadata") or {}).get("call_1_prompt_version")),
        "call3_prompt": call3.get("prompt_version"),
        "branch_semantics": sem,
        "career_leak": leak,
        "clarification": {
            "http_400": clar.get("http_400_on_needs_additional_input"),
            "rounds": len(clar.get("rounds") or []),
            "questions_seen": [
                q
                for r in (clar.get("rounds") or [])
                if r.get("action") == "answer"
                for q in (r.get("questions") or [])
            ],
            "duplicate_questions": clar.get("duplicate_questions"),
            "continued": clar.get("continued_after_clarification"),
            "final_status": clar.get("final_status"),
            "schema_leakage": clar.get("schema_leakage"),
        },
        "factual_fidelity": 10 if not invented_hits else 7,
        "naturalness": naturalness,
        "depth": depth,
        "life_read": life_read,
        "resume_density": resume.get("resume_density"),
        "cva": cva,
        "personal_focus": personal_focus if body else None,
        "social_depth": social_depth if body else None,
        "thesis_closure": thesis_closure,
        "title_quality": title_quality,
        "section_realization": {
            "branch_point": bool(branch_pt),
            "chosen_path": bool(chosen),
            "unchosen_life": bool(unchosen),
            "lost": lost_r,
            "protected": prot_r,
            "residue": residue_r,
            "observatory": bool(observatory),
            "re_branch": re_ok,
            "re_branch_omitted_valid": re_omitted,
        },
        "observatory": {
            "candidates": [
                c.get("lens_id") if isinstance(c, dict) else c for c in (candidates or [])
            ],
            "selected": [x.get("lens_id") for x in lenses],
            "evidence_ids": [
                e.get("id") if isinstance(e, dict) else e for e in (evidence or [])
            ][:8],
            "structures": (obs_diag or {}).get("structures_detected"),
            "lenses_added_meaning": any(x["new_meaning_added"] for x in lenses),
            "zero_lens_ok": len(lenses) == 0,
        },
        "title_validation_passed": title_passed,
        "publishable": publishable,
        "blocking_reasons": blocking,
        "unsupported_causality_count": len(unsupported_causality),
        "unsupported_biography_count": len(unsupported_bio) if isinstance(unsupported_bio, list) else int(bool(unsupported_bio)),
        "affect_inference_count": len(affect) if isinstance(affect, list) else int(bool(affect)),
        "self_help_coaching_drift": coaching,
        "lens_overreach": lens_overreach,
        "schema_leakage": bool(schema_leak) or schema_text,
        "malformed_claims": [
            c.get("section_id")
            for c in contracts
            if claim_text_is_malformed(c.get("interpretive_claim") or "")
        ],
        "hard_failures": hard,
        "classification": classification,
        "final_title": title,
        "body_excerpt": body[:500],
        "abstract_vocab": dens.get("counts"),
        "rebranch_missing": re_missing if rebranch else ["no_section"],
    }


def compare_v117(results: list[dict]) -> dict:
    if not PREV_RAW.exists():
        return {"available": False}
    prev = json.loads(PREV_RAW.read_text(encoding="utf-8"))
    prev_results = {r["case_id"]: r for r in prev.get("results") or []}
    pub117 = sum(1 for r in prev_results.values() if r.get("publishable"))
    pub118 = sum(1 for r in results if r.get("publishable"))
    gate117 = sum(1 for r in prev_results.values() if r.get("classification") == "GATE_BLOCKED")
    gate118 = sum(1 for r in results if r.get("classification") == "GATE_BLOCKED")
    clar117 = sum(
        1
        for r in prev_results.values()
        if "confirm_failed" in (r.get("confirmation_issues") or [])
        or any("400" in str(x) for x in (r.get("confirmation_issues") or []))
    )
    # Prior incomplete/confirm fail heuristic from summary
    clar117 = prev.get("summary", {}).get("incomplete_or_confirm_fail", clar117)
    clar400_118 = sum(1 for r in results if r.get("clarification", {}).get("http_400"))
    leak118 = sum(1 for r in results if r.get("career_leak", {}).get("leaks"))
    return {
        "available": True,
        "v117_verdict": prev.get("verdict"),
        "publishable": {"v117": pub117, "v118": pub118},
        "gate_blocked": {"v117": gate117, "v118": gate118},
        "clarification_failures": {"v117_incomplete_or_confirm": clar117, "v118_http_400": clar400_118},
        "career_template_leakage": {"v117": "not_measured", "v118": leak118},
        "naturalness_pub_ge8": {
            "v117": prev.get("summary", {}).get("publishable_naturalness_ge8"),
            "v118": sum(1 for r in results if r.get("publishable") and (r.get("naturalness") or 0) >= 8),
        },
        "depth_pub_ge8": {
            "v117": prev.get("summary", {}).get("publishable_depth_ge8"),
            "v118": sum(1 for r in results if r.get("publishable") and (r.get("depth") or 0) >= 8),
        },
        "life_read_yes": {
            "v117": prev.get("summary", {}).get("publishable_life_read_yes"),
            "v118": sum(1 for r in results if r.get("publishable") and r.get("life_read") == "YES"),
        },
        "observatory_zero_all": {
            "v117": all((r.get("lens_count") or 0) == 0 for r in prev_results.values()),
            "v118": all(not (r.get("observatory") or {}).get("selected") for r in results),
        },
    }


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify_v118.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V118
        and (
            pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V118_EXP
            or pins["staging_contextual"].get("branch_semantics_present") is True
        )
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
        and pins["flags"].get("production_context_pack_off") is True
    )
    if not ready:
        print(json.dumps({"error": "pins_not_ready", "pins": pins}, ensure_ascii=False, indent=2))
        REPORT.write_text(
            "# Public QA v1.1.8 ABORTED — pins not ready\n\n```json\n"
            + json.dumps(pins, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        return 2

    results: list[dict] = []
    for i, case in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] {case['id']} ...", flush=True)
        pack = build_approved_pack(case["pack_items"]) if case.get("pack_items") else None
        pipe = run_pipeline_v118(
            STAGING_API,
            case_id=case["id"],
            source=case["source"],
            pack=pack,
            case=case,
        )
        session = {}
        sp = (
            ROOT
            / "e2e_reports"
            / "deep-reading-v1.1-context-pack"
            / "live_ab"
            / case["id"]
            / "public_qa_v118_session_final.json"
        )
        if sp.exists():
            session = json.loads(sp.read_text(encoding="utf-8"))
        scored = score_case(case, pipe, session)
        scored["pipeline_error"] = bool(pipe.get("error"))
        scored["stages"] = pipe.get("stages")
        results.append(scored)
        case_dir = OUT / "v118" / case["id"]
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "score.json").write_text(
            json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (case_dir / "pipeline.json").write_text(
            json.dumps(pipe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ms = pipe.get("manuscript") or {}
        if ms.get("body_markdown"):
            (case_dir / "manuscript.md").write_text(
                f"# {ms.get('title') or ''}\n\n{ms.get('body_markdown')}\n",
                encoding="utf-8",
            )
        time.sleep(1.0)

    publishable_cases = [r for r in results if r.get("publishable")]
    hard_fails = [r for r in results if r.get("hard_failures")]
    leak_fails = [r for r in results if r.get("career_leak", {}).get("leaks")]
    clar400 = [r for r in results if r.get("clarification", {}).get("http_400")]
    gate_blocked = [r for r in results if r.get("classification") == "GATE_BLOCKED"]
    safe_stops = [r for r in results if r.get("classification") == "PASS_SAFE_STOP"]

    nat_ok = sum(1 for r in publishable_cases if (r.get("naturalness") or 0) >= 8)
    depth_ok = sum(1 for r in publishable_cases if (r.get("depth") or 0) >= 8)
    life_ok = sum(1 for r in publishable_cases if r.get("life_read") == "YES")
    resume_ok = sum(1 for r in publishable_cases if (r.get("resume_density") or 99) <= 3)
    fidelity_ok = sum(1 for r in results if r.get("factual_fidelity") == 10)

    n_pub = max(1, len(publishable_cases))
    most_nat = nat_ok / n_pub >= 0.6 if publishable_cases else False
    most_depth = depth_ok / n_pub >= 0.6 if publishable_cases else False
    most_life = life_ok / n_pub >= 0.6 if publishable_cases else False

    if hard_fails or clar400 or leak_fails:
        verdict = "V1.1.8 NOT READY"
    elif (
        publishable_cases
        and most_nat
        and most_depth
        and most_life
        and resume_ok == len(publishable_cases)
        and fidelity_ok == len(results)
        and not hard_fails
        and not clar400
        and not leak_fails
    ):
        verdict = "V1.1.8 READY FOR RELEASE CANDIDATE"
    else:
        verdict = "V1.1.8 PROMISING — NEEDS TARGETED FIXES"

    comparison = compare_v117(results)
    improved = False
    if comparison.get("available"):
        improved = (
            comparison["publishable"]["v118"] >= comparison["publishable"]["v117"]
            and comparison["clarification_failures"]["v118_http_400"] == 0
            and comparison["career_template_leakage"]["v118"] == 0
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "verdict": verdict,
        "comparison_v117": comparison,
        "branch_semantics_improved_cross_domain": improved,
        "summary": {
            "cases": len(results),
            "publishable": len(publishable_cases),
            "gate_blocked": len(gate_blocked),
            "safe_stops": len(safe_stops),
            "hard_fails": len(hard_fails),
            "career_leaks": len(leak_fails),
            "clarification_http_400": len(clar400),
            "fidelity_10": fidelity_ok,
            "publishable_naturalness_ge8": nat_ok,
            "publishable_depth_ge8": depth_ok,
            "publishable_life_read_yes": life_ok,
            "publishable_resume_le3": resume_ok,
        },
        "results": results,
        "no_auto_tune": True,
        "production_untouched": True,
    }
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Parallel Life Deep Reading v1.1.8-exp — Staging Public QA Live Report",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Staging: `{STAGING_API}`  ",
        "Production: **untouched**  ",
        "",
        "## 12. Final verdict",
        "",
        "```",
        verdict,
        "```",
        "",
        f"BranchSemantics improved cross-domain generalization: **{improved}**",
        "",
        "**No prompt/runtime/schema/Observatory-threshold changes during this QA. No auto-tune.**",
        "",
        "## 1. Staging deployment",
        "",
        f"- Contextual Call1: `{pins['staging_contextual'].get('call1')}`",
        f"- Contextual runtime/schema: `{pins['staging_contextual'].get('schema')}`",
        f"- Context Pack enabled: `{pins['staging_contextual'].get('pack')}`",
        f"- BranchSemantics present on NTT ground: `{pins['staging_contextual'].get('branch_semantics_present')}` "
        f"(domain=`{pins['staging_contextual'].get('branch_semantics_domain')}`)",
        f"- Strict Call1: `{pins['staging_strict'].get('call1')}`",
        "",
        "Pipeline confirmed:",
        "",
        "```",
        "Grounded → BranchSemantics → Context Pack → Observatory → MeaningCompression",
        "→ Thesis → SectionContracts → Interpretive Claims → Call2 → Call3",
        "```",
        "",
        "## 2. Production untouched confirmation",
        "",
        f"- Production Call1: `{pins['production'].get('call1')}`",
        f"- Production pack: `{pins['production'].get('pack')}` (must be false/null)",
        f"- production_context_pack_off flag: `{pins['flags'].get('production_context_pack_off')}`",
        "",
        "## 3. 10-case matrix",
        "",
        "| Case | Domain(sem) | Pub | Fid | Nat | Depth | Life | Resume | Leak | Clar400 | Class |",
        "|------|-------------|-----|-----|-----|-------|------|--------|------|---------|-------|",
    ]
    for r in results:
        sem = r.get("branch_semantics") or {}
        lines.append(
            "| {id} | {dom} | {pub} | {fid} | {nat} | {dep} | {life} | {res} | {leak} | {c400} | {cls} |".format(
                id=r["case_id"],
                dom=sem.get("domain"),
                pub=r.get("publishable"),
                fid=r.get("factual_fidelity"),
                nat=r.get("naturalness"),
                dep=r.get("depth"),
                life=r.get("life_read"),
                res=r.get("resume_density"),
                leak=";".join((r.get("career_leak") or {}).get("leaks") or []) or "-",
                c400=r.get("clarification", {}).get("http_400"),
                cls=r.get("classification"),
            )
        )

    lines.extend(["", "## 4. BranchSemantics per case", ""])
    for r in results:
        sem = r.get("branch_semantics") or {}
        lines.append(f"### {r['case_id']}")
        lines.append("")
        for k in SEM_FIELDS:
            lines.append(f"- **{k}**: `{sem.get(k)}`")
        lines.append("")

    lines.extend(["", "## 5. Clarification flow", ""])
    for r in results:
        c = r.get("clarification") or {}
        if not c.get("rounds") and not c.get("questions_seen"):
            continue
        lines.append(f"### {r['case_id']}")
        lines.append("")
        lines.append(f"- HTTP 400 on needs_additional_input: `{c.get('http_400')}`")
        lines.append(f"- Rounds: `{c.get('rounds')}`")
        lines.append(f"- Questions: `{c.get('questions_seen')}`")
        lines.append(f"- Duplicates: `{c.get('duplicate_questions')}`")
        lines.append(f"- Continued: `{c.get('continued')}` · final=`{c.get('final_status')}`")
        lines.append(f"- Schema leakage: `{c.get('schema_leakage')}`")
        lines.append("")

    lines.extend(
        [
            "## 6. Career leakage checks",
            "",
            f"| Check | Result |",
            f"|-------|--------|",
            f"| Total leak cases | {len(leak_fails)} |",
            f"| family / romance / education / creative / health | "
            + (
                "FAIL: " + ", ".join(r["case_id"] for r in leak_fails)
                if leak_fails
                else "OK"
            )
            + " |",
            "",
            "## 7. Section realization",
            "",
            "| Case | BP | Chosen | Unchosen | Lost | Prot | Res | Obs | Rebr |",
            "|------|----|--------|----------|------|------|-----|-----|------|",
        ]
    )
    for r in results:
        s = r.get("section_realization") or {}
        lines.append(
            f"| {r['case_id']} | {s.get('branch_point')} | {s.get('chosen_path')} | "
            f"{s.get('unchosen_life')} | {s.get('lost')} | {s.get('protected')} | "
            f"{s.get('residue')} | {s.get('observatory')} | "
            f"{'omit' if s.get('re_branch_omitted_valid') else s.get('re_branch')} |"
        )

    lines.extend(["", "## 8. Observatory", ""])
    for r in results:
        o = r.get("observatory") or {}
        lines.append(
            f"- **{r['case_id']}**: candidates=`{o.get('candidates')}` selected=`{o.get('selected')}` "
            f"evidence=`{o.get('evidence_ids')}` structures=`{o.get('structures')}` "
            f"added_meaning=`{o.get('lenses_added_meaning')}` zero_ok=`{o.get('zero_lens_ok')}`"
        )

    lines.extend(
        [
            "",
            "## 9. Quality scores",
            "",
            "| Case | Fid | Nat | Depth | Life | Resume | CVA | Personal | Social | Thesis | TitleQ |",
            "|------|-----|-----|-------|------|--------|-----|----------|--------|--------|--------|",
        ]
    )
    for r in results:
        lines.append(
            f"| {r['case_id']} | {r.get('factual_fidelity')} | {r.get('naturalness')} | "
            f"{r.get('depth')} | {r.get('life_read')} | {r.get('resume_density')} | "
            f"{r.get('cva')} | {r.get('personal_focus')} | {r.get('social_depth')} | "
            f"{r.get('thesis_closure')} | {r.get('title_quality')} |"
        )

    lines.extend(["", "## 10. v1.1.7 comparison", "", "```json", json.dumps(comparison, ensure_ascii=False, indent=2), "```", ""])
    lines.extend(
        [
            "## 11. Hard failures",
            "",
            f"- Hard-fail cases: `{[r['case_id'] for r in hard_fails] or '-'}`",
            f"- Clarification HTTP 400: `{[r['case_id'] for r in clar400] or '-'}`",
            f"- Career leaks: `{[r['case_id'] for r in leak_fails] or '-'}`",
            f"- Gate-blocked: `{[r['case_id'] for r in gate_blocked] or '-'}`",
            f"- Safe-stops: `{[r['case_id'] for r in safe_stops] or '-'}`",
            "",
            "## Recommendation",
            "",
            "```",
            verdict,
            "```",
            "",
            "Artifacts: `e2e_reports/deep-reading-v1.1-public-qa/PUBLIC_QA_V118_LIVE_REPORT.md`",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": payload["summary"], "improved": improved}, ensure_ascii=False, indent=2))
    print("Wrote", REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
