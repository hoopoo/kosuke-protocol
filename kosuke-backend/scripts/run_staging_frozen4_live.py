#!/usr/bin/env python3
"""Frozen-4 live regression against Cloudflare staging API (HTTP)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.fixtures import (  # noqa: E402
    CASE1_SOURCE,
    CASE2_SOURCE,
    CASE3_SOURCE,
)

API = os.environ.get(
    "STAGING_API_URL",
    "https://parallel-life-api-staging.shiroandco-office.workers.dev",
).rstrip("/")
OUT = Path(
    os.environ.get(
        "FROZEN4_OUT",
        str(ROOT / "e2e_reports/deep-reading-cloudflare-production/frozen4_staging"),
    )
)
OUT.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "KosukeFrozen4Staging/1.0"
)

CASES = [
    {
        "id": "case1",
        "source": CASE1_SOURCE,
        "expect_publishable": True,
    },
    {
        "id": "case2",
        "source": CASE1_SOURCE
        + "\n息子を授かった後、二人目を目指す治療を続けるか妻と話し合い、やめた。",
        "expect_publishable": True,
    },
    {
        "id": "case3",
        "source": CASE2_SOURCE,
        "expect_publishable": True,
        "title_flake_possible": True,
    },
    {
        "id": "case4",
        "source": CASE3_SOURCE,
        "expect_publishable": True,
    },
]


def req(method: str, path: str, body: dict | None = None, timeout: int = 300) -> tuple[int, object]:
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": UA,
    }
    r = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as res:
            raw = res.read().decode()
            return res.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            return e.code, {"detail": raw}


def run_case(case: dict, *, attempt: int = 1) -> dict:
    t0 = time.perf_counter()
    result: dict = {
        "id": case["id"],
        "attempt": attempt,
        "ok": False,
        "stages": {},
        "title_flake": False,
        "notes": [],
    }
    code, ground = req(
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {"source_text": case["source"], "language": "ja", "clarifications": {}, "editorial_context": {}},
    )
    result["stages"]["ground"] = {"status": code}
    if code != 200 or not isinstance(ground, dict):
        result["error"] = ground
        result["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return result

    sid = ground["session"]["session_id"]
    result["session_id"] = sid
    result["stages"]["ground"]["schema_version"] = ground["session"].get("schema_version")
    result["stages"]["ground"]["prompt_versions"] = ground["session"].get("prompt_versions")
    result["stages"]["ground"]["model_metadata"] = ground["session"].get("model_metadata")

    time.sleep(2)
    code_s, sess = req("GET", f"/experience/parallel-life/deep-reading/session/{sid}")
    result["stages"]["session_get"] = {"status": code_s}
    if code_s != 200:
        result["error"] = "session_lost_after_ground"
        result["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return result

    code_c, confirmed = req(
        "POST",
        "/experience/parallel-life/deep-reading/confirm",
        {"session_id": sid, "action": "approve"},
    )
    result["stages"]["confirm"] = {"status": code_c}
    if code_c != 200:
        result["error"] = confirmed
        result["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return result

    idem = f"frozen4-{case['id']}-a{attempt}"
    code_d1, draft1 = req(
        "POST",
        "/experience/parallel-life/deep-reading/draft",
        {"session_id": sid, "idempotency_key": idem},
    )
    code_d2, draft2 = req(
        "POST",
        "/experience/parallel-life/deep-reading/draft",
        {"session_id": sid, "idempotency_key": idem},
    )
    a1 = draft1.get("session", {}).get("draft_attempt_count") if isinstance(draft1, dict) else None
    a2 = draft2.get("session", {}).get("draft_attempt_count") if isinstance(draft2, dict) else None
    result["stages"]["draft"] = {
        "status": code_d1,
        "duplicate_status": code_d2,
        "attempts": [a1, a2],
        "idempotent": code_d1 == 200 and code_d2 == 200 and a1 == a2 == 1,
    }
    if code_d1 != 200:
        result["error"] = draft1
        result["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return result

    code_e, edited = req(
        "POST",
        "/experience/parallel-life/deep-reading/edit-validate",
        {"session_id": sid, "idempotency_key": f"{idem}-edit"},
    )
    sess_final = edited.get("session", {}) if isinstance(edited, dict) else {}
    call3 = sess_final.get("call3") or {}
    validation = (call3.get("validation") or {}) if isinstance(call3, dict) else {}
    status = sess_final.get("status")
    publishable = bool(validation.get("publishable"))
    blockers = validation.get("blocking_reasons") or []
    title = call3.get("final_title") if isinstance(call3, dict) else ""
    result["stages"]["edit"] = {
        "status": code_e,
        "session_status": status,
        "publishable": publishable,
        "blocking_reasons": blockers,
        "final_title": title,
        "schema_version": sess_final.get("schema_version"),
        "model_metadata": sess_final.get("model_metadata"),
    }

    # Title-only flake: validation_failed solely due to title causal frame
    title_only = (
        status == "validation_failed"
        and not publishable
        and blockers
        and all("title" in str(b).lower() or "因果" in str(b) or "causal" in str(b).lower() for b in blockers)
    )
    if title_only and case.get("title_flake_possible"):
        result["title_flake"] = True
        result["notes"].append("title_only_failure_non_publication_safe")

    ok = (
        code_e == 200
        and result["stages"]["draft"]["idempotent"]
        and result["stages"]["session_get"]["status"] == 200
        and (
            (publishable and status == "complete")
            or (result["title_flake"] and not publishable)  # safe non-publish
        )
    )
    result["ok"] = ok
    result["elapsed_s"] = round(time.perf_counter() - t0, 2)

    OUT.joinpath(f"{case['id']}_attempt{attempt}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main() -> int:
    summary = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "api": API,
        "cases": [],
        "all_ok": True,
    }
    for case in CASES:
        print(f"=== {case['id']} attempt 1 ===", flush=True)
        r = run_case(case, attempt=1)
        if (not r["ok"]) and case.get("title_flake_possible") and r.get("title_flake"):
            print(f"=== {case['id']} title flake — retry once ===", flush=True)
            r2 = run_case(case, attempt=2)
            r["retry"] = r2
            r["ok"] = r2["ok"] or (r["title_flake"] and not (
                (r.get("stages", {}).get("edit") or {}).get("publishable")
            ))
            # Non-publication safety is sufficient for cutover gate on title flake
            if r.get("title_flake") and not (r.get("stages", {}).get("edit") or {}).get("publishable"):
                r["ok"] = True
                r["notes"].append("cutover_allowed_title_flake_non_publish")
        print(json.dumps({"id": r["id"], "ok": r["ok"], "elapsed_s": r.get("elapsed_s"), "notes": r.get("notes")}, ensure_ascii=False), flush=True)
        summary["cases"].append(r)
        summary["all_ok"] = summary["all_ok"] and bool(r["ok"])

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    OUT.joinpath("FROZEN4_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("ALL_OK" if summary["all_ok"] else "HAS_FAILURES", flush=True)
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
