#!/usr/bin/env python3
"""Final production confirmation: Call1 → confirm → Call2 Terra → Call3 Terra.

Uses production prompts, runtime, and model split. Does not alter fixtures.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
import traceback
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
from app.parallel_life_deep_reading.fixtures import (  # noqa: E402
    CASE1_SOURCE,
    CASE2_SOURCE,
    CASE3_SOURCE,
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
from app.parallel_life_deep_reading.service import DeepReadingService  # noqa: E402

OUT_DIR = ROOT / "e2e_reports" / "deep-reading-production-v1.0-final"

CASES = [
    {
        "id": "case1",
        "title": "Family formation / fertility — retrospective counterfactual only",
        "source": CASE1_SOURCE,
        "expect_actual_secondary": False,
        "must_retain": [],
    },
    {
        "id": "case2",
        "title": "Family formation / fertility — explicit later discussion/decision",
        "source": CASE1_SOURCE
        + "\n息子を授かった後、二人目を目指す治療を続けるか妻と話し合い、やめた。",
        "expect_actual_secondary": True,
        "must_retain": ["話し合", "やめた"],
    },
    {
        "id": "case3",
        "title": "First-choice university admission",
        "source": CASE2_SOURCE,
        "expect_actual_secondary": False,
        "must_retain": ["第一志望", "早稲田大学第一文学部", "合格", "進学"],
    },
    {
        "id": "case4",
        "title": "Creative work vs corporate career",
        "source": CASE3_SOURCE,
        "expect_actual_secondary": False,
        "must_retain": ["会社員", "創作"],
    },
]

PRICE_PER_M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5.6-terra": {"input": 2.50, "output": 15.00},
    "gpt-5.6-sol": {"input": 5.00, "output": 25.00},
}

USAGE_EVENTS: list[dict[str, Any]] = []
_ORIG_CHAT_JSON = llm_mod.chat_json


def chat_json_tracked(*args: Any, **kwargs: Any) -> dict[str, Any]:
    model = kwargs.get("model") or CALL_1_MODEL
    t0 = time.perf_counter()
    # Capture usage by wrapping the OpenAI call path with a local duplicate that
    # still uses production chat_json parameter rules via monkeypatch of create.
    from openai import OpenAI

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
            "Deep Reading の生成に失敗しました。確認済み構造は保持されています。再試行してください。"
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
            else ("call2" if model == CALL_2_MODEL else "call3_or_other"),
        }
    )
    return llm_mod.parse_json_content(content)


def soft_watch(body: str, title: str) -> list[str]:
    tokens = (
        "転機",
        "情熱",
        "結びつき",
        "関連",
        "原点",
        "意味を持つ",
        "影響",
        "形づく",
        "幸せ",
        "絆",
        "大きな役割",
    )
    blob = (body or "") + "\n" + (title or "")
    return [t for t in tokens if t in blob]


def run_case(service: DeepReadingService, case: dict[str, Any]) -> dict[str, Any]:
    global USAGE_EVENTS
    before = len(USAGE_EVENTS)
    case_dir = OUT_DIR / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "id": case["id"],
        "title": case["title"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }
    t0 = time.perf_counter()

    print(f"\n=== {case['id']}: Call 1 ===", flush=True)
    ground = service.ground(
        DeepReadingGroundRequest(source_text=case["source"], language="ja")
    )
    session = ground.session
    call1 = session.call1
    assert call1 is not None
    (case_dir / "call1.json").write_text(call1.model_dump_json(indent=2), encoding="utf-8")

    secs = [
        s
        for s in call1.branch_structure.secondary_branches
        if s.classification == BranchClassification.actual_secondary_branch
    ]
    residue_items = call1_residue_items(call1)
    entry["call1"] = {
        "status": call1.status.value,
        "prompt_version": getattr(call1, "prompt_version", CALL_1_PROMPT_VERSION),
        "schema_version": getattr(call1, "schema_version", CALL_1_SCHEMA_VERSION),
        "model": (session.model_metadata or {}).get("call_1_model"),
        "actual_secondary_count": len(secs),
        "validated_residue": [r.model_dump(mode="json") for r in residue_items],
        "selected_lenses": len(call1_selected_lenses(call1)),
        "central_thesis": call1.central_thesis.statement,
    }

    print(f"=== {case['id']}: Confirm ===", flush=True)
    confirmed = service.confirm(
        DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
    )
    session = confirmed.session
    call1 = session.call1
    assert call1 and call1.grounded_input.confirmed_by_user

    print(f"=== {case['id']}: Call 2 (Terra) ===", flush=True)
    drafted = service.draft(session.session_id)
    session = drafted.session
    call2 = session.call2
    assert call2 is not None
    (case_dir / "call2.json").write_text(call2.model_dump_json(indent=2), encoding="utf-8")
    (case_dir / "call2_body.md").write_text(call2.body_markdown or "", encoding="utf-8")

    print(f"=== {case['id']}: Call 3 (Terra) ===", flush=True)
    edited = service.edit_validate(session.session_id)
    session = edited.session
    call3 = session.call3
    assert call3 is not None
    (case_dir / "call3.json").write_text(call3.model_dump_json(indent=2), encoding="utf-8")
    (case_dir / "call3_body.md").write_text(call3.body_markdown or "", encoding="utf-8")
    if session.final_manuscript:
        (case_dir / "final_manuscript.md").write_text(
            session.final_manuscript, encoding="utf-8"
        )

    wall_ms = int((time.perf_counter() - t0) * 1000)
    events = USAGE_EVENTS[before:]
    call2_events = [e for e in events if e["model"] == CALL_2_MODEL]
    call3_events = [
        e for e in events if e["model"] == CALL_3_MODEL and e not in call2_events
    ]
    # Call3 may share model id with call2; split by order: first terra block after call1 = call2
    call1_events = [e for e in events if e["model"] == CALL_1_MODEL]
    terra_events = [e for e in events if e["model"] == CALL_2_MODEL]
    # Heuristic: first contiguous terra group after call1 is call2; rest call3
    call2_tok_in = call2_tok_out = call3_tok_in = call3_tok_out = 0
    if terra_events:
        # All terra usage after call1: attribute first event(s) until call2 draft done —
        # simpler: sum all terra; split 40/60 is bad. Use timestamps order:
        # run_call2 is one chat_json; call3 may be multiple. First terra = call2, rest = call3.
        call2_tok_in = terra_events[0]["prompt_tokens"]
        call2_tok_out = terra_events[0]["completion_tokens"]
        for e in terra_events[1:]:
            call3_tok_in += e["prompt_tokens"]
            call3_tok_out += e["completion_tokens"]

    body = call3.body_markdown or ""
    title = call3.final_title or ""
    g = call1.grounded_input
    v = call3.validation
    retain = {tok: tok in (body + "\n" + title) for tok in case["must_retain"]}
    residue_in_body = bool(residue_items) and (
        "残" in body or "接続" in body or any(
            t in body
            for r in residue_items
            for t in __import__("re").findall(r"[\u4e00-\u9fff]{2,}", r.statement())[:4]
        )
    )

    entry["call2"] = {
        "model": CALL_2_MODEL,
        "prompt_version": call2.prompt_version,
        "character_count": len(call2.body_markdown or ""),
        "tokens_in": call2_tok_in,
        "tokens_out": call2_tok_out,
    }
    entry["call3"] = {
        "model": CALL_3_MODEL,
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
        "soft_watch_hits": soft_watch(body, title),
        "residue_represented": residue_in_body,
        "named_entity_retention": retain,
        "tokens_in": call3_tok_in,
        "tokens_out": call3_tok_out,
    }
    entry["session_model_metadata"] = session.model_metadata
    entry["latency_ms_total"] = wall_ms
    entry["usage_events"] = events
    entry["estimated_cost_usd"] = round(sum(e["estimated_cost_usd"] for e in events), 6)
    entry["finished_at"] = datetime.now(timezone.utc).isoformat()
    (case_dir / "case_summary.json").write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"=== {case['id']}: done pub={v.publishable} blockers={v.blocking_reasons} "
        f"title={title!r} cost=${entry['estimated_cost_usd']} lat={wall_ms}ms",
        flush=True,
    )
    return entry


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Patch all import sites (from-import binds the original function object).
    import app.parallel_life_deep_reading.draft as draft_mod
    import app.parallel_life_deep_reading.edit_validate as edit_mod
    import app.parallel_life_deep_reading.grounding as ground_mod

    llm_mod.chat_json = chat_json_tracked  # type: ignore[assignment]
    draft_mod.chat_json = chat_json_tracked  # type: ignore[assignment]
    edit_mod.chat_json = chat_json_tracked  # type: ignore[assignment]
    # grounding uses chat_json_schema → llm.chat_json at call time via module attr.
    if hasattr(ground_mod, "chat_json"):
        ground_mod.chat_json = chat_json_tracked  # type: ignore[assignment]

    if CALL_2_MODEL != "gpt-5.6-terra" or CALL_3_MODEL != "gpt-5.6-terra":
        print("ERROR: production model split is not Terra/Terra", flush=True)
        return 2

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or "your-api" in key:
        print("ERROR: OPENAI_API_KEY missing", flush=True)
        return 2

    service = DeepReadingService()
    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "production_models_version": PRODUCTION_MODELS_VERSION,
        "production_models": dict(PRODUCTION_MODELS),
        "prompt_versions": dict(PROMPT_VERSIONS),
        "runtime_validation_version": SCHEMA_VERSION,
        "call_1_model": CALL_1_MODEL,
        "call_2_model": CALL_2_MODEL,
        "call_3_model": CALL_3_MODEL,
        "fixtures_modified": False,
        "prompts_modified": False,
        "runtime_modified": False,
        "cases": [],
    }

    latencies: list[int] = []
    for case in CASES:
        try:
            entry = run_case(service, case)
            latencies.append(int(entry["latency_ms_total"]))
        except Exception as exc:
            entry = {
                "id": case["id"],
                "title": case["title"],
                "errors": [f"{type(exc).__name__}: {exc}", traceback.format_exc()],
                "publishable": False,
            }
            print(f"FAIL {case['id']}: {exc}", flush=True)
            (OUT_DIR / case["id"]).mkdir(parents=True, exist_ok=True)
            (OUT_DIR / case["id"] / "error.txt").write_text(
                "\n".join(entry["errors"]), encoding="utf-8"
            )
        report["cases"].append(entry)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["cost_latency"] = {
        "total_estimated_cost_usd": round(
            sum(c.get("estimated_cost_usd", 0) or 0 for c in report["cases"]), 6
        ),
        "total_call2_tokens_in": sum(
            (c.get("call2") or {}).get("tokens_in", 0) for c in report["cases"]
        ),
        "total_call2_tokens_out": sum(
            (c.get("call2") or {}).get("tokens_out", 0) for c in report["cases"]
        ),
        "total_call3_tokens_in": sum(
            (c.get("call3") or {}).get("tokens_in", 0) for c in report["cases"]
        ),
        "total_call3_tokens_out": sum(
            (c.get("call3") or {}).get("tokens_out", 0) for c in report["cases"]
        ),
        "average_total_latency_ms": int(statistics.mean(latencies)) if latencies else None,
        "p50_latency_ms": int(statistics.median(latencies)) if latencies else None,
        "p95_latency_ms": int(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)])
        if latencies
        else None,
        "latencies_ms": latencies,
    }
    (OUT_DIR / "FINAL_PRODUCTION_RAW.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nWrote", OUT_DIR / "FINAL_PRODUCTION_RAW.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
