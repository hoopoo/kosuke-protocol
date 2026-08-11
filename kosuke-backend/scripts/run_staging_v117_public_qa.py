#!/usr/bin/env python3
"""Staging Public QA for Parallel Life Deep Reading v1.1.7-exp.

Does NOT modify prompts, runtime, schemas, models, Observatory-Core,
title validation, or publication gates. No auto-tune after failures.
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

from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V117,
    RUNTIME_VERSION_V117_EXP,
    UI_SECTION_LABELS_JA,
    abstract_vocabulary_density,
    claim_text_is_malformed,
    re_branch_realization_check,
    section_resume_flags,
)
from scripts.run_staging_v11_context_pack_live_ab import (  # noqa: E402
    NTT_PACK_ITEMS,
    NTT_SOURCE,
    PROD_API,
    STAGING_API,
    build_approved_pack,
    extract_trace,
    probe_flags,
    req,
    run_pipeline,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-public-qa"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = OUT / "PUBLIC_QA_REPORT.md"
RAW = OUT / "PUBLIC_QA_RAW.json"

COACHING_RE = re.compile(r"(?:すべき|今こそ|挑戦しよう|成長しよう|キャリアアップ|生産性を上げ)")
SCHEMA_LEAK_RE = re.compile(
    r"(?:この選択は、実際に選んだのは|スキーマ|boundary_type|fact_\d+|source_field)"
)


def _fields_to_source(fields: dict[str, str]) -> str:
    order = [
        ("branch_period", "{v}のとき、"),
        ("triggering_event", "{v}という分岐があった。"),
        ("chosen_path", "実際に選んだ道は、{v}。"),
        ("unchosen_path", "選ばなかった道は、{v}。"),
        ("current_context", "現在は、{v}。"),
        ("present_question", "いまも「{v}」と考えることがある。"),
        ("additional_context", "{v}"),
    ]
    parts: list[str] = []
    for key, tmpl in order:
        v = (fields.get(key) or "").strip()
        if not v:
            continue
        if key == "branch_period":
            parts.append(tmpl.format(v=v))
        elif key == "triggering_event" and parts and parts[-1].endswith("、"):
            parts[-1] = parts[-1] + v + "という分岐があった。"
        else:
            parts.append(tmpl.format(v=v))
    return "\n".join(p for p in parts if p).strip() + "\n"


CASES: list[dict[str, Any]] = [
    {
        "id": "case01_career",
        "category": "career",
        "title": "Career — NTT vs foreign firm",
        "source": NTT_SOURCE,
        "pack_items": NTT_PACK_ITEMS,
        "expect_lenses_optional": True,
    },
    {
        "id": "case02_family",
        "category": "family / fertility",
        "title": "Family / fertility — second child question",
        "source": _fields_to_source(
            {
                "branch_period": "45歳",
                "triggering_event": "不妊治療を経て子どもを授かったあと、二人目を目指すかを考えた",
                "chosen_path": "妻と息子と三人で暮らす人生を続けること",
                "unchosen_path": "二人目を目指して治療を続けること",
                "current_context": "妻と息子との三人家族で暮らし、自分の会社を経営している",
                "present_question": "二人目を持っていたらどうだったか",
                "additional_context": "息子を可愛いと感じ、息子の友人が家に遊びに来ることを楽しいと感じている",
            }
        ),
        "pack_items": [
            ("family_context", "妻と息子との三人家族で暮らしている"),
            ("current_work", "現在は自分の会社を経営している"),
        ],
    },
    {
        "id": "case03_education",
        "category": "education",
        "title": "Education — university choice",
        "source": _fields_to_source(
            {
                "branch_period": "19歳",
                "triggering_event": "第一志望の大学に合格した",
                "chosen_path": "その大学へ進学すること",
                "unchosen_path": "別の大学へ進学すること",
                "current_context": "複数業界を経験したあと、文章や制作の仕事をしている",
                "present_question": "別の大学へ行っていたら、いまの仕事の感じ方は違ったか",
            }
        ),
        "pack_items": [
            ("career_history", "複数業界を経験した"),
            ("current_work", "文章や制作の仕事をしている"),
        ],
    },
    {
        "id": "case04_romance",
        "category": "romance / relationship",
        "title": "Romance — breakup branch",
        "source": _fields_to_source(
            {
                "branch_period": "20代後半",
                "triggering_event": "長く付き合っていた人と別れた",
                "chosen_path": "別れること",
                "unchosen_path": "一緒にいること",
                "current_context": "今は一人で普通に暮らしている",
                "present_question": "あのままだったらどうなっていたか",
                "additional_context": "思い出すと少し寂しい",
            }
        ),
        "pack_items": [
            ("major_life_events", "今は一人で普通に暮らしている"),
        ],
    },
    {
        "id": "case05_health",
        "category": "health / body",
        "title": "Health / body — treatment vs work pace",
        "source": _fields_to_source(
            {
                "branch_period": "38歳",
                "triggering_event": "体調を崩し、働き方を変えるかを考えた",
                "chosen_path": "仕事量を減らして治療と休養を優先すること",
                "unchosen_path": "以前と同じペースで働き続けること",
                "current_context": "治療を続けながら、在宅中心で仕事をしている",
                "present_question": "無理をして働き続けていたらどうなっていたか",
            }
        ),
        "pack_items": [
            ("major_life_events", "治療を続けながら在宅中心で仕事をしている"),
            ("current_work", "仕事量を抑えて働いている"),
        ],
        "sensitive": True,
    },
    {
        "id": "case06_entrepreneurship",
        "category": "entrepreneurship / business",
        "title": "Entrepreneurship — leave company to found",
        "source": _fields_to_source(
            {
                "branch_period": "33歳",
                "triggering_event": "会社を辞めて起業するかを選ぶ分岐があった",
                "chosen_path": "会社を辞めて自分の会社を始めること",
                "unchosen_path": "会社員として残ること",
                "current_context": "小さな会社を経営し、顧客向けの制作を続けている",
                "present_question": "会社に残っていたら、いまの不安は少なかったか",
            }
        ),
        "pack_items": [
            ("career_history", "会社を辞めて起業した"),
            ("current_work", "小さな会社を経営している"),
            ("current_projects", "顧客向けの制作を続けている"),
        ],
    },
    {
        "id": "case07_creative",
        "category": "creative work",
        "title": "Creative work — side project vs full-time craft",
        "source": _fields_to_source(
            {
                "branch_period": "29歳",
                "triggering_event": "創作を本業にするか、会社員のまま続けるかを考えた",
                "chosen_path": "会社員を続けながら創作を副業として続けること",
                "unchosen_path": "創作を本業にすること",
                "current_context": "平日は会社で働き、夜と週末に文章と写真の制作をしている",
                "present_question": "創作を本業にしていたら、いまの作り方は違ったか",
            }
        ),
        "pack_items": [
            ("current_work", "平日は会社で働いている"),
            ("current_creative_activity", "夜と週末に文章と写真の制作をしている"),
        ],
    },
    {
        "id": "case08_vague",
        "category": "vague or weak branch",
        "title": "Vague / weak branch — thin options",
        "source": _fields_to_source(
            {
                "branch_period": "二十代のどこか",
                "triggering_event": "何か選んだ気がする",
                "chosen_path": "よく覚えていない",
                "unchosen_path": "特に考えていなかった",
                "current_context": "今も普通に暮らしている",
                "present_question": "別の道があったのかな",
            }
        ),
        "pack_items": [],
        "expect_safe_stop_ok": True,
    },
    {
        "id": "case09_zero_lens",
        "category": "zero-lens-appropriate",
        "title": "Zero-lens-appropriate — quiet local stay",
        "source": _fields_to_source(
            {
                "branch_period": "22歳",
                "triggering_event": "地元に残るか、都会へ出るかを考えた",
                "chosen_path": "地元に残ること",
                "unchosen_path": "都会へ出ること",
                "current_context": "地元で事務の仕事をしながら、近所の人と暮らしている",
                "present_question": "都会へ出ていたら、いまの日常は違ったか",
            }
        ),
        "pack_items": [
            ("current_work", "地元で事務の仕事をしている"),
            ("relevant_social_context", "近所の人と暮らしている"),
        ],
        "expect_zero_lens_ok": True,
    },
    {
        "id": "case10_sensitive",
        "category": "sensitive causal restraint",
        "title": "Sensitive — illness timing vs career move",
        "source": _fields_to_source(
            {
                "branch_period": "41歳",
                "triggering_event": "大きな病気の診断を受けたあと、仕事を辞めるかを考えた",
                "chosen_path": "治療のため仕事を一旦離れること",
                "unchosen_path": "治療しながら同じ仕事を続けること",
                "current_context": "体調を見ながら短い仕事を再開している",
                "present_question": "働き続けていたら、病状や生活はどうなっていたか",
                "additional_context": "家族が看病を手伝ってくれた",
            }
        ),
        "pack_items": [
            ("major_life_events", "体調を見ながら短い仕事を再開している"),
            ("family_context", "家族が看病を手伝ってくれた"),
        ],
        "sensitive": True,
    },
]


def _section_bodies(body: str) -> dict[str, str]:
    parts = re.split(r"(?m)^##\s+", body or "")
    out = {}
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        out[lines[0].strip()] = "\n".join(lines[1:]).strip()
    return out


def verify_pins() -> dict:
    pack = build_approved_pack(NTT_PACK_ITEMS)
    code_s, strict = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": "pin strict",
            "language": "ja",
            "deep_reading_mode": "strict",
            "clarifications": {},
            "editorial_context": {},
        },
    )
    ss = (strict or {}).get("session") or {}
    sm = ss.get("model_metadata") or {}
    code_c, ctx = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": NTT_SOURCE,
            "language": "ja",
            "deep_reading_mode": "contextual",
            "context_pack": pack,
            "clarifications": {},
            "editorial_context": {},
        },
        timeout=300,
    )
    cs = (ctx or {}).get("session") or {}
    cm = cs.get("model_metadata") or {}
    c1 = cs.get("call1") or {}
    code_p, prod = req(
        PROD_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": "pin prod",
            "language": "ja",
            "deep_reading_mode": "contextual",
            "clarifications": {},
            "editorial_context": {},
        },
    )
    ps = (prod or {}).get("session") or {}
    pm = ps.get("model_metadata") or {}
    flags = probe_flags()
    return {
        "flags": flags,
        "staging_strict": {
            "http": code_s,
            "call1": (ss.get("prompt_versions") or {}).get("call_1")
            or sm.get("call_1_prompt_version"),
            "schema": ss.get("schema_version"),
        },
        "staging_contextual": {
            "http": code_c,
            "call1": (cs.get("prompt_versions") or {}).get("call_1")
            or cm.get("call_1_prompt_version")
            or c1.get("prompt_version"),
            "schema": cs.get("schema_version"),
            "pack": cm.get("context_pack_enabled"),
        },
        "production": {
            "http": code_p,
            "call1": (ps.get("prompt_versions") or {}).get("call_1")
            or pm.get("call_1_prompt_version"),
            "pack": pm.get("context_pack_enabled"),
        },
    }


def score_case(case: dict, pipe: dict, session: dict) -> dict:
    call1 = session.get("call1") or {}
    call3 = session.get("call3") or {}
    validation = call3.get("validation") or {}
    body = (pipe.get("manuscript") or {}).get("body_markdown") or call3.get("body_markdown") or ""
    title = (pipe.get("manuscript") or {}).get("title") or call3.get("final_title") or ""
    blob = f"{title}\n{body}"
    sections = _section_bodies(body)
    resume = section_resume_flags(blob) if body else {"resume_density": 0, "compression_required": False}
    dens = abstract_vocabulary_density(blob) if body else {"counts": {}, "excess": {}}

    lost = sections.get("失ったもの", "")
    prot = sections.get("守られたもの", "")
    residue = sections.get("今に残った構造", "")
    rebranch = sections.get("これからの再分岐", "")
    re_ok, re_missing, _ = re_branch_realization_check(rebranch, residue_body=residue) if rebranch else (False, ["absent"], {})
    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    reb_contract = next((c for c in contracts if c.get("section_id") == "re_branch"), {})
    re_omitted = bool(reb_contract) and not reb_contract.get("must_be_present")

    lenses = []
    sel = call1.get("selected_observatory_lenses") or {}
    selected = sel.get("selected") if isinstance(sel, dict) else sel
    for c in selected or []:
        if isinstance(c, dict):
            lenses.append(
                {
                    "lens_id": c.get("lens_id"),
                    "new_meaning_added": bool((c.get("new_meaning_added") or "").strip()),
                    "meaning": (c.get("new_meaning_added") or "")[:120],
                }
            )
    lens_added = any(x["new_meaning_added"] for x in lenses)

    blocking = list(validation.get("blocking_reasons") or [])
    unsupported_causality = list(validation.get("unsupported_causality") or [])
    unsupported_bio = list(
        validation.get("unsupported_personal_details")
        or validation.get("unsupported_scenes")
        or []
    )
    affect = list(validation.get("unsupported_affect") or [])
    schema_leak = list(validation.get("schema_leakage_prose") or [])
    title_ok = validation.get("title_validation", {})
    if isinstance(title_ok, dict):
        title_passed = title_ok.get("passed", "title_validation_failed" not in blocking)
    else:
        title_passed = "title_validation_failed" not in blocking

    coaching = bool(COACHING_RE.search(blob)) if blob else False
    schema_text = bool(SCHEMA_LEAK_RE.search(blob)) if blob else False
    lens_overreach = bool(re.search(r"(?:レンズ|Observatory|制度理論|社会学的に断言)", blob)) if blob else False

    # Pack usage: only approved pack ids should appear
    usage = (call1.get("context_pack_usage") or {}) if case.get("pack_items") else {}
    pack_facts = [
        f
        for f in ((call1.get("grounded_input") or {}).get("facts") or [])
        if f.get("source_field") == "context_pack" or "context_pack" in (f.get("tags") or [])
    ]
    unapproved_pack_use = False
    if not case.get("pack_items") and pack_facts:
        unapproved_pack_use = True

    lost_r = bool(re.search(r"(?:物差し|測り方|確かめ|目印|連続|手放)", lost)) if lost else False
    prot_r = bool(re.search(r"(?:余白|定義し直|別の言葉|固定しきら|預け)", prot)) if prot else False
    residue_r = bool(re.search(r"(?:問い|いまも|残|並べ|想像|物差し)", residue)) if residue else False

    publishable = bool(validation.get("publishable"))
    naturalness = 5
    depth = 5
    life_read = "n/a"
    if body:
        template_n = len(
            re.findall(r"(?:と読むことができる|とも言える|として見ることができる)", blob)
        )
        naturalness = 9 if template_n <= 2 and resume["resume_density"] <= 3 and not dens.get("excess") else (
            8 if resume["resume_density"] <= 3 and template_n <= 4 else 7
        )
        if coaching or schema_text:
            naturalness = min(naturalness, 6)
        depth = 9 if lost_r and prot_r and residue_r and (re_ok or re_omitted) else (
            8 if (lost_r or residue_r) and (re_ok or re_omitted or not reb_contract.get("must_be_present", True)) else 7
        )
        life_read = (
            "YES"
            if publishable and naturalness >= 8 and depth >= 8 and resume["resume_density"] <= 3
            else "mixed"
        )

    # Hard failures
    hard = []
    if unapproved_pack_use:
        hard.append("unapproved_context_pack_use")
    if publishable and blocking:
        hard.append("publishable_true_with_blocking")
    if unsupported_causality and case.get("sensitive"):
        hard.append("sensitive_unsupported_causality")
    if any("強制" in str(x) for x in lenses):
        hard.append("forced_observatory_lens")
    # Invented facts heuristic: medical/financial specifics not in source
    source = case.get("source") or ""
    invented_hits = []
    for phrase in ("年収", "診断名", "ステージ", "治った", "成功した起業"):
        if phrase in blob and phrase not in source:
            invented_hits.append(phrase)
    if invented_hits and case.get("sensitive"):
        hard.append(f"possible_invented_sensitive:{','.join(invented_hits)}")

    malformed_claims = [
        c.get("section_id")
        for c in contracts
        if claim_text_is_malformed(c.get("interpretive_claim") or "")
    ]

    call1_status = call1.get("status") or session.get("status")
    confirmation_issues = []
    if call1_status in {"needs_additional_input", "structural_ambiguity", "insufficient_current_context"}:
        confirmation_issues.append(f"call1_status:{call1_status}")
    if pipe.get("stages", {}).get("confirm", {}).get("status") != 200 and pipe.get("error"):
        confirmation_issues.append("confirm_failed")

    classification = "PASS"
    if hard:
        classification = "HARD_FAIL"
    elif not pipe.get("ok") and case.get("expect_safe_stop_ok") and not publishable:
        classification = "PASS_SAFE_STOP"
    elif publishable and naturalness >= 8 and depth >= 8 and life_read == "YES" and not hard:
        classification = "PASS"
    elif publishable:
        classification = "PASS_WITH_NOTES"
    elif pipe.get("stages", {}).get("edit", {}).get("status") == 200:
        classification = "GATE_BLOCKED"
    else:
        classification = "INCOMPLETE"

    return {
        "case_id": case["id"],
        "category": case["category"],
        "title": case["title"],
        "pipeline_ok": bool(pipe.get("ok")),
        "elapsed_s": pipe.get("elapsed_s"),
        "session_id": pipe.get("session_id"),
        "call1_status": call1_status,
        "call1_prompt": (session.get("prompt_versions") or {}).get("call_1")
        or ((session.get("model_metadata") or {}).get("call_1_prompt_version")),
        "call3_prompt": call3.get("prompt_version"),
        "factual_fidelity": 10 if not invented_hits else 7,
        "naturalness": naturalness if body else None,
        "depth": depth if body else None,
        "life_read": life_read,
        "resume_density": resume.get("resume_density"),
        "observatory_lenses": lenses,
        "lens_count": len(lenses),
        "lenses_added_meaning": lens_added,
        "lost_realization": lost_r,
        "protected_realization": prot_r,
        "residue_realization": residue_r,
        "rebranch_realization": re_ok,
        "rebranch_omitted_valid": re_omitted,
        "rebranch_missing": re_missing if rebranch else ["no_section"],
        "title_validation_passed": title_passed,
        "publishable": publishable,
        "blocking_reasons": blocking,
        "unsupported_causality_count": len(unsupported_causality),
        "unsupported_biography_count": len(unsupported_bio) if isinstance(unsupported_bio, list) else int(bool(unsupported_bio)),
        "affect_inference_count": len(affect) if isinstance(affect, list) else int(bool(affect)),
        "self_help_coaching_drift": coaching,
        "lens_overreach": lens_overreach,
        "schema_leakage": bool(schema_leak) or schema_text,
        "malformed_claims": malformed_claims,
        "unapproved_pack_use": unapproved_pack_use,
        "pack_fact_count": len(pack_facts),
        "confirmation_issues": confirmation_issues,
        "hard_failures": hard,
        "classification": classification,
        "final_title": title,
        "body_excerpt": body[:500],
        "abstract_vocab": dens.get("counts"),
    }


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V117
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V117_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
        and pins["flags"].get("production_context_pack_off") is True
    )
    if not ready:
        print(json.dumps({"error": "pins_not_ready", "pins": pins}, ensure_ascii=False, indent=2))
        REPORT.write_text(
            "# Public QA ABORTED — pins not ready\n\n```json\n"
            + json.dumps(pins, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        return 2

    results: list[dict] = []
    for i, case in enumerate(CASES, 1):
        print(f"[{i}/{len(CASES)}] {case['id']} ...", flush=True)
        pack = build_approved_pack(case["pack_items"]) if case.get("pack_items") else None
        # Even with empty pack_items, use contextual mode; omit pack key when none
        mode = "contextual"
        pipe = run_pipeline(
            STAGING_API,
            case_id=case["id"],
            arm="public_qa",
            source=case["source"],
            mode=mode,
            pack=pack,
        )
        # Prefer dumped session
        session = {}
        sp = (
            ROOT
            / "e2e_reports"
            / "deep-reading-v1.1-context-pack"
            / "live_ab"
            / case["id"]
            / "public_qa_session_final.json"
        )
        if sp.exists():
            session = json.loads(sp.read_text(encoding="utf-8"))
        scored = score_case(case, pipe, session)
        scored["pipeline_error"] = bool(pipe.get("error"))
        scored["stages"] = pipe.get("stages")
        results.append(scored)
        case_dir = OUT / case["id"]
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
    safety_block_violations = [
        r for r in results if "publishable_true_with_blocking" in (r.get("hard_failures") or [])
    ]
    nat_ok = sum(1 for r in publishable_cases if (r.get("naturalness") or 0) >= 8)
    depth_ok = sum(1 for r in publishable_cases if (r.get("depth") or 0) >= 8)
    life_ok = sum(1 for r in publishable_cases if r.get("life_read") == "YES")
    resume_ok = sum(1 for r in publishable_cases if (r.get("resume_density") or 99) <= 3)
    fidelity_ok = sum(1 for r in results if r.get("factual_fidelity") == 10)

    n_pub = max(1, len(publishable_cases))
    most_nat = nat_ok / n_pub >= 0.6 if publishable_cases else False
    most_depth = depth_ok / n_pub >= 0.6 if publishable_cases else False
    most_life = life_ok / n_pub >= 0.6 if publishable_cases else False

    if hard_fails or safety_block_violations:
        verdict = "V1.1 NOT READY"
    elif (
        publishable_cases
        and most_nat
        and most_depth
        and most_life
        and resume_ok == len(publishable_cases)
        and fidelity_ok == len(results)
        and not hard_fails
    ):
        verdict = "V1.1 READY FOR RELEASE CANDIDATE"
    else:
        verdict = "V1.1 PROMISING — NEEDS TARGETED FIXES"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "verdict": verdict,
        "summary": {
            "cases": len(results),
            "publishable": len(publishable_cases),
            "hard_fails": len(hard_fails),
            "fidelity_10": fidelity_ok,
            "publishable_naturalness_ge8": nat_ok,
            "publishable_depth_ge8": depth_ok,
            "publishable_life_read_yes": life_ok,
            "publishable_resume_le3": resume_ok,
        },
        "results": results,
        "no_auto_tune": True,
        "production_untouched": True,
    }
    RAW.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Parallel Life Deep Reading v1.1.7-exp — Staging Public QA",
        "",
        f"Generated: `{payload['generated_at']}`  ",
        f"Staging: `{STAGING_API}`  ",
        "Production: **untouched** (v1.0.2 / pack OFF)  ",
        "",
        "## Verdict",
        "",
        "```",
        verdict,
        "```",
        "",
        "**No prompt/runtime/schema/model changes during this QA. No auto-tune.**",
        "",
        "## Pins verified",
        "",
        f"- Staging Contextual Call1: `{pins['staging_contextual'].get('call1')}`",
        f"- Staging Contextual runtime: `{pins['staging_contextual'].get('schema')}`",
        f"- Staging pack: `{pins['staging_contextual'].get('pack')}`",
        f"- Staging Strict Call1: `{pins['staging_strict'].get('call1')}`",
        f"- Production Call1: `{pins['production'].get('call1')}` pack=`{pins['production'].get('pack')}`",
        "",
        "## Batch summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Cases | {len(results)} |",
        f"| Publishable | {len(publishable_cases)} |",
        f"| Hard failures | {len(hard_fails)} |",
        f"| Fidelity=10 | {fidelity_ok}/{len(results)} |",
        f"| Publishable naturalness≥8 | {nat_ok}/{len(publishable_cases)} |",
        f"| Publishable depth≥8 | {depth_ok}/{len(publishable_cases)} |",
        f"| Publishable life_read=YES | {life_ok}/{len(publishable_cases)} |",
        f"| Publishable resume≤3 | {resume_ok}/{len(publishable_cases)} |",
        "",
        "## Per-case matrix",
        "",
        "| Case | Cat | Pub | Fid | Nat | Depth | Life | Resume | Lenses | Lost | Prot | Res | Rebr | Title | Hard | Class |",
        "|------|-----|-----|-----|-----|-------|------|--------|--------|------|------|-----|------|-------|------|-------|",
    ]
    for r in results:
        lines.append(
            "| {id} | {cat} | {pub} | {fid} | {nat} | {dep} | {life} | {res} | {lens} | {lost} | {prot} | {residue} | {rebr} | {title} | {hard} | {cls} |".format(
                id=r["case_id"],
                cat=r["category"][:18],
                pub=r.get("publishable"),
                fid=r.get("factual_fidelity"),
                nat=r.get("naturalness"),
                dep=r.get("depth"),
                life=r.get("life_read"),
                res=r.get("resume_density"),
                lens=r.get("lens_count"),
                lost=r.get("lost_realization"),
                prot=r.get("protected_realization"),
                residue=r.get("residue_realization"),
                rebr=("omit" if r.get("rebranch_omitted_valid") else r.get("rebranch_realization")),
                title=r.get("title_validation_passed"),
                hard=";".join(r.get("hard_failures") or []) or "-",
                cls=r.get("classification"),
            )
        )

    lines.extend(["", "## Per-case notes", ""])
    for r in results:
        lines.append(f"### {r['case_id']} — {r['title']}")
        lines.append("")
        lines.append(f"- Classification: `{r['classification']}`")
        lines.append(f"- Call1 status: `{r.get('call1_status')}` · Call3: `{r.get('call3_prompt')}`")
        lines.append(
            f"- Lenses: `{[x.get('lens_id') for x in (r.get('observatory_lenses') or [])]}` "
            f"added_meaning=`{r.get('lenses_added_meaning')}`"
        )
        lines.append(
            f"- Safety counters: causality=`{r.get('unsupported_causality_count')}` "
            f"bio=`{r.get('unsupported_biography_count')}` affect=`{r.get('affect_inference_count')}` "
            f"coaching=`{r.get('self_help_coaching_drift')}` lens_overreach=`{r.get('lens_overreach')}` "
            f"schema_leak=`{r.get('schema_leakage')}`"
        )
        lines.append(f"- Blocking: `{r.get('blocking_reasons')}`")
        lines.append(f"- Confirmation issues: `{r.get('confirmation_issues')}`")
        lines.append(f"- Hard failures: `{r.get('hard_failures')}`")
        lines.append(f"- Title: {r.get('final_title')}")
        if r.get("body_excerpt"):
            lines.append("")
            lines.append("<details><summary>excerpt</summary>")
            lines.append("")
            lines.append(r["body_excerpt"][:400])
            lines.append("")
            lines.append("</details>")
        lines.append("")

    lines.extend(
        [
            "## Hard-failure checklist",
            "",
            f"| Check | Result |",
            f"|-------|--------|",
            f"| Invented personal facts (heuristic) | {'FAIL' if any('invented' in h for r in results for h in r.get('hard_failures') or []) else 'OK'} |",
            f"| Unsupported causality on sensitive | {'FAIL' if any('unsupported_causality' in h for r in results for h in r.get('hard_failures') or []) else 'OK'} |",
            f"| Unapproved Context Pack use | {'FAIL' if any(r.get('unapproved_pack_use') for r in results) else 'OK'} |",
            f"| Publishable=true with blockers | {'FAIL' if safety_block_violations else 'OK'} |",
            f"| Forced Observatory lens | {'FAIL' if any('forced_observatory' in h for r in results for h in r.get('hard_failures') or []) else 'OK'} |",
            "",
            "## Recommendation",
            "",
            "```",
            verdict,
            "```",
            "",
            "Artifacts: `e2e_reports/deep-reading-v1.1-public-qa/`",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "summary": payload["summary"]}, ensure_ascii=False, indent=2))
    print("Wrote", REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
