#!/usr/bin/env python3
"""Full live E2E: Call1 → confirm → Call2 → Call3 → publication gate (v1.0.4).

Optional: ONLY_CASES=case2,case3 poetry run python scripts/run_full_live_e2e_v101.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

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

from app.parallel_life_deep_reading.call1_schema import (  # noqa: E402
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
    call1_rebranch_directions,
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
from app.parallel_life_deep_reading.prompts import (  # noqa: E402
    CALL_2_VERSION,
    CALL_3_VERSION,
)
from app.parallel_life_deep_reading.runtime_validation import (  # noqa: E402
    detect_copied_long_segments,
    detect_generic_advice,
    detect_schema_leakage_prose,
    detect_sentence_fragments,
    detect_unsupported_affect,
    detect_unsupported_causal_frame,
    detect_unsupported_causality,
    detect_unsupported_personal_details,
    detect_unsupported_role_behavior,
    detect_unsupported_scenes,
    filter_publishable_rebranch,
    recalculate_publication_gate,
)
from app.parallel_life_deep_reading.service import DeepReadingService  # noqa: E402

OUT_DIR = ROOT / "e2e_reports" / "deep-reading-v1.0.4-full-live-run"

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


def _heading_count(body: str) -> int:
    return len(re.findall(r"(?m)^#{1,3}\s+", body or ""))


def _chapter_feel(body: str) -> bool:
    # Heuristic: many short H2 sections or numbered chapter labels
    if _heading_count(body) >= 5:
        return True
    if re.search(r"(第\s*[一二三四五六七八九十0-9]+章|Chapter\s*\d)", body or ""):
        return True
    return False


def analyze_body(body: str, call1, draft_rebranch) -> dict:
    grounded = call1.grounded_input
    source = call1.grounded_input.facts[0].source_text if call1.grounded_input.facts else ""
    source_blob = "\n".join(
        [source]
        + [f.source_text for f in grounded.facts if f.source_text]
        + list(grounded.current_context)
    )
    scenes = detect_unsupported_scenes(body, grounded)
    personal = detect_unsupported_personal_details(body, grounded)
    causality = detect_unsupported_causality(body, grounded)
    causal_frames = detect_unsupported_causal_frame(body, grounded)
    schema_leakage = detect_schema_leakage_prose(body)
    affect = detect_unsupported_affect(body, grounded)
    roles = detect_unsupported_role_behavior(body, grounded)
    advice = detect_generic_advice(body, grounded)
    fragments = detect_sentence_fragments(body)
    copied = detect_copied_long_segments(body, source_blob)
    _, pub_rb = filter_publishable_rebranch(
        draft_rebranch or [], grounded=grounded
    )
    return {
        "char_count": len(body or ""),
        "heading_count": _heading_count(body),
        "chapter_by_chapter_feel": _chapter_feel(body),
        "unsupported_scenes": [s.model_dump(mode="json") for s in scenes],
        "unsupported_personal_details": [d.model_dump(mode="json") for d in personal],
        "unsupported_causality": [c.model_dump(mode="json") for c in causality],
        "unsupported_causal_frame": [c.model_dump(mode="json") for c in causal_frames],
        "schema_leakage_prose": [s.model_dump(mode="json") for s in schema_leakage],
        "unsupported_affect": [a.model_dump(mode="json") for a in affect],
        "unsupported_role_behavior": [r.model_dump(mode="json") for r in roles],
        "generic_advice": [a.model_dump(mode="json") for a in advice],
        "sentence_fragments": fragments,
        "copied_long_segments": copied,
        "publishable_rebranch_count": len(pub_rb),
    }


def run_case(service: DeepReadingService, case: dict) -> dict:
    entry: dict = {
        "id": case["id"],
        "title": case["title"],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }
    case_dir = OUT_DIR / case["id"]
    case_dir.mkdir(parents=True, exist_ok=True)

    # --- Call 1 ---
    print(f"\n=== {case['id']}: Call 1 ===", flush=True)
    ground = service.ground(DeepReadingGroundRequest(source_text=case["source"], language="ja"))
    session = ground.session
    call1 = session.call1
    assert call1 is not None
    (case_dir / "call1.json").write_text(
        call1.model_dump_json(indent=2), encoding="utf-8"
    )

    secs = [
        s
        for s in call1.branch_structure.secondary_branches
        if s.classification == BranchClassification.actual_secondary_branch
    ]
    residue_items = call1_residue_items(call1)
    entry["call1"] = {
        "session_id": session.session_id,
        "status": call1.status.value,
        "prompt_version": getattr(call1, "prompt_version", CALL_1_PROMPT_VERSION),
        "schema_version": getattr(call1, "schema_version", CALL_1_SCHEMA_VERSION),
        "source_coverage": call1.source_coverage.model_dump(),
        "central_thesis": call1.central_thesis.statement,
        "actual_secondary_count": len(secs),
        "actual_secondary_descriptions": [s.description for s in secs],
        "retrospective_counterfactuals": [
            c.description for c in call1.branch_structure.retrospective_counterfactuals
        ],
        "questions": [q.content for q in call1.grounded_input.questions],
        "current_context": list(call1.grounded_input.current_context),
        "selected_lenses": [
            c.model_dump(mode="json") for c in call1_selected_lenses(call1)
        ],
        "rebranch_directions": [
            d.model_dump(mode="json") for d in call1_rebranch_directions(call1)
        ],
        "residue_generation_path": [
            n for n in call1.validation.notes if n.startswith("residue:")
        ],
        "validated_residue": [r.model_dump(mode="json") for r in residue_items],
        "confirmation_view": call1.user_confirmation_view.model_dump(),
    }

    if call1.status not in {
        GenerationStatus.ready_for_user_confirmation,
        GenerationStatus.ready_for_draft,
    }:
        # Still try approve if needs_additional_input but coverage somehow ok — else stop
        if call1.status == GenerationStatus.needs_additional_input:
            entry["errors"].append(f"Call1 status={call1.status.value}; attempting approve anyway")
        else:
            entry["verdict"] = "FAIL"
            entry["stage_failed"] = "call1"
            return entry

    # --- Confirm ---
    print(f"=== {case['id']}: Confirm ===", flush=True)
    confirmed = service.confirm(
        DeepReadingConfirmRequest(session_id=session.session_id, action="approve")
    )
    session = confirmed.session
    call1 = session.call1
    assert call1 and call1.grounded_input.confirmed_by_user
    entry["confirmation"] = {
        "status": session.status.value,
        "confirmed_by_user": call1.grounded_input.confirmed_by_user,
        "timestamp": session.confirmation_timestamp,
    }

    # --- Call 2 ---
    print(f"=== {case['id']}: Call 2 ===", flush=True)
    drafted = service.draft(session.session_id)
    session = drafted.session
    call2 = session.call2
    assert call2 is not None
    (case_dir / "call2.json").write_text(call2.model_dump_json(indent=2), encoding="utf-8")
    (case_dir / "call2_body.md").write_text(call2.body_markdown or "", encoding="utf-8")
    c2_analysis = analyze_body(call2.body_markdown, call1, call2.rebranch_candidates)
    # Independent gate on draft body
    c2_gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=call2,
        body=call2.body_markdown,
        title=call2.title_candidates[0] if call2.title_candidates else "",
        subtitle=call2.subtitle_candidates[0] if call2.subtitle_candidates else "",
        rebranch_candidates=call2.rebranch_candidates,
    )
    entry["call2"] = {
        "prompt_version": call2.prompt_version,
        "character_count": call2.character_count or len(call2.body_markdown or ""),
        "title_candidates": call2.title_candidates,
        "subtitle_candidates": call2.subtitle_candidates,
        "rebranch_candidates": [r.model_dump(mode="json") for r in call2.rebranch_candidates],
        "rebranch_omitted_reason": call2.rebranch_omitted_reason,
        "observatory_omitted": call2.observatory_omitted,
        "analysis": c2_analysis,
        "independent_gate": c2_gate.model_dump(mode="json"),
    }

    # --- Call 3 ---
    print(f"=== {case['id']}: Call 3 ===", flush=True)
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

    c3_analysis = analyze_body(call3.body_markdown, call1, call3.validation.rebranch_validations)
    c3_gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=call2,
        body=call3.body_markdown,
        title=call3.final_title,
        subtitle=call3.final_subtitle,
        rebranch_candidates=list(call3.validation.rebranch_validations)
        or list(call2.rebranch_candidates),
    )

    # Retention check
    blob = (call3.body_markdown or "") + "\n" + (call3.final_title or "")
    retain_hits = {tok: tok in blob for tok in case["must_retain"]}

    entry["call3"] = {
        "prompt_version": call3.prompt_version,
        "status": call3.status.value,
        "final_title": call3.final_title,
        "final_subtitle": call3.final_subtitle,
        "character_count": call3.character_count or len(call3.body_markdown or ""),
        "validation_from_runtime": call3.validation.model_dump(mode="json"),
        "independent_gate": c3_gate.model_dump(mode="json"),
        "analysis": c3_analysis,
        "named_entity_retention": retain_hits,
        "session_status": session.status.value,
        "publishable": bool(call3.validation.publishable),
        "final_manuscript_present": bool(session.final_manuscript),
    }

    # Machine pass hints (quality scores filled later in report)
    v = call3.validation
    machine_ok = (
        session.status == GenerationStatus.complete
        and v.publishable
        and len(v.unsupported_scenes) == 0
        and len(v.unsupported_personal_details) == 0
        and getattr(v, "unsupported_causality_count", len(v.unsupported_causality)) == 0
        and getattr(v, "unsupported_affect_count", len(v.unsupported_affect)) == 0
        and getattr(v, "unsupported_role_behavior_count", len(v.unsupported_role_behavior))
        == 0
        and getattr(v, "unsupported_causal_frame_count", len(v.unsupported_causal_frame))
        == 0
        and getattr(v, "schema_leakage_prose_count", len(v.schema_leakage_prose)) == 0
        and not getattr(v.title_validation, "title_causal_frame_violation", False)
        and len(v.contradictions) == 0
        and not v.observatory_takeover
        and len(v.sentence_fragments) == 0
        and len(v.generic_advice_findings) == 0
        and v.title_validation.passed
        and all(retain_hits.values())
    )
    entry["call1_present_anchors"] = [
        {"residue": r.statement(), "present_anchor_ids": r.present_anchor_ids}
        for r in residue_items
    ]
    entry["machine_pass_hints"] = {
        "complete_and_publishable": machine_ok,
        "blocking_reasons": v.blocking_reasons,
        "independent_blocking": c3_gate.blocking_reasons,
    }
    entry["finished_at"] = datetime.now(timezone.utc).isoformat()
    (case_dir / "case_summary.json").write_text(
        json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"=== {case['id']}: done status={session.status.value} "
        f"publishable={call3.validation.publishable} "
        f"blockers={call3.validation.blocking_reasons}",
        flush=True,
    )
    return entry


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    service = DeepReadingService()
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "prompt_versions": {
            "call_1": CALL_1_PROMPT_VERSION,
            "call_1_schema": CALL_1_SCHEMA_VERSION,
            "call_2": CALL_2_VERSION,
            "call_3": CALL_3_VERSION,
        },
        "prompts_modified_during_run": False,
        "call1_frozen": True,
        "cases": [],
    }

    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or "your-api" in key:
        print("ERROR: OPENAI_API_KEY missing or placeholder", flush=True)
        return 2

    only = {
        x.strip()
        for x in os.environ.get("ONLY_CASES", "").split(",")
        if x.strip()
    }
    selected = [c for c in CASES if not only or c["id"] in only]
    for case in selected:
        try:
            entry = run_case(service, case)
        except Exception as exc:
            entry = {
                "id": case["id"],
                "title": case["title"],
                "verdict": "FAIL",
                "stage_failed": "exception",
                "errors": [f"{type(exc).__name__}: {exc}", traceback.format_exc()],
            }
            print(f"FAIL {case['id']}: {exc}", flush=True)
            (OUT_DIR / case["id"]).mkdir(parents=True, exist_ok=True)
            (OUT_DIR / case["id"] / "error.txt").write_text(
                "\n".join(entry["errors"]), encoding="utf-8"
            )
        report["cases"].append(entry)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (OUT_DIR / "FULL_LIVE_RAW.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nWrote", OUT_DIR / "FULL_LIVE_RAW.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
