#!/usr/bin/env python3
"""Staging Public QA for Parallel Life Deep Reading v1.1.10-exp.

Deterministic realization fixes only. Same 10 fixtures as v1.1.7–v1.1.9.
No editorial auto-tune. Production untouched.
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
    CALL_1_PROMPT_VERSION_V1110,
    RUNTIME_VERSION_V1110_EXP,
)
from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    LOCKED_PUBLIC_LABELS_JA,
    LABEL_ALIAS_TO_LOCKED,
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
    run_pipeline_v119,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-public-qa"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / "DETERMINISTIC_REALIZATION_V1110_REPORT.md"
RAW = OUT / "PUBLIC_QA_V1110_RAW.json"
PREV_RAW = OUT / "PUBLIC_QA_V119_RAW.json"

TARGET7 = {
    "case02_family",
    "case06_entrepreneurship",
    "case03_education",
    "case05_health",
    "case04_romance",
    "case07_creative",
    "case09_zero_lens",
}

ALIAS_RE = re.compile(
    r"(?m)^##\s*(?:残されたもの|今に残る問い|失われたもの|選ばなかった道)\s*$"
)
INLINE_HEADING_RE = re.compile(r"[^\n#]##\s*\S")
PERIOD_HEADING_RE = re.compile(r"(?m)^##\s+.+[。．]\s*$")


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
    prod_pack = sess_p.get("context_pack")
    prod_call1 = (sess_p.get("prompt_versions") or {}).get("call_1") or (
        sess_p.get("call1") or {}
    ).get("prompt_version")
    prod_schema = sess_p.get("schema_version")

    pins = {
        "staging_contextual": {
            "http": code,
            "call1": staging_call1,
            "schema": staging_schema,
            "pack": bool(session.get("context_pack") or call1.get("context_pack_usage")),
            "branch_semantics_present": bool(call1.get("branch_semantics")),
        },
        "staging_strict": {"http": code_s, "call1": strict_call1},
        "production": {
            "http": code_p,
            "call1": prod_call1,
            "schema": prod_schema,
            "pack": prod_pack if prod_pack is not None else None,
        },
        "flags": flags,
        "expected": {
            "call1": CALL_1_PROMPT_VERSION_V1110,
            "runtime": RUNTIME_VERSION_V1110_EXP,
        },
    }
    (OUT / "pin_verify_v1110.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return pins


def pins_ready(pins: dict[str, Any]) -> bool:
    return (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V1110
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V1110_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
        and pins["flags"].get("production_context_pack_off") is True
    )


def run_pipeline_v1110(
    api: str,
    *,
    case_id: str,
    source: str,
    pack: dict | None,
    case: dict,
) -> dict:
    import scripts.run_staging_v118_public_qa as m118

    original = m118.confirm_with_clarification_loop
    m118.confirm_with_clarification_loop = confirm_with_clarification_loop
    try:
        out = run_pipeline_v119(
            api, case_id=case_id, source=source, pack=pack, case=case
        )
    finally:
        m118.confirm_with_clarification_loop = original
    out["qa_version"] = "v1.1.10-exp"
    return out


def deterministic_diagnostics(scored: dict, pipe: dict, session: dict) -> dict[str, Any]:
    body = (
        ((pipe.get("manuscript") or {}).get("body_markdown") or "")
        or ((session.get("call3") or {}).get("body_markdown") or "")
    )
    call1 = session.get("call1") or {}
    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    obs = next((c for c in contracts if c.get("section_id") == "observatory"), {})
    blocking = scored.get("blocking_reasons") or []
    obs_unrealized = any("observatory" in str(b) for b in blocking)
    obs_required = bool(obs.get("must_be_present"))
    # False negative heuristic: required OR present section with social prose,
    # but validator still flags observatory unrealized
    social_prose = bool(
        re.search(
            r"(?:社会|並[べび置]|ケア|身体|似た条件|人々|制度|問いが残)",
            body,
        )
    )
    obs_fn = bool(obs_unrealized and social_prose and ("社会との接続" in body or not obs_required))

    aliases = ALIAS_RE.findall(body) if body else []
    # After normalize, aliases should map — check raw manuscript for mutation
    label_mutation = bool(aliases)
    parsed = parse_locked_sections(normalize_markdown_section_headings(body)) if body else {}
    inline_miss = bool(INLINE_HEADING_RE.search(body or ""))
    period_heading = bool(PERIOD_HEADING_RE.search(body or ""))

    clar = scored.get("clarification") or {}
    status = clar.get("final_status") or scored.get("call1_status") or session.get("status")
    draft_reached = bool(
        pipe.get("manuscript")
        or (session.get("call2") or {}).get("body_markdown")
        or (session.get("call3") or {}).get("body_markdown")
        or status in {"ready_for_draft", "draft_ready", "completed", "published"}
        or scored.get("publishable")
    )
    dead_end = bool(
        clar.get("infinite_loop_suspected")
        or (
            status == "ready_for_user_confirmation"
            and not draft_reached
            and clar.get("rounds")
            and len(clar.get("rounds") or []) >= 2
        )
        or clar.get("http_400_on_needs_additional_input")
    )
    # Also: exited clarification but stuck confirm without draft/insufficient
    if (
        clar.get("exit_reason") is None
        and status == "ready_for_user_confirmation"
        and not draft_reached
        and (clar.get("continued_after_clarification") or clar.get("rounds"))
    ):
        dead_end = True

    return {
        "observatory_required": obs_required,
        "observatory_omission_reason": obs.get("omission_reason"),
        "observatory_unrealized_block": obs_unrealized,
        "observatory_false_negative": obs_fn,
        "locked_label_mutation": label_mutation,
        "alias_headings_raw": aliases,
        "parsed_locked_labels": list(parsed.keys()),
        "heading_parser_inline_miss": inline_miss,
        "heading_parser_period_form": period_heading,
        "clarification_dead_end": dead_end,
        "draft_reached": draft_reached,
        "final_status": status,
        "clarification_exit": (session.get("model_metadata") or {}).get(
            "clarification_exit"
        )
        or clar.get("exit_reason"),
    }


def load_session(case_id: str) -> dict:
    sp = (
        ROOT
        / "e2e_reports"
        / "deep-reading-v1.1-context-pack"
        / "live_ab"
        / case_id
        / "public_qa_v118_session_final.json"
    )
    if sp.exists():
        return json.loads(sp.read_text(encoding="utf-8"))
    return {}


def run_cases(case_ids: set[str] | None) -> tuple[list[dict], dict[str, dict]]:
    results: list[dict] = []
    pipelines: dict[str, dict] = {}
    selected = [c for c in CASES if case_ids is None or c["id"] in case_ids]
    for i, case in enumerate(selected, 1):
        print(f"[{i}/{len(selected)}] {case['id']} ...", flush=True)
        pack_case = (
            build_approved_pack(case["pack_items"]) if case.get("pack_items") else None
        )
        pipe = run_pipeline_v1110(
            STAGING_API,
            case_id=case["id"],
            source=case["source"],
            pack=pack_case,
            case=case,
        )
        pipelines[case["id"]] = pipe
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
                    "final_title": (pipe.get("manuscript") or {}).get("title"),
                },
                "model_metadata": pipe.get("model_metadata") or {},
                "status": (pipe.get("clarification") or {}).get("final_status"),
            }
        scored = enhance_score(case, pipe, session)
        scored["pipeline_error"] = bool(pipe.get("error"))
        scored["deterministic"] = deterministic_diagnostics(scored, pipe, session)
        results.append(scored)
        case_dir = OUT / "v1110" / case["id"]
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
    return results, pipelines


def write_report(
    *,
    pins: dict,
    target_results: list[dict],
    full_results: list[dict],
    sensitive: dict | None,
) -> dict[str, Any]:
    prev = {}
    if PREV_RAW.exists():
        prev = json.loads(PREV_RAW.read_text(encoding="utf-8"))
    prev_by = {r["case_id"]: r for r in (prev.get("results") or [])}

    def _count(rows: list[dict], key: str) -> int:
        return sum(1 for r in rows if (r.get("deterministic") or {}).get(key))

    publishable = [r for r in full_results if r.get("publishable")]
    hard = [r for r in full_results if r.get("hard_failures")]
    sdl = [
        r for r in full_results if (r.get("semantic_domain_leak") or {}).get("leaked")
    ]
    obs_fn = _count(full_results, "observatory_false_negative")
    label_mut = _count(full_results, "locked_label_mutation")
    parser_miss = sum(
        1
        for r in full_results
        if (r.get("deterministic") or {}).get("heading_parser_inline_miss")
        or (r.get("deterministic") or {}).get("heading_parser_period_form")
    )
    dead = _count(full_results, "clarification_dead_end")
    gate_blocked = [r for r in full_results if r.get("classification") == "GATE_BLOCKED"]

    det_ok = (
        obs_fn == 0
        and label_mut == 0
        and parser_miss == 0
        and dead == 0
        and len(sdl) == 0
        and not any(
            any(str(h).startswith("hard_safety") or "safety" in str(h).lower() for h in (r.get("hard_failures") or []))
            for r in full_results
        )
    )

    editorial: list[dict] = []
    for r in full_results:
        if r.get("publishable"):
            continue
        det = r.get("deterministic") or {}
        if det.get("observatory_false_negative") or det.get("locked_label_mutation") or det.get(
            "clarification_dead_end"
        ):
            continue
        editorial.append(
            {
                "case_id": r["case_id"],
                "classification": r.get("classification"),
                "blocking": (r.get("blocking_reasons") or [])[:8],
                "section_realization": r.get("section_realization"),
                "call1_status": r.get("call1_status") or det.get("final_status"),
            }
        )

    verdict = (
        "V1.1.10 DETERMINISTIC TARGETS MET — editorial failures remain (Track B not started)"
        if det_ok
        else "V1.1.10 DETERMINISTIC FAILURES REMAIN — STOP"
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "verdict": verdict,
        "deterministic_ok": det_ok,
        "summary": {
            "cases": len(full_results),
            "publishable": len(publishable),
            "gate_blocked": len(gate_blocked),
            "hard_fails": len(hard),
            "semantic_domain_leak": len(sdl),
            "observatory_false_negatives": obs_fn,
            "locked_label_mutations": label_mut,
            "heading_parser_misses": parser_miss,
            "clarification_dead_ends": dead,
        },
        "target7": target_results,
        "sensitive_deterministic": sensitive,
        "v119_compare": {
            cid: {
                "v119_class": (prev_by.get(cid) or {}).get("classification"),
                "v119_pub": (prev_by.get(cid) or {}).get("publishable"),
                "v1110_class": r.get("classification"),
                "v1110_pub": r.get("publishable"),
                "det": r.get("deterministic"),
            }
            for cid, r in ((x["case_id"], x) for x in full_results)
        },
        "remaining_editorial": editorial,
        "results": full_results,
    }
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Parallel Life Deep Reading v1.1.10-exp — Deterministic Realization Report",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Staging: `{STAGING_API}`  ",
        "Production: **untouched**  ",
        "",
        "## Verdict",
        "",
        f"```\n{verdict}\n```",
        "",
        "## 1. Observatory FN root cause / fix",
        "",
        "- **Root cause (v1.1.9):** Observatory realization used employment-oriented keyword expectations;",
        "  family / entrepreneurship prose that realized social-parallel meaning still failed.",
        "- **Fix:** evidence/claim/variant-aware `_observatory_realized`; contract stores",
        "  `supporting_observatory_evidence_ids` + `acceptable_semantic_variants`;",
        "  `must_be_present` only when selected lenses > 0 (lens=0 → omit, no FN).",
        f"- Live Observatory FN count: **{obs_fn}**",
        "",
        "## 2. Locked-label fix",
        "",
        "- Public labels are immutable structural contracts.",
        "- Alias map restores literary renames (e.g. 残されたもの → 守られたもの).",
        f"- Live locked-label mutations: **{label_mut}**",
        "",
        "## 3. Call3 heading preservation",
        "",
        "- Call3 literary naturalness LLM skipped on v1.1.10 runtime.",
        "- After each Call3 rewrite / language pass: `restore_locked_section_manuscript`",
        "  (Call2 markdown = fallback SoT for required meanings).",
        "",
        "## 4. Parser behavior",
        "",
        "- Valid: line-start `## <locked label>`.",
        "- Normalize: inline `##`, missing space, trailing `。`, alias labels.",
        "- Pipeline prefers parse → restore → `render_locked_sections`.",
        f"- Live heading parser misses (inline/period forms remaining): **{parser_miss}**",
        "",
        "## 5. Education compression fix",
        "",
        "- Required-section meaning preservation: if Call3 prose loses interpretive core,",
        "  restore that section body from Call2 fallback.",
        "- No education semantic rewrite.",
        "",
        "## 6. Clarification exit state machine",
        "",
        "```",
        "needs_additional_input → clarification_answered → reevaluate_grounding",
        "→ ready_for_user_confirmation → confirmed → ready_for_draft → draft_generation",
        "```",
        "",
        "- Soft thesis bounce after max rounds + structurally sufficient → `ready_for_draft`",
        "  (`clarification_exit=sufficient_for_deep_reading`).",
        "- Structurally insufficient → `insufficient_for_deep_reading` (HTTP 200).",
        "- No confirm dead-end without draft route.",
        f"- Live clarification dead-ends: **{dead}**",
        "",
        "## 7. Targeted 7-case rerun",
        "",
        "| Case | Pub | ObsFN | LabelMut | Parser | DeadEnd | Draft | Status | Class |",
        "|------|-----|-------|----------|--------|---------|-------|--------|-------|",
    ]
    for r in target_results:
        d = r.get("deterministic") or {}
        lines.append(
            "| {cid} | {pub} | {ofn} | {lm} | {pm} | {de} | {dr} | {st} | {cls} |".format(
                cid=r["case_id"],
                pub=r.get("publishable"),
                ofn=d.get("observatory_false_negative"),
                lm=d.get("locked_label_mutation"),
                pm=bool(
                    d.get("heading_parser_inline_miss")
                    or d.get("heading_parser_period_form")
                ),
                de=d.get("clarification_dead_end"),
                dr=d.get("draft_reached"),
                st=d.get("final_status"),
                cls=r.get("classification"),
            )
        )

    lines += [
        "",
        "## 8. Sensitive deterministic-only result",
        "",
        "```json",
        json.dumps(sensitive or {}, ensure_ascii=False, indent=2),
        "```",
        "",
        "- Editorial Lost/Protected underrealization left for Track B (not tuned here).",
        "",
        "## 9. Full 10-case rerun (v1.1.9 → v1.1.10)",
        "",
        "| Case | v119 Pub | v1110 Pub | ObsFN | LabelMut | DeadEnd | Class |",
        "|------|----------|-----------|-------|----------|---------|-------|",
    ]
    for r in full_results:
        d = r.get("deterministic") or {}
        prev_r = prev_by.get(r["case_id"]) or {}
        lines.append(
            "| {cid} | {p119} | {p110} | {ofn} | {lm} | {de} | {cls} |".format(
                cid=r["case_id"],
                p119=prev_r.get("publishable"),
                p110=r.get("publishable"),
                ofn=d.get("observatory_false_negative"),
                lm=d.get("locked_label_mutation"),
                de=d.get("clarification_dead_end"),
                cls=r.get("classification"),
            )
        )

    lines += [
        "",
        "## 10. Publishable count",
        "",
        f"**{len(publishable)} / {len(full_results)}**",
        "",
        "## 11. Remaining genuine editorial failures",
        "",
        "```json",
        json.dumps(editorial, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 12. Production untouched confirmation",
        "",
        f"- Production Call1: `{pins['production'].get('call1')}`",
        f"- Production schema: `{pins['production'].get('schema')}`",
        f"- Production pack: `{pins['production'].get('pack')}` (must be false/null)",
        f"- production_context_pack_off: `{pins['flags'].get('production_context_pack_off')}`",
        f"- Staging Call1 (keep v1.1.9-exp): `{pins['staging_contextual'].get('call1')}`",
        f"- Staging runtime: `{pins['staging_contextual'].get('schema')}`",
        "",
        "## 13. Recommendation",
        "",
    ]
    if not det_ok:
        lines.append(
            "STOP per stop-rule. Fix remaining deterministic failures before Track B."
        )
    else:
        lines.append(
            "Deterministic Track A targets met. Do **not** auto-start Track B; "
            "review remaining editorial failure matrix first."
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
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--phase",
        choices=["pins", "target7", "full", "all"],
        default="all",
    )
    args = ap.parse_args()

    pins = verify_pins()
    if not pins_ready(pins):
        print(json.dumps({"error": "pins_not_ready", "pins": pins}, ensure_ascii=False, indent=2))
        REPORT.write_text(
            "# Deterministic Realization v1.1.10 ABORTED — pins not ready\n\n```json\n"
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
    if args.phase in {"target7", "all"}:
        target_results, _ = run_cases(TARGET7)
        (OUT / "PUBLIC_QA_V1110_TARGET7.json").write_text(
            json.dumps(target_results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Early stop if deterministic failures in target7
        det_fail = any(
            (r.get("deterministic") or {}).get(k)
            for r in target_results
            for k in (
                "observatory_false_negative",
                "locked_label_mutation",
                "clarification_dead_end",
            )
        ) or any(
            (r.get("deterministic") or {}).get("heading_parser_inline_miss")
            or (r.get("deterministic") or {}).get("heading_parser_period_form")
            for r in target_results
        )
        if det_fail and args.phase == "target7":
            write_report(
                pins=pins,
                target_results=target_results,
                full_results=target_results,
                sensitive=None,
            )
            print(json.dumps({"verdict": "target7_deterministic_fail"}, indent=2))
            return 1

    if args.phase in {"full", "all"}:
        full_results, _ = run_cases(None)
    else:
        full_results = target_results

    sensitive = next(
        (r for r in full_results if r["case_id"] == "case10_sensitive"), None
    )
    if sensitive is None and args.phase == "all":
        # may already be in full
        pass
    payload = write_report(
        pins=pins,
        target_results=target_results or [r for r in full_results if r["case_id"] in TARGET7],
        full_results=full_results,
        sensitive={
            "case_id": "case10_sensitive",
            "publishable": (sensitive or {}).get("publishable"),
            "deterministic": (sensitive or {}).get("deterministic"),
            "blocking": ((sensitive or {}).get("blocking_reasons") or [])[:8],
            "note": "Editorial Lost/Protected left for Track B",
        }
        if sensitive
        else None,
    )
    print(
        json.dumps(
            {"verdict": payload["verdict"], "summary": payload["summary"]},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload.get("deterministic_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
