#!/usr/bin/env python3
"""Call 1–only live E2E for schema v1.0.1 (four cases). Does not invoke Call 2/3."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env if present
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from app.parallel_life_deep_reading.call1_schema import (  # noqa: E402
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
    Call1SchemaError,
    call1_rebranch_directions,
)
from app.parallel_life_deep_reading.fixtures import (  # noqa: E402
    CASE1_SOURCE,
    CASE2_SOURCE,
    CASE3_SOURCE,
)
from app.parallel_life_deep_reading.grounding import run_call1_grounding  # noqa: E402
from app.parallel_life_deep_reading.models import (  # noqa: E402
    BranchClassification,
    GenerationStatus,
)
from app.parallel_life_deep_reading.runtime_validation import (  # noqa: E402
    looks_like_user_question,
)

OUT_DIR = ROOT / "e2e_reports" / "deep-reading-call1-v1.0.1-live-run"

CASES = [
    {
        "id": "case1",
        "title": "Fertility — retrospective counterfactual only",
        "source": CASE1_SOURCE,
        "expect_actual_secondary": False,
        "must_retain": [],
    },
    {
        "id": "case2",
        "title": "Fertility + explicit later discussion/decision",
        "source": CASE1_SOURCE
        + "\n息子を授かった後、二人目を目指す治療を続けるか妻と話し合い、やめた。",
        "expect_actual_secondary": True,
        "must_retain": ["話し合", "やめた"],
    },
    {
        "id": "case3",
        "title": "University — named entities and polarity",
        "source": CASE2_SOURCE,
        "expect_actual_secondary": False,
        "must_retain": [
            "第一志望",
            "早稲田大学第一文学部",
            "合格",
            "進学",
            "別の大学",
        ],
    },
    {
        "id": "case4",
        "title": "Creative vs corporate",
        "source": CASE3_SOURCE,
        "expect_actual_secondary": False,
        "must_retain": ["会社員", "創作", "現在"],
    },
]


def _blob(call1) -> str:
    parts = [
        call1.branch_structure.primary_branch.period,
        call1.branch_structure.primary_branch.triggering_event,
        call1.branch_structure.primary_branch.realized_path,
        *call1.branch_structure.primary_branch.unrealized_paths,
        *call1.grounded_input.current_context,
        *[f.content for f in call1.grounded_input.facts],
        *[q.content for q in call1.grounded_input.questions],
        call1.user_confirmation_view.central_thesis_preview,
    ]
    return "\n".join(parts)


def evaluate(case: dict, call1) -> dict:
    cov = call1.source_coverage.model_dump()
    questions = [q.content for q in call1.grounded_input.questions]
    feelings = [f.content for f in call1.grounded_input.feelings]
    secs = call1.branch_structure.secondary_branches
    cfs = call1.branch_structure.retrospective_counterfactuals
    dirs = call1_rebranch_directions(call1)
    blob = _blob(call1)

    q_ok = any(looks_like_user_question(q) for q in questions) or bool(questions)
    feeling_leak = any(looks_like_user_question(f) for f in feelings)
    actual_ok = (
        any(s.classification == BranchClassification.actual_secondary_branch for s in secs)
        if case["expect_actual_secondary"]
        else not any(s.classification == BranchClassification.actual_secondary_branch for s in secs)
    )
    if case["expect_actual_secondary"]:
        actual_ok = actual_ok and any(s.explicit_evidence_ids for s in secs)

    cf_ok = True
    if not case["expect_actual_secondary"]:
        cf_ok = len(cfs) >= 1 or len(questions) >= 1

    retain_hits = {tok: (tok in blob) for tok in case["must_retain"]}
    retain_ok = all(retain_hits.values()) if case["must_retain"] else True

    status_ok = call1.status == GenerationStatus.ready_for_user_confirmation
    coverage_ok = call1.source_coverage.all_required_present()
    rebranch_ok = all(d.support_ids and d.genericity_score <= 1 for d in dirs)
    confirm_ok = bool(
        call1.user_confirmation_view.branch_period
        or call1.user_confirmation_view.triggering_event
        or call1.user_confirmation_view.chosen_path
    )

    checks = {
        "raw_structured_response_valid": True,
        "normalization_applied": list(
            (call1.parse_diagnostics.normalization_applied if call1.parse_diagnostics else [])
        ),
        "source_coverage": cov,
        "source_coverage_complete": coverage_ok,
        "fact_boundary_question_present": q_ok,
        "fact_boundary_no_feeling_leak": not feeling_leak,
        "branch_classification_ok": actual_ok and cf_ok,
        "actual_secondary_count": len(
            [s for s in secs if s.classification == BranchClassification.actual_secondary_branch]
        ),
        "retrospective_counterfactual_count": len(cfs),
        "rebranch_filtered_ok": rebranch_ok,
        "rebranch_direction_count": len(dirs),
        "named_entity_retention": retain_hits,
        "named_entity_ok": retain_ok,
        "status": call1.status.value,
        "confirmation_view_present": confirm_ok,
        "status_ready_for_confirmation": status_ok,
    }
    passed = (
        status_ok
        and coverage_ok
        and q_ok
        and not feeling_leak
        and actual_ok
        and cf_ok
        and rebranch_ok
        and confirm_ok
        and retain_ok
    )
    checks["PASS"] = passed
    return checks


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": CALL_1_PROMPT_VERSION,
        "schema_version": CALL_1_SCHEMA_VERSION,
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "cases": [],
    }

    all_pass = True
    for case in CASES:
        entry = {"id": case["id"], "title": case["title"]}
        print(f"\n=== {case['id']}: {case['title']} ===", flush=True)
        try:
            call1 = run_call1_grounding(case["source"])
            # Save sanitized summary (not full personal narrative dump in production logs;
            # this is a local E2E artifact directory).
            raw_path = OUT_DIR / f"{case['id']}_call1_result.json"
            raw_path.write_text(
                call1.model_dump_json(indent=2, exclude_none=True),
                encoding="utf-8",
            )
            checks = evaluate(case, call1)
            entry["checks"] = checks
            entry["parser_result"] = "ok"
            entry["confirmation_view"] = call1.user_confirmation_view.model_dump()
            entry["PASS"] = checks["PASS"]
            print(json.dumps(checks, ensure_ascii=False, indent=2), flush=True)
        except Call1SchemaError as exc:
            all_pass = False
            entry["parser_result"] = "Call1SchemaError"
            entry["diagnostics"] = exc.diagnostics.model_dump()
            entry["PASS"] = False
            print("FAIL schema", exc.diagnostics.validation_errors[:8], flush=True)
            (OUT_DIR / f"{case['id']}_schema_error.json").write_text(
                json.dumps(entry, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            all_pass = False
            entry["parser_result"] = f"{type(exc).__name__}: {exc}"
            entry["PASS"] = False
            print("FAIL", type(exc).__name__, exc, flush=True)
            cause = getattr(exc, "__cause__", None)
            if cause:
                print("cause", cause, flush=True)

        all_pass = all_pass and bool(entry.get("PASS"))
        report["cases"].append(entry)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["all_four_pass"] = all_pass
    report["call2_reachable"] = all_pass  # reachable after user confirmation once Call1 passes
    report["release_status"] = (
        "Call1 milestone met — not Production Candidate frozen"
        if all_pass
        else "Call1 milestone NOT met — do not proceed to Call 2/3"
    )

    md_lines = [
        "# Call 1 Live E2E — v1.0.1",
        "",
        f"- Prompt: `{CALL_1_PROMPT_VERSION}`",
        f"- Schema: `{CALL_1_SCHEMA_VERSION}`",
        f"- Model: `{report['model']}`",
        f"- All four PASS: **{all_pass}**",
        f"- Call 2 reachable after confirmation: **{all_pass}**",
        f"- Release: {report['release_status']}",
        "",
    ]
    for c in report["cases"]:
        md_lines.append(f"## {c['id']} — {'PASS' if c.get('PASS') else 'FAIL'}")
        md_lines.append("")
        md_lines.append(f"- {c['title']}")
        md_lines.append(f"- parser: `{c.get('parser_result')}`")
        checks = c.get("checks") or {}
        for k in (
            "status",
            "source_coverage_complete",
            "fact_boundary_question_present",
            "branch_classification_ok",
            "rebranch_filtered_ok",
            "named_entity_ok",
            "confirmation_view_present",
            "status_ready_for_confirmation",
        ):
            if k in checks:
                md_lines.append(f"- {k}: `{checks[k]}`")
        md_lines.append("")

    (OUT_DIR / "CALL1_LIVE_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "CALL1_LIVE_REPORT.md").write_text("\n".join(md_lines), encoding="utf-8")
    print("\nWrote", OUT_DIR / "CALL1_LIVE_REPORT.md", flush=True)
    print("ALL_PASS" if all_pass else "SOME_FAILED", flush=True)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
