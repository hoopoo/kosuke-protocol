#!/usr/bin/env python3
"""Staging Public QA for Parallel Life Deep Reading v1.1.9-exp.

BranchSemantics authority + clarification exit.
Same 10 fixtures as v1.1.7/v1.1.8. No auto-tune. Production untouched.
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
    CALL_1_PROMPT_VERSION_V119,
    RUNTIME_VERSION_V119_EXP,
    career_template_leakage,
)
from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    claim_text_is_malformed,
    re_branch_realization_check,
    section_resume_flags,
    abstract_vocabulary_density,
)
from scripts.run_staging_v11_context_pack_live_ab import (  # noqa: E402
    NTT_PACK_ITEMS,
    NTT_SOURCE,
    PROD_API,
    STAGING_API,
    _aq_list,
    _view,
    build_approved_pack,
    probe_flags,
    req,
)
from scripts.run_staging_v117_public_qa import CASES, _section_bodies  # noqa: E402
from scripts.run_staging_v118_public_qa import (  # noqa: E402
    CAREER_LEAK_FAMILY,
    CAREER_LEAK_ROMANCE,
    CAUSAL_RE,
    COACHING_RE,
    CREATIVE_ENT_LEAK,
    EDU_MOBILITY_LEAK,
    SCHEMA_LEAK_RE,
    SEM_FIELDS,
    _answer_payload,
    career_leak_check,
    extract_sem,
    score_case,
    verify_pins as verify_pins_v118,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-public-qa"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / "BRANCH_SEMANTICS_AUTHORITY_V119_REPORT.md"
RAW = OUT / "PUBLIC_QA_V119_RAW.json"
PREV_RAW = OUT / "PUBLIC_QA_V118_RAW.json"


def verify_pins() -> dict[str, Any]:
    """Reuse v118 probe shape but expect v1.1.9 pins."""
    pins = verify_pins_v118()
    # Overlay expected versions for readiness check
    pins["expected"] = {
        "call1": CALL_1_PROMPT_VERSION_V119,
        "runtime": RUNTIME_VERSION_V119_EXP,
    }
    return pins


def confirm_with_clarification_loop(
    api: str, sid: str, session: dict, case: dict
) -> tuple[int, dict, dict]:
    """Answer → approve loop with v1.1.9 terminal exit awareness."""
    clarification: dict[str, Any] = {
        "rounds": [],
        "http_400_on_needs_additional_input": False,
        "duplicate_questions": [],
        "schema_leakage": False,
        "continued_after_clarification": False,
        "infinite_loop_suspected": False,
        "final_status": None,
        "clarification_required_flags": [],
        "exit_reason": None,
    }
    seen_q: list[str] = []
    view = _view(session)
    ctx = [c for c in (view.get("current_context") or []) if str(c).strip()]
    if not ctx:
        view["current_context"] = ["いまの暮らしと仕事の具体的な場面が続いている"]
    pq = [q for q in (view.get("present_questions") or []) if str(q).strip()]
    if not pq:
        view["present_questions"] = ["あのとき別の道を選んでいたら、いまはどうだったか"]

    for round_i in range(5):
        call1 = session.get("call1") or {}
        status = call1.get("status") or session.get("status")
        if status == "insufficient_for_deep_reading":
            clarification["final_status"] = status
            return 200, {"session": session, "status": status}, clarification

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
                    "resp_status": (
                        answered.get("status") if isinstance(answered, dict) else None
                    ),
                    "clarification_required": (
                        answered.get("clarification_required")
                        if isinstance(answered, dict)
                        else None
                    ),
                    "exit_reason": (
                        answered.get("clarification_exit_reason")
                        if isinstance(answered, dict)
                        else None
                    ),
                }
            )
            if code == 400 and status == "needs_additional_input":
                clarification["http_400_on_needs_additional_input"] = True
            if code != 200:
                clarification["final_status"] = status
                return (
                    code,
                    answered if isinstance(answered, dict) else {"detail": answered},
                    clarification,
                )
            session = answered.get("session") or {}
            view = _view(session)
            clarification["continued_after_clarification"] = True
            clarification["exit_reason"] = answered.get("clarification_exit_reason")
            if SCHEMA_LEAK_RE.search(json.dumps(answered, ensure_ascii=False)):
                clarification["schema_leakage"] = True
            st = answered.get("status") or (session.get("call1") or {}).get("status")
            if st == "insufficient_for_deep_reading":
                clarification["final_status"] = st
                return 200, answered, clarification

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
                "resp_status": (
                    confirmed.get("status") if isinstance(confirmed, dict) else None
                ),
                "clarification_required": (
                    confirmed.get("clarification_required")
                    if isinstance(confirmed, dict)
                    else None
                ),
                "questions": (
                    confirmed.get("questions") if isinstance(confirmed, dict) else None
                ),
                "exit_reason": (
                    confirmed.get("clarification_exit_reason")
                    if isinstance(confirmed, dict)
                    else None
                ),
            }
        )
        if code == 400:
            prev = session.get("status") or (session.get("call1") or {}).get("status")
            if prev == "needs_additional_input":
                clarification["http_400_on_needs_additional_input"] = True
            clarification["final_status"] = prev
            return (
                code,
                confirmed if isinstance(confirmed, dict) else {"detail": confirmed},
                clarification,
            )
        if code != 200:
            clarification["final_status"] = session.get("status")
            return (
                code,
                confirmed if isinstance(confirmed, dict) else {"detail": confirmed},
                clarification,
            )

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
        clarification["exit_reason"] = confirmed.get("clarification_exit_reason")
        if status in {"ready_for_draft", "insufficient_for_deep_reading"}:
            return code, confirmed, clarification
        if not confirmed.get("clarification_required") and status not in {
            "needs_additional_input",
            "structural_ambiguity",
            "insufficient_current_context",
            "sensitive_domain_clarification_required",
        }:
            return code, confirmed, clarification

    clarification["infinite_loop_suspected"] = True
    return 200, {"session": session, "status": clarification["final_status"]}, clarification


def run_pipeline_v119(
    api: str,
    *,
    case_id: str,
    source: str,
    pack: dict | None,
    case: dict,
) -> dict:
    from scripts.run_staging_v118_public_qa import run_pipeline_v118

    # Monkey-patch confirmation loop for this process
    import scripts.run_staging_v118_public_qa as m118

    original = m118.confirm_with_clarification_loop
    m118.confirm_with_clarification_loop = confirm_with_clarification_loop
    try:
        out = run_pipeline_v118(
            api, case_id=case_id, source=source, pack=pack, case=case
        )
    finally:
        m118.confirm_with_clarification_loop = original
    # Relocate session dump path marker
    out["qa_version"] = "v1.1.9-exp"
    return out


def classify_section_realization_failure(scored: dict, pipe: dict) -> dict[str, Any]:
    """Taxonomy for gate-blocked / non-publishable cases (no auto-tune)."""
    if scored.get("publishable"):
        return {"applicable": False}
    call1 = ((pipe.get("stages") or {}).get("ground") or {}).get("call1") or {}
    # Prefer final session contracts via scored
    contracts = (
        (scored.get("branch_semantics") and {})
        or {}
    )
    # Use pipeline manuscript absence / blocking
    blocking = scored.get("blocking_reasons") or []
    sec = scored.get("section_realization") or {}
    malformed = scored.get("malformed_claims") or []
    leak = (scored.get("career_leak") or {}).get("leaks") or []

    reasons: list[str] = []
    if leak:
        reasons.append("semantic_mismatch")
    if not sec.get("lost") and not sec.get("protected") and not sec.get("residue"):
        # Could be manuscript omission or contract unsupported
        if any("section" in str(b).lower() or "realization" in str(b).lower() for b in blocking):
            reasons.append("manuscript_omission")
        else:
            reasons.append("claim_weak")
    elif not (sec.get("lost") and sec.get("protected") and sec.get("residue")):
        if malformed:
            reasons.append("claim_weak")
        elif any("required_section" in str(b) for b in blocking):
            reasons.append("manuscript_omission")
        else:
            reasons.append("validator_too_strict")
    if any("title" in str(b).lower() for b in blocking):
        reasons.append("validator_too_strict")
    if scored.get("call1_status") == "insufficient_for_deep_reading":
        reasons.append("contract_unsupported")
    if not reasons:
        if blocking:
            reasons.append("validator_too_strict")
        else:
            reasons.append("claim_weak")

    return {
        "applicable": True,
        "primary": reasons[0],
        "all": reasons,
        "blocking_reasons": blocking[:12],
        "section_realization": sec,
        "malformed_claims": malformed,
        "career_leaks": leak,
    }


def enhance_score(case: dict, pipe: dict, session: dict) -> dict:
    scored = score_case(case, pipe, session)
    clar = pipe.get("clarification") or {}
    scored["clarification"]["infinite_loop_suspected"] = bool(
        clar.get("infinite_loop_suspected")
    )
    scored["clarification"]["exit_reason"] = clar.get("exit_reason")
    scored["clarification"]["final_status"] = clar.get("final_status") or scored[
        "clarification"
    ].get("final_status")
    # semantic_domain_leak from contracts diagnostics
    call1 = session.get("call1") or {}
    sc = call1.get("section_contracts") or {}
    leak_diag = (sc.get("diagnostics") or {}).get("semantic_domain_leak") or {}
    scored["semantic_domain_leak"] = leak_diag
    if leak_diag.get("leaked"):
        hard = list(scored.get("hard_failures") or [])
        hard.append("semantic_domain_leak")
        scored["hard_failures"] = hard
        if scored.get("classification") != "HARD_FAIL":
            scored["classification"] = "HARD_FAIL"
    # Stronger education/creative leak surface on structural_shift
    contracts = (sc.get("contracts") or [])
    chosen = next((c for c in contracts if c.get("section_id") == "chosen_path"), {})
    shift = chosen.get("structural_shift") or ""
    cat = (case.get("category") or "").lower()
    if ("education" in cat or "creative" in cat) and (
        "仕事を定義し直" in shift or "所属が変わるたびに" in shift
    ):
        leaks = list((scored.get("career_leak") or {}).get("leaks") or [])
        tag = (
            "education_auto_career_mobility"
            if "education" in cat
            else "creative_auto_entrepreneurship_metric"
        )
        if tag not in leaks:
            leaks.append(tag)
        scored["career_leak"] = {"leaks": leaks, "ok": False}
        hard = list(scored.get("hard_failures") or [])
        if not any(str(h).startswith("career_template_leakage") for h in hard):
            hard.append("career_template_leakage:" + ",".join(leaks))
        scored["hard_failures"] = hard
        scored["classification"] = "HARD_FAIL"
    if clar.get("infinite_loop_suspected"):
        hard = list(scored.get("hard_failures") or [])
        hard.append("clarification_infinite_loop")
        scored["hard_failures"] = hard
        scored["classification"] = "HARD_FAIL"
    scored["realization_taxonomy"] = classify_section_realization_failure(scored, pipe)
    return scored


def main() -> int:
    # Patch verify to check v119
    flags = probe_flags()
    pack = build_approved_pack(NTT_PACK_ITEMS)
    code, grounded = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": NTT_SOURCE,
            "deep_reading_mode": "contextual",
            "context_pack": pack,
            "clarifications": {},
            "language": "ja",
        },
    )
    session = (grounded or {}).get("session") or {} if isinstance(grounded, dict) else {}
    call1 = session.get("call1") or {}
    staging_call1 = (
        (session.get("prompt_versions") or {}).get("call_1")
        or (session.get("model_metadata") or {}).get("call_1_prompt_version")
        or call1.get("prompt_version")
    )
    staging_schema = session.get("schema_version")
    sem_present = bool(call1.get("branch_semantics"))
    code_s, grounded_s = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": NTT_SOURCE[:200],
            "deep_reading_mode": "strict",
            "clarifications": {},
            "language": "ja",
        },
    )
    sess_s = (grounded_s or {}).get("session") or {} if isinstance(grounded_s, dict) else {}
    strict_call1 = (sess_s.get("prompt_versions") or {}).get("call_1") or (
        sess_s.get("call1") or {}
    ).get("prompt_version")
    code_p, grounded_p = req(
        PROD_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": NTT_SOURCE[:200],
            "deep_reading_mode": "contextual",
            "context_pack": pack,
            "clarifications": {},
            "language": "ja",
        },
    )
    sess_p = (grounded_p or {}).get("session") or {} if isinstance(grounded_p, dict) else {}
    prod_pack = sess_p.get("context_pack")
    prod_call1 = (sess_p.get("prompt_versions") or {}).get("call_1") or (
        sess_p.get("call1") or {}
    ).get("prompt_version")

    pins = {
        "staging_contextual": {
            "http": code,
            "call1": staging_call1,
            "schema": staging_schema,
            "pack": bool(session.get("context_pack") or call1.get("context_pack_usage")),
            "branch_semantics_present": sem_present,
            "domain": (call1.get("branch_semantics") or {}).get("domain"),
            "allows_career": (
                (call1.get("branch_semantics") or {}).get("diagnostics") or {}
            ).get("allows_career_product_logic"),
        },
        "staging_strict": {"http": code_s, "call1": strict_call1},
        "production": {
            "http": code_p,
            "call1": prod_call1,
            "pack": prod_pack if prod_pack is not None else None,
        },
        "flags": flags,
        "expected": {
            "call1": CALL_1_PROMPT_VERSION_V119,
            "runtime": RUNTIME_VERSION_V119_EXP,
        },
    }
    (OUT / "pin_verify_v119.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V119
        and (
            pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V119_EXP
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
            "# Branch Semantics Authority v1.1.9 ABORTED — pins not ready\n\n```json\n"
            + json.dumps(pins, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        return 2

    results: list[dict] = []
    pipelines: dict[str, dict] = {}
    for i, case in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] {case['id']} ...", flush=True)
        pack_case = (
            build_approved_pack(case["pack_items"]) if case.get("pack_items") else None
        )
        pipe = run_pipeline_v119(
            STAGING_API,
            case_id=case["id"],
            source=case["source"],
            pack=pack_case,
            case=case,
        )
        pipelines[case["id"]] = pipe
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
        # Fallbacks from pipeline stages when dump missing
        if not session.get("call1"):
            for key in ("edit", "confirm", "ground"):
                st = (pipe.get("stages") or {}).get(key) or {}
                # not always nested; use branch_semantics_final / after_confirm
                break
            if pipe.get("branch_semantics_final") or pipe.get("branch_semantics_after_confirm"):
                session = {
                    "call1": {
                        "branch_semantics": pipe.get("branch_semantics_final")
                        or pipe.get("branch_semantics_after_confirm"),
                        "status": (pipe.get("clarification") or {}).get("final_status"),
                    },
                    "call3": {
                        "body_markdown": (pipe.get("manuscript") or {}).get(
                            "body_markdown"
                        ),
                        "final_title": (pipe.get("manuscript") or {}).get("title"),
                        "validation": {},
                    },
                    "status": (pipe.get("clarification") or {}).get("final_status"),
                }
        scored = enhance_score(case, pipe, session)
        scored["pipeline_error"] = bool(pipe.get("error"))
        scored["stages"] = pipe.get("stages")
        results.append(scored)
        case_dir = OUT / "v119" / case["id"]
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
    clar_loops = [
        r for r in results if r.get("clarification", {}).get("infinite_loop_suspected")
    ]
    gate_blocked = [r for r in results if r.get("classification") == "GATE_BLOCKED"]
    sdl = [r for r in results if (r.get("semantic_domain_leak") or {}).get("leaked")]

    # Compare with v118
    prev = {}
    if PREV_RAW.exists():
        prev = json.loads(PREV_RAW.read_text(encoding="utf-8"))
    prev_results = {r["case_id"]: r for r in (prev.get("results") or [])}

    def _sem_before_after(case_id: str) -> dict:
        before = (prev_results.get(case_id) or {}).get("branch_semantics") or {}
        after = next((r for r in results if r["case_id"] == case_id), {})
        after_sem = after.get("branch_semantics") or {}
        return {
            "before_domain": before.get("domain"),
            "after_domain": after_sem.get("domain"),
            "before_tension": (before.get("central_tension") or "")[:160],
            "after_tension": (after_sem.get("central_tension") or "")[:160],
            "before_leaks": (prev_results.get(case_id) or {})
            .get("career_leak", {})
            .get("leaks"),
            "after_leaks": after.get("career_leak", {}).get("leaks"),
            "before_class": (prev_results.get(case_id) or {}).get("classification"),
            "after_class": after.get("classification"),
            "after_chosen_shift": "",
        }

    edu = _sem_before_after("case03_education")
    cre = _sem_before_after("case07_creative")
    # Attach chosen structural_shift from v119 artifacts
    for label, cid in (("edu", "case03_education"), ("cre", "case07_creative")):
        sp = OUT / "v119" / cid / "pipeline.json"
        shift = ""
        if sp.exists():
            pipe = json.loads(sp.read_text(encoding="utf-8"))
            sess = pipe.get("session_final") or {}
            contracts = (
                ((sess.get("call1") or {}).get("section_contracts") or {}).get(
                    "contracts"
                )
                or []
            )
            chosen = next(
                (c for c in contracts if c.get("section_id") == "chosen_path"), {}
            )
            shift = chosen.get("structural_shift") or ""
        if label == "edu":
            edu["after_chosen_shift"] = shift
        else:
            cre["after_chosen_shift"] = shift

    career_leak_count = len(leak_fails) + len(sdl)
    # Unique cases
    leak_case_ids = {
        r["case_id"]
        for r in results
        if r.get("career_leak", {}).get("leaks")
        or (r.get("semantic_domain_leak") or {}).get("leaked")
    }
    career_leak_count = len(leak_case_ids)
    clar_loop_count = len(clar_loops)

    if career_leak_count > 0 or clar_loop_count > 0 or clar400:
        verdict = "V1.1.9 NOT READY — STOP (leak or clarification loop)"
    elif gate_blocked and len(publishable_cases) < 3:
        verdict = (
            "V1.1.9 LEAK/LOOP FIXED — section realization still blocks many cases"
        )
    elif publishable_cases and not hard_fails:
        verdict = "V1.1.9 PROMISING"
    else:
        verdict = "V1.1.9 PARTIAL"

    taxonomies = {
        r["case_id"]: r.get("realization_taxonomy")
        for r in results
        if r.get("classification") == "GATE_BLOCKED"
        or (
            not r.get("publishable")
            and r.get("classification") not in {"PASS_SAFE_STOP", "HARD_FAIL"}
        )
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "verdict": verdict,
        "summary": {
            "cases": len(results),
            "publishable": len(publishable_cases),
            "gate_blocked": len(gate_blocked),
            "hard_fails": len(hard_fails),
            "career_leak_cases": career_leak_count,
            "clarification_http_400": len(clar400),
            "clarification_infinite_loops": clar_loop_count,
            "semantic_domain_leak_cases": len(sdl),
        },
        "education_before_after": edu,
        "creative_before_after": cre,
        "realization_taxonomy": taxonomies,
        "results": results,
    }
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Parallel Life Deep Reading v1.1.9-exp — Branch Semantics Authority Report",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Staging: `{STAGING_API}`  ",
        "Production: **untouched**  ",
        "",
        "## Verdict",
        "",
        f"```\n{verdict}\n```",
        "",
        "## 1. Downstream career leak source (v1.1.8 root)",
        "",
        "- `_has_employment_regime` / Chosen Path `structural_shift` treated Context Pack",
        "  `career_history` / `current_work` as template authority.",
        "- Education/creative BranchSemantics domain could be `mixed` while career",
        "  mobility copy (`所属が変わるたびに自分の仕事を定義し直す`) was still injected.",
        "",
        "## 2. Domain authority rule (v1.1.9)",
        "",
        "- Primary semantic source: **BranchSemantics**",
        "- `allows_career_product_logic(sem)` required for career templates",
        "- Pack employment = `background_employment_context` only",
        "- If `domain ∈ non-career` OR `changed_dimension` not employment-related →",
        "  employment helpers must not inject redefine-work / salary / accumulation framing",
        "",
        "## 3. Education before / after",
        "",
        "```json",
        json.dumps(edu, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 4. Creative before / after",
        "",
        "```json",
        json.dumps(cre, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 5. semantic_domain_leak diagnostics",
        "",
        f"- Cases with leaked=true: **{len(sdl)}**",
        "",
    ]
    for r in results:
        sdl_r = r.get("semantic_domain_leak") or {}
        lines.append(
            f"- `{r['case_id']}` domain=`{(r.get('branch_semantics') or {}).get('domain')}` "
            f"leaked=`{sdl_r.get('leaked')}` hits=`{sdl_r.get('hits')}`"
        )

    lines += [
        "",
        "## 6. Clarification-loop root cause",
        "",
        "- Creative (and similar) stayed in `needs_additional_input` because gates re-asked",
        "  equivalent present-context questions after `answer`, with no round bound.",
        "- Approve while clarifying returned HTTP 200 (v1.1.8) but could still loop.",
        "",
        "## 7. Clarification exit behavior",
        "",
        f"- Max rounds: **{2}**",
        "- Duplicate / already-satisfied questions suppressed",
        "- After max: structurally sufficient → proceed; else `insufficient_for_deep_reading` (HTTP 200)",
        f"- Infinite-loop suspected cases: **{clar_loop_count}**",
        f"- HTTP 400 on needs_additional_input: **{len(clar400)}**",
        "",
        "## 8. 10-case rerun",
        "",
        "| Case | Domain | Pub | Leak | Clar400 | Loop | Class | Realization |",
        "|------|--------|-----|------|---------|------|-------|-------------|",
    ]
    for r in results:
        tax = r.get("realization_taxonomy") or {}
        lines.append(
            "| {cid} | {dom} | {pub} | {leak} | {c400} | {loop} | {cls} | {tax} |".format(
                cid=r["case_id"],
                dom=(r.get("branch_semantics") or {}).get("domain"),
                pub=r.get("publishable"),
                leak=",".join((r.get("career_leak") or {}).get("leaks") or []) or "-",
                c400=r.get("clarification", {}).get("http_400"),
                loop=r.get("clarification", {}).get("infinite_loop_suspected"),
                cls=r.get("classification"),
                tax=(tax.get("primary") if tax.get("applicable") else "-"),
            )
        )

    lines += [
        "",
        "## 9. Publishable count",
        "",
        f"**{len(publishable_cases)} / {len(results)}**",
        "",
        "## 10. Remaining section-realization failures",
        "",
        "```json",
        json.dumps(taxonomies, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 11. Production untouched confirmation",
        "",
        f"- Production Call1: `{prod_call1}`",
        f"- Production pack: `{prod_pack}` (must be false/null)",
        f"- production_context_pack_off: `{flags.get('production_context_pack_off')}`",
        f"- Staging Contextual Call1: `{staging_call1}`",
        f"- Staging schema: `{staging_schema}`",
        "",
        "## 12. Recommendation",
        "",
    ]
    if career_leak_count > 0 or clar_loop_count > 0:
        lines.append(
            "STOP per stop-rule. Do not auto-tune section realization until leak/loop = 0."
        )
    elif len(gate_blocked) >= 4:
        lines.append(
            "Career leak and clarification loop targets met (or nearly). "
            "Next: targeted section-realization quality work only — no gate loosening."
        )
    else:
        lines.append(
            "Continue Public QA monitoring; consider release-candidate review if publishable quality holds."
        )

    lines += [
        "",
        "## Summary metrics",
        "",
        "```json",
        json.dumps(payload["summary"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": payload["summary"]}, ensure_ascii=False, indent=2))
    return 0 if career_leak_count == 0 and clar_loop_count == 0 and not clar400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
