#!/usr/bin/env python3
"""Model-isolation A/B for Deep Reading Call 2/3.

Does not change prompts, runtime validation, schemas, fixtures, or gates.
Uses frozen confirmed Call 1 payloads from a prior live run.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from copy import deepcopy
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

from app.parallel_life_deep_reading.call1_schema import call1_residue_items  # noqa: E402
from app.parallel_life_deep_reading.draft import run_call2_draft  # noqa: E402
from app.parallel_life_deep_reading.edit_validate import run_call3_edit_validate  # noqa: E402
from app.parallel_life_deep_reading.llm import (  # noqa: E402
    DeepReadingGenerationError,
    parse_json_content,
    require_api_key,
)
from app.parallel_life_deep_reading.models import Call1Result  # noqa: E402
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

CALL1_SOURCE_DIR = ROOT / "e2e_reports" / "deep-reading-v1.0.4-full-live-run"
OUT_DIR = ROOT / "e2e_reports" / "deep-reading-model-ab"

CASES = ["case1", "case2", "case3", "case4"]

CONFIGS = [
    {
        "id": "A_baseline",
        "label": "Baseline gpt-4o-mini / gpt-4o-mini",
        "call2_model": "gpt-4o-mini",
        "call3_model": "gpt-4o-mini",
    },
    {
        "id": "B_terra_terra",
        "label": "Balanced GPT-5.6 Terra / Terra",
        "call2_model": "gpt-5.6-terra",
        "call3_model": "gpt-5.6-terra",
    },
    {
        "id": "C_terra_sol",
        "label": "Editorial Terra / Sol",
        "call2_model": "gpt-5.6-terra",
        "call3_model": "gpt-5.6-sol",
    },
    {
        "id": "D_sol_sol",
        "label": "Maximum Sol / Sol",
        "call2_model": "gpt-5.6-sol",
        "call3_model": "gpt-5.6-sol",
    },
]

# Approximate USD / 1M tokens (short context). Used only for report deltas.
PRICE_PER_M = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5.6-terra": {"input": 2.50, "output": 15.00},
    "gpt-5.6-sol": {"input": 5.00, "output": 25.00},
}

USAGE_LOG: list[dict[str, Any]] = []
ACTIVE_MODEL = "gpt-4o-mini"


def _is_reasoning_family(model: str) -> bool:
    return model.startswith("gpt-5") or "terra" in model or "sol" in model


def chat_json_ab(
    system: str,
    user: str,
    *,
    max_tokens: int = 6000,
    temperature: float = 0.4,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Drop-in chat_json replacement that binds ACTIVE_MODEL and records usage."""
    api_key = require_api_key()
    model = ACTIVE_MODEL
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": response_format or {"type": "json_object"},
    }
    if _is_reasoning_family(model):
        kwargs["max_completion_tokens"] = max_tokens
        # Leave temperature unset for GPT-5.6 family.
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature

    t0 = time.perf_counter()
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        raise DeepReadingGenerationError(
            f"A/B chat_json failed model={model}: {exc}"
        ) from exc
    latency_ms = int((time.perf_counter() - t0) * 1000)
    content = response.choices[0].message.content or ""
    usage = response.usage
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    reasoning_tokens = 0
    details = getattr(usage, "completion_tokens_details", None)
    if details is not None:
        reasoning_tokens = int(getattr(details, "reasoning_tokens", 0) or 0)
    price = PRICE_PER_M.get(model, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens / 1_000_000) * price["input"] + (
        completion_tokens / 1_000_000
    ) * price["output"]
    USAGE_LOG.append(
        {
            "model": model,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "estimated_cost_usd": round(cost, 6),
            "response_model": getattr(response, "model", model),
        }
    )
    return parse_json_content(content)


def load_frozen_call1(case_id: str) -> Call1Result:
    path = CALL1_SOURCE_DIR / case_id / "call1.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing frozen Call1: {path}")
    call1 = Call1Result.model_validate_json(path.read_text(encoding="utf-8"))
    gi = call1.grounded_input.model_copy(update={"confirmed_by_user": True})
    call1 = call1.model_copy(update={"grounded_input": gi})
    if not call1_residue_items(call1):
        raise RuntimeError(f"{case_id}: frozen Call1 has no validated Residue")
    return call1


def analyze_body(body: str, title: str, call1: Call1Result) -> dict[str, Any]:
    g = call1.grounded_input
    return {
        "unsupported_personal_details": [
            x.model_dump(mode="json") for x in detect_unsupported_personal_details(body, g)
        ],
        "unsupported_causal_frame": [
            x.model_dump(mode="json") for x in detect_unsupported_causal_frame(body, g)
        ],
        "unsupported_causality": [
            x.model_dump(mode="json") for x in detect_unsupported_causality(body, g)
        ],
        "unsupported_affect": [
            x.model_dump(mode="json") for x in detect_unsupported_affect(body, g)
        ],
        "unsupported_role_behavior": [
            x.model_dump(mode="json") for x in detect_unsupported_role_behavior(body, g)
        ],
        "generic_advice": [
            x.model_dump(mode="json") for x in detect_generic_advice(body, g)
        ],
        "unsupported_scenes": [
            x.model_dump(mode="json") for x in detect_unsupported_scenes(body, g)
        ],
        "schema_leakage_prose": [
            x.model_dump(mode="json") for x in detect_schema_leakage_prose(body)
        ],
        "title_causal_frame_violation": title_has_unsupported_causal_frame(title, g),
        "soft_watch_hits": _soft_watch(body, title),
    }


def _soft_watch(body: str, title: str) -> list[str]:
    tokens = (
        "転機",
        "情熱",
        "結びつき",
        "結びつ",
        "関連",
        "原点",
        "意味を持つ",
        "影響",
        "形づく",
        "大きな役割",
        "幸せ",
        "絆",
    )
    blob = (body or "") + "\n" + (title or "")
    return [t for t in tokens if t in blob]


