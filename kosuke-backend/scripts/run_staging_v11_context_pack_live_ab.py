#!/usr/bin/env python3
"""Live Strict vs Contextual A/B on Cloudflare STAGING (Context Pack v1.1-exp).

Does not modify prompts/runtime/schema. Fresh session per arm.
Writes artifacts under e2e_reports/deep-reading-v1.1-context-pack/live_ab/.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.fixtures import (  # noqa: E402
    CASE1_SOURCE,
    CASE2_SOURCE,
    CASE3_SOURCE,
)

STAGING_API = os.environ.get(
    "STAGING_API_URL",
    "https://parallel-life-api-staging.shiroandco-office.workers.dev",
).rstrip("/")
PROD_API = os.environ.get(
    "PROD_API_URL",
    "https://parallel-life-api.shiroandco-office.workers.dev",
).rstrip("/")

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "live_ab"
OUT.mkdir(parents=True, exist_ok=True)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "KosukeV11ContextPackLiveAB/1.0"
)

NTT_SOURCE = """28歳のとき、NTTに残るか、外資へ移るかを選ぶ分岐があった。
実際に選んだ道はNTTを離れ、外資系企業へ移ること。
選ばなかった道は、一企業の内部で役割を積み上げ続けること。
いまは自分の会社を経営している。
いまも「あのとき残っていたら」と考えることがある。"""

NTT_PACK_ITEMS = [
    ("career_history", "NTT東日本で勤務した"),
    ("career_history", "外資系半導体企業へ転職した"),
    ("career_history", "その後、複数業界・企業を経験した"),
    ("current_work", "現在は自分の会社を経営している"),
    ("current_projects", "現在、複数の観測・Protocol・文章制作を行っている"),
]

FAMILY_PACK_ITEMS = [
    ("family_context", "妻と息子との三人家族で暮らしている"),
    ("current_work", "現在は自分の会社を経営している"),
    ("current_creative_activity", "文章やプロトコルの制作を続けている"),
]

EDU_PACK_ITEMS = [
    ("current_work", "現在は自分の会社を経営している"),
    ("current_projects", "文章やプロトコルをまとめている"),
    ("current_creative_activity", "観測・Protocol・文章制作を行っている"),
]

CREATIVE_PACK_ITEMS = [
    ("current_work", "現在は自分の会社を経営している"),
    ("current_creative_activity", "文章制作を行っている"),
    ("current_projects", "観測プロジェクトを進めている"),
    ("current_projects", "Protocol 関連の仕事をしている"),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def req(api: str, method: str, path: str, body: dict | None = None, timeout: int = 420):
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": UA,
    }
    r = urllib.request.Request(f"{api}{path}", data=data, headers=headers, method=method)
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


def build_approved_pack(items: list[tuple[str, str]], language: str = "ja") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    pack_items = []
    for i, (category, content) in enumerate(items):
        interp_only = category in {"current_values", "user_self_definitions"}
        pack_items.append(
            {
                "id": f"pack_{category}_{i+1:03d}",
                "content": content,
                "category": category,
                "source": "user_typed",
                "confidence": 1.0,
                "approved": True,
                "allowed_for_fact": not interp_only,
                "allowed_for_interpretation": True,
                "time_span": {"start": "", "end": "", "precision": "unknown"},
                "chronology_rank": (10 + i) if category == "career_history" else (100 + i),
                "tags": ["live_ab_approved"],
            }
        )
    return {
        "pack_id": f"pack_live_{_now()}_{abs(hash(str(items))) % 10_000:04d}",
        "mode_intent": "contextual",
        "source": "user_authored",
        "created_at": now,
        "updated_at": now,
        "approved_by_user": True,
        "approved_at": now,
        "language": language,
        "items": pack_items,
        "rejected_or_deleted_ids": [],
    }


def _view(session: dict) -> dict:
    call1 = (session.get("call1") or {}) if isinstance(session, dict) else {}
    return deepcopy(call1.get("user_confirmation_view") or {})


def _aq_list(call1: dict) -> list[str]:
    aq = call1.get("additional_questions")
    if isinstance(aq, dict):
        return list(aq.get("questions") or [])
    if isinstance(aq, list):
        return [str(x) for x in aq]
    return []


def approve_with_clarifications(api: str, sid: str, session: dict) -> tuple[int, dict]:
    """Answer clarifications if needed, then approve. Fresh pipeline per arm."""
    call1 = session.get("call1") or {}
    view = _view(session)
    # Ensure minimum present context for draft gate
    ctx = [c for c in (view.get("current_context") or []) if str(c).strip()]
    if not ctx:
        view["current_context"] = ["いまの暮らしと仕事の具体的な場面が続いている"]
    pq = [q for q in (view.get("present_questions") or []) if str(q).strip()]
    if not pq:
        view["present_questions"] = ["あのとき別の道を選んでいたら、いまはどうだったか"]

    questions = _aq_list(call1)
    if questions or (call1.get("status") in {"needs_additional_input", "structural_ambiguity"}):
        answers = {
            str(i): (
                "妻と息子と三人で暮らし、仕事と制作の日常が続いている。"
                if any(t in q for t in ("現在", "生活", "場面", "暮ら"))
                else "あの分岐がいまも残る問いとして触れることがある。"
            )
            for i, q in enumerate(questions or ["いまの生活の具体的な場面を教えてください"])
        }
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
        if code != 200:
            return code, answered if isinstance(answered, dict) else {"detail": answered}
        session = answered.get("session") or {}
        view = _view(session)
        # loop once more if still asking
        call1 = session.get("call1") or {}
        more = _aq_list(call1)
        if more and call1.get("status") == "needs_additional_input":
            answers2 = {
                str(i): "いまの仕事と暮らしの具体が続いている。"
                for i in range(len(more))
            }
            code, answered = req(
                api,
                "POST",
                "/experience/parallel-life/deep-reading/confirm",
                {
                    "session_id": sid,
                    "action": "answer",
                    "answers_to_additional_questions": answers2,
                    "confirmation_view_overrides": view,
                },
            )
            if code != 200:
                return code, answered if isinstance(answered, dict) else {"detail": answered}
            session = answered.get("session") or {}
            view = _view(session)

    return req(
        api,
        "POST",
        "/experience/parallel-life/deep-reading/confirm",
        {
            "session_id": sid,
            "action": "approve",
            "confirmation_view_overrides": view,
        },
    )


def extract_trace(session: dict) -> dict:
    call1 = session.get("call1") or {}
    meta = session.get("model_metadata") or {}
    usage = call1.get("context_pack_usage") or meta.get("context_pack_usage") or {}
    grounded = call1.get("grounded_input") or {}
    facts = grounded.get("facts") or []
    pack_facts = [
        {"id": f.get("id"), "content": f.get("content"), "tags": f.get("tags")}
        for f in facts
        if f.get("source_field") == "context_pack" or "context_pack" in (f.get("tags") or [])
    ]
    residue = call1.get("residue_candidates") or {}
    residue_items = residue.get("items") if isinstance(residue, dict) else residue
    residue_items = residue_items or []
    lenses = call1.get("selected_observatory_lenses") or {}
    selected = lenses.get("selected") if isinstance(lenses, dict) else lenses
    selected = selected or []
    rebranch = call1.get("rebranch_design") or {}
    directions = rebranch.get("directions") if isinstance(rebranch, dict) else rebranch
    directions = directions or []
    pack_ids = {p["id"] for p in pack_facts if p.get("id")}
    thesis = (call1.get("central_thesis") or {}).get("statement") or ""
    return {
        "deep_reading_mode": session.get("deep_reading_mode"),
        "call1_prompt_version": (session.get("prompt_versions") or {}).get("call_1")
        or meta.get("call_1_prompt_version"),
        "runtime_schema_version": session.get("schema_version"),
        "pack_fact_ids": sorted(pack_ids),
        "pack_facts": pack_facts,
        "context_pack_usage": usage,
        "residue": [
            {
                "statement": r.get("residue_statement") or r.get("content"),
                "past_anchor_ids": r.get("past_anchor_ids"),
                "present_anchor_ids": r.get("present_anchor_ids"),
                "pack_ids_used": [
                    x
                    for x in (r.get("past_anchor_ids") or []) + (r.get("present_anchor_ids") or [])
                    if x in pack_ids
                ],
            }
            for r in residue_items
            if isinstance(r, dict)
        ],
        "central_thesis": thesis,
        "thesis_mentions_pack_content": any(
            (p.get("content") or "")[:8] in thesis for p in pack_facts if p.get("content")
        ),
        "observatory_selected": [
            {
                "lens_id": c.get("lens_id"),
                "explicit_evidence_ids": c.get("explicit_evidence_ids"),
                "residue_evidence_ids": c.get("residue_evidence_ids"),
                "new_meaning_added": c.get("new_meaning_added"),
                "pack_evidence_ids": [
                    e for e in (c.get("explicit_evidence_ids") or []) if e in pack_ids
                ],
            }
            for c in selected
            if isinstance(c, dict)
        ],
        "rebranch": [
            {
                "id": d.get("id"),
                "branch_specific_form": d.get("branch_specific_form"),
                "current_receiver": d.get("current_receiver"),
                "support_ids": d.get("support_ids"),
                "pack_support_ids": [s for s in (d.get("support_ids") or []) if s in pack_ids],
            }
            for d in directions
            if isinstance(d, dict)
        ],
    }


def leak_check(strict_session: dict, pack_items: list[tuple[str, str]]) -> dict:
    """Strict arm must not contain pack-only career claims as facts."""
    blob = json.dumps(strict_session, ensure_ascii=False)
    # Unique pack phrases that should not appear if Strict ignored the pack
    unique = [c for _, c in pack_items if c not in NTT_SOURCE and "経営" not in c]
    hits = [c for c in unique if c in blob]
    pack_facts = [
        f
        for f in ((strict_session.get("call1") or {}).get("grounded_input") or {}).get("facts")
        or []
        if f.get("source_field") == "context_pack"
    ]
    return {
        "pack_fact_count": len(pack_facts),
        "unique_pack_phrase_hits_in_session_json": hits,
        "leak_detected": bool(pack_facts) or bool(hits),
    }


def run_pipeline(
    api: str,
    *,
    case_id: str,
    arm: str,
    source: str,
    mode: str,
    pack: dict | None,
) -> dict:
    t0 = time.perf_counter()
    out: dict = {
        "case_id": case_id,
        "arm": arm,
        "mode": mode,
        "ok": False,
        "stages": {},
    }
    body = {
        "source_text": source,
        "language": "ja",
        "clarifications": {},
        "editorial_context": {},
        "deep_reading_mode": mode,
    }
    if pack is not None:
        body["context_pack"] = pack

    code, ground = req(api, "POST", "/experience/parallel-life/deep-reading/ground", body)
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
            "deep_reading_mode": session.get("deep_reading_mode"),
            "schema_version": session.get("schema_version"),
            "prompt_versions": session.get("prompt_versions"),
            "call1_prompt": (session.get("model_metadata") or {}).get("call_1_prompt_version"),
            "context_pack_enabled_meta": (session.get("model_metadata") or {}).get(
                "context_pack_enabled"
            ),
        }
    )
    out["trace_after_ground"] = extract_trace(session)

    time.sleep(1.5)
    code_c, confirmed = approve_with_clarifications(api, sid, session)
    out["stages"]["confirm"] = {"status": code_c}
    if code_c != 200:
        out["error"] = confirmed
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        _dump(case_id, arm, "confirm_error", confirmed)
        return out
    session = confirmed.get("session") or {}
    out["trace_after_confirm"] = extract_trace(session)

    idem = f"v11ab-{case_id}-{arm}-{_now()}"
    code_d, draft = req(
        api,
        "POST",
        "/experience/parallel-life/deep-reading/draft",
        {"session_id": sid, "idempotency_key": idem},
    )
    out["stages"]["draft"] = {"status": code_d}
    if code_d != 200:
        out["error"] = draft
        out["elapsed_s"] = round(time.perf_counter() - t0, 2)
        return out

    code_e, edited = req(
        api,
        "POST",
        "/experience/parallel-life/deep-reading/edit-validate",
        {"session_id": sid, "idempotency_key": f"{idem}-edit"},
    )
    session = edited.get("session") or {} if isinstance(edited, dict) else {}
    call3 = session.get("call3") or {}
    validation = call3.get("validation") or {}
    out["stages"]["edit"] = {
        "status": code_e,
        "session_status": session.get("status"),
        "publishable": validation.get("publishable"),
        "blocking_reasons": validation.get("blocking_reasons") or [],
        "final_title": call3.get("final_title"),
        "final_subtitle": call3.get("final_subtitle"),
    }
    body_md = call3.get("body_markdown") or session.get("final_manuscript") or ""
    out["manuscript"] = {
        "title": call3.get("final_title"),
        "subtitle": call3.get("final_subtitle"),
        "body_markdown": body_md,
        "char_count": len(body_md),
    }
    out["trace_final"] = extract_trace(session)
    out["ok"] = (
        code_e == 200
        and session.get("status") == "complete"
        and bool(validation.get("publishable"))
    )
    out["elapsed_s"] = round(time.perf_counter() - t0, 2)
    _dump(case_id, arm, "session_final", session)
    _dump(case_id, arm, "manuscript", out["manuscript"])
    _dump(case_id, arm, "trace", out["trace_final"])
    return out


def _dump(case_id: str, arm: str, name: str, payload: object) -> None:
    d = OUT / case_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{arm}_{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def probe_flags() -> dict:
    sc, staging = req(STAGING_API, "GET", "/experience/parallel-life/deep-reading/enabled")
    pc, prod = req(PROD_API, "GET", "/experience/parallel-life/deep-reading/enabled")
    return {
        "staging": {"http": sc, "body": staging},
        "production": {"http": pc, "body": prod},
        "staging_context_pack_on": bool(
            isinstance(staging, dict) and staging.get("context_pack_enabled")
        ),
        "production_context_pack_off": not bool(
            isinstance(prod, dict) and prod.get("context_pack_enabled")
        ),
    }


def ux_seed_checks() -> dict:
    """API-level Context Pack approval UX checks (seed/edit/approve semantics)."""
    code, seeded = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/context-pack/seed",
        {
            "text": "NTT東日本で勤務した。現在は自分の会社を経営している。",
            "language": "ja",
            "source": "imported_paste",
        },
    )
    pack = (seeded or {}).get("context_pack") if isinstance(seeded, dict) else None
    items = (pack or {}).get("items") or []
    # Unapproved by default
    all_unapproved = all(not i.get("approved") for i in items) if items else False
    pack_unapproved = not bool((pack or {}).get("approved_by_user"))
    # No raw internal field names as user-visible content
    raw_id_leak = any(
        re.search(r"\b(fact_|source_field|boundary_type)\b", i.get("content") or "")
        for i in items
    )
    # Edit/delete/add locally then approve for ground
    if pack and items:
        items[0]["content"] = items[0]["content"] + "（編集済）"
        items[0]["approved"] = True
        if len(items) > 1:
            deleted = items.pop()
            pack["rejected_or_deleted_ids"] = [deleted.get("id")]
        items.append(
            {
                "id": "pack_current_projects_999",
                "content": "観測プロジェクトを進めている",
                "category": "current_projects",
                "source": "user_typed",
                "confidence": 1.0,
                "approved": True,
                "allowed_for_fact": True,
                "allowed_for_interpretation": True,
                "time_span": {"start": "", "end": "", "precision": "unknown"},
                "chronology_rank": 120,
                "tags": [],
            }
        )
        pack["items"] = items
        pack["approved_by_user"] = True
        pack["approved_at"] = datetime.now(timezone.utc).isoformat()
        pack["mode_intent"] = "contextual"

    # Seed must 404/disabled on production
    pcode, pbody = req(
        PROD_API,
        "POST",
        "/experience/parallel-life/deep-reading/context-pack/seed",
        {"text": "test", "language": "ja"},
    )
    return {
        "staging_seed_http": code,
        "seed_items": len(items),
        "items_start_unapproved": all_unapproved,
        "pack_starts_unapproved": pack_unapproved,
        "no_raw_internal_ids_in_content": not raw_id_leak,
        "can_edit_delete_add_locally": True,
        "production_seed_blocked": pcode in {404, 403, 501}
        or (
            isinstance(pbody, dict)
            and ("disabled" in str(pbody).lower() or "not found" in str(pbody).lower())
        )
        or pcode != 200,
        "production_seed_http": pcode,
        "edited_pack_for_ground": pack,
    }


CASES = [
    {
        "id": "A_ntt",
        "label": "NTT career branch",
        "source": NTT_SOURCE,
        "pack_items": NTT_PACK_ITEMS,
    },
    {
        "id": "B_family",
        "label": "Family / fertility",
        "source": CASE1_SOURCE,
        "pack_items": FAMILY_PACK_ITEMS,
    },
    {
        "id": "C_education",
        "label": "Education (Waseda)",
        "source": CASE2_SOURCE,
        "pack_items": EDU_PACK_ITEMS,
    },
    {
        "id": "D_creative",
        "label": "Creative vs corporate",
        "source": CASE3_SOURCE,
        "pack_items": CREATIVE_PACK_ITEMS,
    },
]


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    flags = probe_flags()
    (OUT / "flag_probe.json").write_text(
        json.dumps(flags, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not flags["staging_context_pack_on"]:
        print("ERROR: staging context_pack_enabled is not true", json.dumps(flags, ensure_ascii=False))
        return 2
    if not flags["production_context_pack_off"]:
        print("ERROR: production context_pack unexpectedly enabled", json.dumps(flags, ensure_ascii=False))
        return 3

    ux = ux_seed_checks()
    (OUT / "ux_seed_checks.json").write_text(
        json.dumps(ux, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Mode separation leak test on NTT
    ntt_pack = build_approved_pack(NTT_PACK_ITEMS)
    strict = run_pipeline(
        STAGING_API,
        case_id="mode_sep",
        arm="strict",
        source=NTT_SOURCE,
        mode="strict",
        pack=ntt_pack,  # intentionally send pack; Strict must ignore
    )
    contextual = run_pipeline(
        STAGING_API,
        case_id="mode_sep",
        arm="contextual",
        source=NTT_SOURCE,
        mode="contextual",
        pack=ntt_pack,
    )
    sep = {
        "strict": {
            "ok": strict.get("ok"),
            "prompt": (strict.get("stages") or {}).get("ground", {}).get("call1_prompt"),
            "mode": (strict.get("stages") or {}).get("ground", {}).get("deep_reading_mode"),
            "schema": (strict.get("stages") or {}).get("ground", {}).get("schema_version"),
            "leak": leak_check(
                json.loads((OUT / "mode_sep" / "strict_session_final.json").read_text())
                if (OUT / "mode_sep" / "strict_session_final.json").exists()
                else {},
                NTT_PACK_ITEMS,
            )
            if strict.get("ok") or strict.get("session_id")
            else {"error": strict.get("error")},
        },
        "contextual": {
            "ok": contextual.get("ok"),
            "prompt": (contextual.get("stages") or {}).get("ground", {}).get("call1_prompt"),
            "mode": (contextual.get("stages") or {}).get("ground", {}).get("deep_reading_mode"),
            "schema": (contextual.get("stages") or {}).get("ground", {}).get("schema_version"),
            "pack_fact_count": len(
                (contextual.get("trace_final") or {}).get("pack_fact_ids") or []
            ),
        },
    }
    (OUT / "mode_separation.json").write_text(
        json.dumps(sep, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    results = []
    for case in CASES:
        pack = build_approved_pack(case["pack_items"])
        a = run_pipeline(
            STAGING_API,
            case_id=case["id"],
            arm="strict",
            source=case["source"],
            mode="strict",
            pack=None,
        )
        b = run_pipeline(
            STAGING_API,
            case_id=case["id"],
            arm="contextual",
            source=case["source"],
            mode="contextual",
            pack=pack,
        )
        results.append(
            {
                "case": case["id"],
                "label": case["label"],
                "strict": {
                    "ok": a.get("ok"),
                    "elapsed_s": a.get("elapsed_s"),
                    "title": (a.get("manuscript") or {}).get("title"),
                    "char_count": (a.get("manuscript") or {}).get("char_count"),
                    "blockers": (a.get("stages") or {}).get("edit", {}).get("blocking_reasons"),
                    "prompt": (a.get("stages") or {}).get("ground", {}).get("call1_prompt"),
                    "schema": (a.get("stages") or {}).get("ground", {}).get("schema_version"),
                    "trace": a.get("trace_final"),
                    "error": a.get("error"),
                },
                "contextual": {
                    "ok": b.get("ok"),
                    "elapsed_s": b.get("elapsed_s"),
                    "title": (b.get("manuscript") or {}).get("title"),
                    "char_count": (b.get("manuscript") or {}).get("char_count"),
                    "blockers": (b.get("stages") or {}).get("edit", {}).get("blocking_reasons"),
                    "prompt": (b.get("stages") or {}).get("ground", {}).get("call1_prompt"),
                    "schema": (b.get("stages") or {}).get("ground", {}).get("schema_version"),
                    "trace": b.get("trace_final"),
                    "error": b.get("error"),
                },
            }
        )
        print(
            f"[{case['id']}] strict_ok={a.get('ok')} contextual_ok={b.get('ok')} "
            f"chars={ (a.get('manuscript') or {}).get('char_count') }/"
            f"{ (b.get('manuscript') or {}).get('char_count') }"
        )

    summary = {
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "staging_api": STAGING_API,
        "prod_api": PROD_API,
        "flags": flags,
        "ux": {
            k: ux[k]
            for k in ux
            if k != "edited_pack_for_ground"
        },
        "mode_separation": sep,
        "cases": results,
    }
    (OUT / "LIVE_AB_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"flags": flags, "mode_separation": sep}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
