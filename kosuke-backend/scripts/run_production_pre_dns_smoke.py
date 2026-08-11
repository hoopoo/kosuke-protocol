#!/usr/bin/env python3
"""Pre-DNS production smoke A–F against Cloudflare temporary URLs."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get(
    "PROD_API_URL",
    "https://parallel-life-api.shiroandco-office.workers.dev",
).rstrip("/")
OUT = Path(
    os.environ.get(
        "PROD_SMOKE_DIR",
        "e2e_reports/deep-reading-cloudflare-production/pre_dns_smoke",
    )
)
OUT.mkdir(parents=True, exist_ok=True)
RESULTS: dict[str, dict] = {}

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "KosukeProdSmoke/1.0"
)

STANDARD_TEXT = (
    "大学4年のとき、地元で就職するか東京に出るかで迷った。"
    "結局地元のメーカーに入り、今は安定しているが、"
    "あのとき東京に出ていれば別の可能性があったのではないかと時々思う。"
)

CASE09 = (
    "時期: 22歳\n"
    "出来事: 第一志望の会社に落ちた\n"
    "選んだ道: 第一志望の会社に入社した\n"
    "選ばなかった道: 別の会社に入ること\n"
    "今の問い: 別の会社だったらどうだったか\n"
    "今の状況: 今は転職して別の会社にいる"
)

CASE10 = (
    "時期: 特にない\n"
    "出来事: なんとなく今まで働いてきた\n"
    "選んだ道: 今の人生\n"
    "選ばなかった道: もっと自由な人生\n"
    "今の問い: 別の人生もあったのかな\n"
    "今の状況: 今も仕事をしている"
)


def req(method: str, path: str, body: dict | None = None, timeout: int = 180) -> tuple[int, object]:
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
            try:
                return res.status, json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                return res.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"detail": raw}
        except json.JSONDecodeError:
            return e.code, {"detail": raw}


def record(case: str, ok: bool, detail: object) -> None:
    RESULTS[case] = {"ok": ok, "detail": detail}
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {case}: {detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)[:400]}")


def main() -> int:
    code, health = req("GET", "/healthz", timeout=120)
    record("healthz", code == 200 and isinstance(health, dict) and health.get("status") == "ok", health)

    # A: Standard happy path
    code, std = req(
        "POST",
        "/experience/parallel-life",
        {
            "source_text": STANDARD_TEXT,
            "language": "ja",
            "depth": "standard",
            "clarifications": {},
        },
        timeout=180,
    )
    record(
        "A_standard_happy",
        code == 200 and isinstance(std, dict) and bool(std.get("title") or std.get("sections")),
        {"status": code, "keys": list(std.keys())[:12] if isinstance(std, dict) else type(std).__name__},
    )

    # B + F: Deep Reading happy + persistence across separate requests
    code, ground = req(
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": STANDARD_TEXT,
            "language": "ja",
            "clarifications": {},
            "editorial_context": {},
        },
        timeout=180,
    )
    if code != 200 or not isinstance(ground, dict) or "session" not in ground:
        record("B_deep_reading_happy", False, {"status": code, "body": ground})
        record("F_session_persistence", False, "skipped: ground failed")
    else:
        sid = ground["session"]["session_id"]
        time.sleep(3)
        code_s, sess = req("GET", f"/experience/parallel-life/deep-reading/session/{sid}", timeout=60)
        persisted = code_s == 200 and isinstance(sess, dict) and sess.get("session", {}).get("session_id") == sid

        code_c, confirmed = req(
            "POST",
            "/experience/parallel-life/deep-reading/confirm",
            {"session_id": sid, "action": "approve"},
            timeout=120,
        )
        if code_c != 200:
            record(
                "B_deep_reading_happy",
                False,
                {"stage": "confirm", "status": code_c, "body": confirmed},
            )
            record("F_session_persistence", persisted, {"session_get": code_s, "confirm": code_c})
        else:
            idem = f"prod-draft-{sid}"
            code_d, draft = req(
                "POST",
                "/experience/parallel-life/deep-reading/draft",
                {"session_id": sid, "idempotency_key": idem},
                timeout=300,
            )
            code_e, edited = req(
                "POST",
                "/experience/parallel-life/deep-reading/edit-validate",
                {"session_id": sid, "idempotency_key": f"prod-edit-{sid}"},
                timeout=300,
            )
            final_status = (
                edited.get("session", {}).get("status")
                if isinstance(edited, dict)
                else None
            )
            ok_b = code_d == 200 and code_e in (200, 400)
            record(
                "B_deep_reading_happy",
                ok_b,
                {
                    "session_id": sid,
                    "draft": code_d,
                    "edit": code_e,
                    "status": final_status,
                },
            )
            record(
                "F_session_persistence",
                persisted and code_c == 200 and code_d == 200,
                {
                    "session_get": code_s,
                    "confirm": code_c,
                    "draft": code_d,
                    "edit": code_e,
                },
            )

    # C: Case09 contradiction — safe stop before confirmation / no Call2
    code, c09 = req(
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": CASE09,
            "language": "ja",
            "clarifications": {},
            "editorial_context": {},
        },
        timeout=180,
    )
    c09_session = c09.get("session") if isinstance(c09, dict) else None
    c09_status = c09_session.get("status") if isinstance(c09_session, dict) else None
    c09_sid = c09_session.get("session_id") if isinstance(c09_session, dict) else None
    confirm_blocked = False
    if c09_sid:
        code_c09, conf09 = req(
            "POST",
            "/experience/parallel-life/deep-reading/confirm",
            {"session_id": c09_sid, "action": "approve"},
            timeout=120,
        )
        # Safe stop: confirm rejected OR session never ready_for_user_confirmation
        confirm_blocked = code_c09 != 200 or (
            isinstance(conf09, dict)
            and conf09.get("session", {}).get("status")
            not in {"confirmed", "drafting", "draft_ready", "completed", "published"}
        )
        if c09_status and c09_status not in {
            "ready_for_user_confirmation",
            "awaiting_confirmation",
        }:
            confirm_blocked = True
    record(
        "C_case09_contradiction",
        code == 200 and confirm_blocked,
        {"ground": code, "status": c09_status, "confirm_blocked": confirm_blocked},
    )

    # D: Case10 vague branch — structural ambiguity
    code, c10 = req(
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": CASE10,
            "language": "ja",
            "clarifications": {},
            "editorial_context": {},
        },
        timeout=180,
    )
    c10_session = c10.get("session") if isinstance(c10, dict) else None
    c10_status = c10_session.get("status") if isinstance(c10_session, dict) else None
    ambiguous = c10_status in {
        "structural_ambiguity",
        "needs_clarification",
        "clarification_required",
        "insufficient_branch",
        "safe_stop",
    } or (
        isinstance(c10, dict)
        and (
            c10.get("needs_clarification") is True
            or "ambigu" in json.dumps(c10, ensure_ascii=False).lower()
        )
    )
    record(
        "D_case10_vague_branch",
        code == 200 and ambiguous,
        {"ground": code, "status": c10_status, "ambiguous": ambiguous},
    )

    # E: Kill switch probe (enabled=true on production by default; toggle verified separately)
    code, enabled = req("GET", "/experience/parallel-life/deep-reading/enabled", timeout=60)
    record(
        "E_kill_switch_probe_enabled",
        code == 200 and isinstance(enabled, dict) and enabled.get("enabled") is True,
        enabled,
    )

    OUT.joinpath("RESULTS.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2))
    print(f"\nWrote {OUT / 'RESULTS.json'}")
    failed = [k for k, v in RESULTS.items() if not v["ok"]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