def run_one(config: dict[str, Any], case_id: str) -> dict[str, Any]:
    global ACTIVE_MODEL, USAGE_LOG
    call1 = load_frozen_call1(case_id)
    out_dir = OUT_DIR / config["id"] / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "call1_frozen.json").write_text(
        call1.model_dump_json(indent=2), encoding="utf-8"
    )

    entry: dict[str, Any] = {
        "config_id": config["id"],
        "case_id": case_id,
        "call2_model": config["call2_model"],
        "call3_model": config["call3_model"],
        "errors": [],
    }

    # Patch production helpers without modifying their source permanently.
    import app.parallel_life_deep_reading.draft as draft_mod
    import app.parallel_life_deep_reading.edit_validate as edit_mod

    draft_mod.chat_json = chat_json_ab
    edit_mod.chat_json = chat_json_ab

    USAGE_LOG = []
    t_all = time.perf_counter()

    ACTIVE_MODEL = config["call2_model"]
    t2 = time.perf_counter()
    draft = run_call2_draft(call1)
    call2_wall_ms = int((time.perf_counter() - t2) * 1000)
    usage_after_call2 = list(USAGE_LOG)

    ACTIVE_MODEL = config["call3_model"]
    t3 = time.perf_counter()
    call3 = run_call3_edit_validate(call1, draft)
    call3_wall_ms = int((time.perf_counter() - t3) * 1000)
    usage_all = list(USAGE_LOG)

    total_ms = int((time.perf_counter() - t_all) * 1000)

    (out_dir / "call2.json").write_text(draft.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "call2_body.md").write_text(draft.body_markdown or "", encoding="utf-8")
    (out_dir / "call3.json").write_text(call3.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "call3_body.md").write_text(call3.body_markdown or "", encoding="utf-8")

    analysis = analyze_body(call3.body_markdown or "", call3.final_title or "", call1)
    v = call3.validation

    prompt_tokens = sum(u["prompt_tokens"] for u in usage_all)
    completion_tokens = sum(u["completion_tokens"] for u in usage_all)
    reasoning_tokens = sum(u["reasoning_tokens"] for u in usage_all)
    est_cost = sum(u["estimated_cost_usd"] for u in usage_all)

    entry.update(
        {
            "final_title": call3.final_title,
            "final_subtitle": call3.final_subtitle,
            "status": call3.status.value,
            "publishable": bool(v.publishable),
            "blocking_reasons": list(v.blocking_reasons),
            "runtime_counts": {
                "unsupported_personal_detail_count": v.unsupported_personal_detail_count,
                "unsupported_scene_count": v.unsupported_scene_count,
                "unsupported_causality_count": v.unsupported_causality_count,
                "unsupported_causal_frame_count": v.unsupported_causal_frame_count,
                "unsupported_affect_count": v.unsupported_affect_count,
                "unsupported_role_behavior_count": v.unsupported_role_behavior_count,
                "schema_leakage_prose_count": v.schema_leakage_prose_count,
                "generic_advice_count": len(v.generic_advice_findings),
            },
            "independent_analysis": analysis,
            "character_count": len(call3.body_markdown or ""),
            "latency_ms": {
                "call2_wall": call2_wall_ms,
                "call3_wall": call3_wall_ms,
                "total_wall": total_ms,
                "sum_api_calls": sum(u["latency_ms"] for u in usage_all),
            },
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "reasoning": reasoning_tokens,
                "total": prompt_tokens + completion_tokens,
            },
            "estimated_cost_usd": round(est_cost, 6),
            "usage_events": usage_all,
            "call2_usage_events": usage_after_call2,
            "body_preview": (call3.body_markdown or "")[:500],
        }
    )
    (out_dir / "case_summary.json").write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"=== {config['id']} / {case_id}: "
        f"pub={entry['publishable']} cost=${entry['estimated_cost_usd']} "
        f"latency={total_ms}ms blockers={entry['blocking_reasons']}",
        flush=True,
    )
    return entry


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    only_cfg = {
        x.strip()
        for x in os.environ.get("ONLY_CONFIGS", "").split(",")
        if x.strip()
    }
    only_cases = {
        x.strip()
        for x in os.environ.get("ONLY_CASES", "").split(",")
        if x.strip()
    }
    configs = [c for c in CONFIGS if not only_cfg or c["id"] in only_cfg]
    cases = [c for c in CASES if not only_cases or c in only_cases]

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "call1_source": str(CALL1_SOURCE_DIR),
        "prompts_modified": False,
        "runtime_modified": False,
        "configs": [],
        "results": [],
    }

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or "your-api" in key:
        print("ERROR: OPENAI_API_KEY missing or placeholder", flush=True)
        return 2

    for config in configs:
        print(f"\n######## CONFIG {config['id']} ########", flush=True)
        report["configs"].append(deepcopy(config))
        for case_id in cases:
            try:
                entry = run_one(config, case_id)
            except Exception as exc:
                entry = {
                    "config_id": config["id"],
                    "case_id": case_id,
                    "errors": [f"{type(exc).__name__}: {exc}", traceback.format_exc()],
                    "publishable": False,
                }
                print(f"FAIL {config['id']}/{case_id}: {exc}", flush=True)
                case_dir = OUT_DIR / config["id"] / case_id
                case_dir.mkdir(parents=True, exist_ok=True)
                (case_dir / "error.txt").write_text(
                    "\n".join(entry["errors"]), encoding="utf-8"
                )
            report["results"].append(entry)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (OUT_DIR / "MODEL_AB_RAW.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nWrote", OUT_DIR / "MODEL_AB_RAW.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
