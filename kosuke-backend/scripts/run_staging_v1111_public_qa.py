#!/usr/bin/env python3
"""Staging Public QA for Parallel Life Deep Reading v1.1.11-exp (Track B).

Targeted editorial realization. Track A frozen. Production untouched.
"""

from __future__ import annotations

import argparse
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
    CALL_1_PROMPT_VERSION_V1111,
    RUNTIME_VERSION_V1111_EXP,
)
from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    LOCKED_PUBLIC_LABELS_JA,
    normalize_markdown_section_headings,
    parse_locked_sections,
)
from scripts.run_staging_v11_context_pack_live_ab import (  # noqa: E402
    NTT_PACK_ITEMS,
    NTT_SOURCE,
    PROD_API,
    STAGING_API,
    build_approved_pack,
    probe_flags,
    req,
)
from scripts.run_staging_v117_public_qa import CASES  # noqa: E402
from scripts.run_staging_v119_public_qa import (  # noqa: E402
    confirm_with_clarification_loop,
    enhance_score,
)
from scripts.run_staging_v1110_public_qa import (  # noqa: E402
    deterministic_diagnostics,
    load_session,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-public-qa"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / "TARGETED_EDITORIAL_V1111_REPORT.md"
RAW = OUT / "PUBLIC_QA_V1111_RAW.json"
PREV_RAW = OUT / "PUBLIC_QA_V1110_RAW.json"

TARGET4 = {
    "case01_career",
    "case03_education",
    "case04_romance",
    "case05_health",
}


def verify_pins() -> dict[str, Any]:
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
    staging_schema = session.get("schema_version") or call1.get("schema_version")
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
    pins = {
        "staging_contextual": {
            "http": code,
            "call1": staging_call1,
            "schema": staging_schema,
            "pack": bool(session.get("context_pack") or call1.get("context_pack_usage")),
        },
        "staging_strict": {"http": code_s, "call1": strict_call1},
        "production": {
            "http": code_p,
            "call1": (sess_p.get("prompt_versions") or {}).get("call_1")
            or (sess_p.get("call1") or {}).get("prompt_version"),
            "schema": sess_p.get("schema_version"),
            "pack": sess_p.get("context_pack"),
        },
        "flags": flags,
        "expected": {
            "call1": CALL_1_PROMPT_VERSION_V1111,
            "runtime": RUNTIME_VERSION_V1111_EXP,
        },
    }
    (OUT / "pin_verify_v1111.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return pins


def pins_ready(pins: dict[str, Any]) -> bool:
    return (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V1111
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V1111_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
        and pins["flags"].get("production_context_pack_off") is True
    )


def run_pipeline_v1111(api: str, *, case_id: str, source: str, pack: dict | None, case: dict) -> dict:
    import scripts.run_staging_v118_public_qa as m118
    from scripts.run_staging_v119_public_qa import run_pipeline_v119

    original = m118.confirm_with_clarification_loop
    m118.confirm_with_clarification_loop = confirm_with_clarification_loop
    try:
        out = run_pipeline_v119(api, case_id=case_id, source=source, pack=pack, case=case)
    finally:
        m118.confirm_with_clarification_loop = original
    out["qa_version"] = "v1.1.11-exp"
    return out


def editorial_section_ok(case_id: str, scored: dict, pipe: dict) -> dict[str, Any]:
    body = ((pipe.get("manuscript") or {}).get("body_markdown") or "")
    blocking = [str(b) for b in (scored.get("blocking_reasons") or [])]
    hard = [str(h) for h in (scored.get("hard_failures") or [])]
    secs = parse_locked_sections(normalize_markdown_section_headings(body)) if body else {}
    if case_id == "case01_career":
        ok = not any("chosen_path" in b for b in blocking)
        return {"target": "chosen_path", "ok": ok, "excerpt": (secs.get("選んだ道") or "")[:220]}
    if case_id == "case03_education":
        re_fail = any("re_branch" in b for b in blocking)
        # valid omission: no re_branch section and no unrealized block
        omitted = "これからの再分岐" not in secs and not re_fail
        ok = (not re_fail) or omitted
        return {
            "target": "re_branch",
            "ok": ok,
            "omitted_valid": omitted,
            "excerpt": (secs.get("これからの再分岐") or "")[:220],
        }
    if case_id == "case04_romance":
        ok = not any("branch_point" in b for b in blocking)
        return {"target": "branch_point", "ok": ok, "excerpt": (secs.get("分岐点") or "")[:220]}
    if case_id == "case05_health":
        causal = any("unsupported_causality" in b for b in blocking) or any(
            "causality" in h for h in hard
        )
        lost_fail = any(":lost" in b or b.endswith("lost") for b in blocking)
        return {
            "target": "causality+lost",
            "ok": (not causal) and (not lost_fail),
            "unsupported_causality": causal,
            "lost_ok": not lost_fail,
            "excerpt_lost": (secs.get("失ったもの") or "")[:220],
            "hard": hard,
        }
    return {"target": "n/a", "ok": True}


def track_a_regressions(scored: dict) -> list[str]:
    d = scored.get("deterministic") or {}
    regs: list[str] = []
    for k in (
        "observatory_false_negative",
        "locked_label_mutation",
        "heading_parser_inline_miss",
        "heading_parser_period_form",
        "clarification_dead_end",
    ):
        if d.get(k):
            regs.append(k)
    if (scored.get("semantic_domain_leak") or {}).get("leaked"):
        regs.append("semantic_domain_leak")
    return regs


def run_cases(case_ids: set[str] | None) -> list[dict]:
    results: list[dict] = []
    selected = [c for c in CASES if case_ids is None or c["id"] in case_ids]
    for i, case in enumerate(selected, 1):
        print(f"[{i}/{len(selected)}] {case['id']} ...", flush=True)
        pack_case = (
            build_approved_pack(case["pack_items"]) if case.get("pack_items") else None
        )
        pipe = run_pipeline_v1111(
            STAGING_API,
            case_id=case["id"],
            source=case["source"],
            pack=pack_case,
            case=case,
        )
        session = load_session(case["id"])
        if not session.get("call1"):
            session = {
                "call1": {
                    "branch_semantics": pipe.get("branch_semantics_final")
                    or pipe.get("branch_semantics_after_confirm"),
                    "section_contracts": pipe.get("section_contracts"),
                    "status": (pipe.get("clarification") or {}).get("final_status"),
                },
                "call3": {
                    "body_markdown": (pipe.get("manuscript") or {}).get("body_markdown"),
                },
                "model_metadata": pipe.get("model_metadata") or {},
                "status": (pipe.get("clarification") or {}).get("final_status"),
            }
        scored = enhance_score(case, pipe, session)
        scored["pipeline_error"] = bool(pipe.get("error"))
        scored["deterministic"] = deterministic_diagnostics(scored, pipe, session)
        scored["editorial_target"] = editorial_section_ok(case["id"], scored, pipe)
        scored["track_a_regressions"] = track_a_regressions(scored)
        # attach contracts / sem for report
        call1 = session.get("call1") or {}
        scored["branch_semantics"] = call1.get("branch_semantics") or scored.get(
            "branch_semantics"
        )
        results.append(scored)
        case_dir = OUT / "v1111" / case["id"]
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
    return results


def write_report(
    *,
    pins: dict,
    target_results: list[dict],
    full_results: list[dict],
) -> dict[str, Any]:
    prev = {}
    if PREV_RAW.exists():
        prev = json.loads(PREV_RAW.read_text(encoding="utf-8"))
    prev_by = {r["case_id"]: r for r in (prev.get("results") or [])}

    publishable = [r for r in full_results if r.get("publishable")]
    hard = [r for r in full_results if r.get("hard_failures")]
    sdl = [r for r in full_results if (r.get("semantic_domain_leak") or {}).get("leaked")]
    gate = [r for r in full_results if r.get("classification") == "GATE_BLOCKED"]
    regs = [r for r in full_results if r.get("track_a_regressions")]
    target_ok = all((r.get("editorial_target") or {}).get("ok") for r in target_results)
    health_causal_left = any(
        (r.get("editorial_target") or {}).get("unsupported_causality")
        for r in target_results
        if r["case_id"] == "case05_health"
    )

    if regs or health_causal_left or not target_ok:
        verdict = "V1.1.11 STOP — targeted failure or Track A regression"
    else:
        verdict = (
            "V1.1.11 TARGETED EDITORIAL PASS — do not chase 10/10; review matrix"
        )

    legitimate = [
        {
            "case_id": r["case_id"],
            "classification": r.get("classification"),
            "status": (r.get("deterministic") or {}).get("final_status"),
            "note": "non-publishable but not a targeted Track B miss"
            if not r.get("publishable")
            and (r.get("editorial_target") or {}).get("ok", True)
            else "remaining failure",
        }
        for r in full_results
        if not r.get("publishable")
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "verdict": verdict,
        "targeted_ok": target_ok and not regs and not health_causal_left,
        "summary": {
            "cases": len(full_results),
            "publishable": len(publishable),
            "gate_blocked": len(gate),
            "hard_fails": len(hard),
            "semantic_domain_leak": len(sdl),
            "track_a_regression_cases": len(regs),
        },
        "target4": [
            {
                "case_id": r["case_id"],
                "publishable": r.get("publishable"),
                "classification": r.get("classification"),
                "blocking": (r.get("blocking_reasons") or [])[:8],
                "editorial_target": r.get("editorial_target"),
                "track_a_regressions": r.get("track_a_regressions"),
            }
            for r in target_results
        ],
        "v1110_compare": {
            cid: {
                "v1110_pub": (prev_by.get(cid) or {}).get("publishable"),
                "v1110_class": (prev_by.get(cid) or {}).get("classification"),
                "v1111_pub": r.get("publishable"),
                "v1111_class": r.get("classification"),
            }
            for cid, r in ((x["case_id"], x) for x in full_results)
        },
        "legitimate_non_publishable": legitimate,
        "results": full_results,
    }
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Parallel Life Deep Reading v1.1.11-exp — Targeted Editorial Report",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Staging: `{STAGING_API}`  ",
        "Production: **untouched**  ",
        "",
        "## Verdict",
        "",
        f"```\n{verdict}\n```",
        "",
        "## 1. Career chosen_path fix",
        "",
        "- Contract structural_shift: one-institution continuity → work across organizations",
        "- Realization accepts structural cues (一つの所属 / 移り方 / 組織を移) without requiring employment-metric jargon",
        "- Anti-résumé: chronology-only still fails",
        "",
        "## 2. Education re_branch fix / omission",
        "",
        "- Re-branch place from BranchSemantics domain (not pack「仕事の場」)",
        "- reconsider release: 「固定しなくてよい」; ensure_rebranch restores quiet decision",
        "- Zero / valid omission still allowed when modes empty",
        "",
        "## 3. Romance branch_point fix",
        "",
        "- Contract first-paragraph fork: trigger + chosen + unchosen + 境界",
        "- Realization accepts 境目 as 境界 synonym",
        "",
        "## 4. Health causality trace / fix",
        "",
        "- Exact trip: 「働き方を変えるかを考えた」 matched assertion pattern 「を変える」",
        "- Detector unchanged; manuscript rewrite → 「働き方をどう置くかを考え」",
        "- Also neutralize 「によって」「つながっている」frames in thesis_link / finalize",
        "",
        "## 5. Health Lost result",
        "",
        "- Lost meaning from health BranchSemantics: bodily condition / unverifiable configuration",
        "- Realization accepts 検証することはできない / 身体条件 / 同じようには辿",
        "",
        "## 6. Targeted 4-case results",
        "",
        "| Case | Pub | Target OK | Class | Blocking |",
        "|------|-----|-----------|-------|----------|",
    ]
    for r in target_results:
        et = r.get("editorial_target") or {}
        lines.append(
            "| {cid} | {pub} | {ok} | {cls} | {blk} |".format(
                cid=r["case_id"],
                pub=r.get("publishable"),
                ok=et.get("ok"),
                cls=r.get("classification"),
                blk=", ".join((r.get("blocking_reasons") or [])[:3]) or "-",
            )
        )

    lines += [
        "",
        "```json",
        json.dumps(payload["target4"], ensure_ascii=False, indent=2),
        "```",
        "",
        "## 7. Full 10-case rerun (v1.1.10 → v1.1.11)",
        "",
        "| Case | v1110 Pub | v1111 Pub | Class | TrackA reg |",
        "|------|-----------|-----------|-------|------------|",
    ]
    for r in full_results:
        prev_r = prev_by.get(r["case_id"]) or {}
        lines.append(
            "| {cid} | {p0} | {p1} | {cls} | {reg} |".format(
                cid=r["case_id"],
                p0=prev_r.get("publishable"),
                p1=r.get("publishable"),
                cls=r.get("classification"),
                reg=",".join(r.get("track_a_regressions") or []) or "-",
            )
        )

    lines += [
        "",
        "## 8. Publishable count",
        "",
        f"**{len(publishable)} / {len(full_results)}**",
        "",
        "## 9. Legitimate non-publishable cases",
        "",
        "```json",
        json.dumps(legitimate, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 10. Track A regression check",
        "",
        f"- Cases with Track A regressions: **{len(regs)}**",
        f"- semantic_domain_leak: **{len(sdl)}**",
        "",
        "## 11. Production untouched confirmation",
        "",
        f"- Production Call1: `{pins['production'].get('call1')}`",
        f"- Production schema: `{pins['production'].get('schema')}`",
        f"- Production pack: `{pins['production'].get('pack')}`",
        f"- production_context_pack_off: `{pins['flags'].get('production_context_pack_off')}`",
        f"- Staging Call1: `{pins['staging_contextual'].get('call1')}`",
        f"- Staging runtime: `{pins['staging_contextual'].get('schema')}`",
        "",
        "## 12. Recommendation",
        "",
    ]
    if not payload["targeted_ok"]:
        lines.append("STOP per stop-rule. Inspect target4 excerpts before further edits.")
    else:
        lines.append(
            "Targeted Track B goals met. Do not chase 10/10. "
            "Next only if new genuine editorial failures appear in the matrix."
        )
    lines += [
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(payload["summary"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["pins", "target4", "full", "all"], default="all")
    args = ap.parse_args()

    pins = verify_pins()
    if not pins_ready(pins):
        print(json.dumps({"error": "pins_not_ready", "pins": pins}, ensure_ascii=False, indent=2))
        REPORT.write_text(
            "# Targeted Editorial v1.1.11 ABORTED — pins not ready\n\n```json\n"
            + json.dumps(pins, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        return 2
    if args.phase == "pins":
        print(json.dumps({"ok": True, "pins": pins}, ensure_ascii=False, indent=2))
        return 0

    target_results: list[dict] = []
    full_results: list[dict] = []
    if args.phase in {"target4", "all"}:
        target_results = run_cases(TARGET4)
        (OUT / "PUBLIC_QA_V1111_TARGET4.json").write_text(
            json.dumps(target_results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if args.phase == "target4":
            payload = write_report(
                pins=pins, target_results=target_results, full_results=target_results
            )
            print(json.dumps({"verdict": payload["verdict"], "target4": payload["target4"]}, ensure_ascii=False, indent=2))
            return 0 if payload["targeted_ok"] else 1

    if args.phase in {"full", "all"}:
        full_results = run_cases(None)
    else:
        full_results = target_results

    payload = write_report(
        pins=pins,
        target_results=target_results
        or [r for r in full_results if r["case_id"] in TARGET4],
        full_results=full_results,
    )
    print(
        json.dumps(
            {"verdict": payload["verdict"], "summary": payload["summary"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload.get("targeted_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
