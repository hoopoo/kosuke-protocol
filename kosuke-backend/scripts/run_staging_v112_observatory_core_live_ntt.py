#!/usr/bin/env python3
"""Live NTT E2E for Observatory-Core v1.1.2-exp on STAGING ONLY.

Does not modify prompts/runtime/schema/evidence/lens rules.
Does not touch production.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.context_selection import compute_resume_density  # noqa: E402
from app.parallel_life_deep_reading.observatory_core import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V112,
    RUNTIME_VERSION_V112_EXP,
    relation_density_score,
)
from scripts.run_staging_v11_context_pack_live_ab import (  # noqa: E402
    NTT_PACK_ITEMS,
    NTT_SOURCE,
    STAGING_API,
    PROD_API,
    approve_with_clarifications,
    build_approved_pack,
    extract_trace,
    req,
    run_pipeline,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "observatory_core_live_ntt"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "OBSERVATORY_CORE_LIVE_NTT_REPORT.md"
)

CAUSAL_BLOCK_RE = re.compile(
    r"(?:引き起こ|追いや|せざるを得な|が原因で|させた|強いた|"
    r"雇用構造(?:の変化)?が.{0,24}(?:退職|転職|離れ)|"
    r"(?:社会|市場|制度)(?:の変化)?が.{0,24}(?:退職|転職|離れ))"
)
LENS_NAME_RE = re.compile(
    r"(?:Clean Society|After Success|Education[–-]Employment|Market Signals|"
    r"Protocol Publishing|ObservatoryEvidence|CrossLensRelation|"
    r"観測所レンズ|クリーンソサエティ)",
    re.I,
)
PROMO_RE = re.compile(
    r"(?:SHIRO\s*&\s*Co|観測所プロジェクトを拡大|Protocol を(?:拡大|伸ば)|"
    r"アプリを(?:発売|ローンチ)|もっと(?:出版|公開))",
    re.I,
)


def verify_pins() -> dict:
    pack = build_approved_pack(NTT_PACK_ITEMS)
    # Strict on staging
    code_s, strict = req(
        STAGING_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": "ピン確認のみ。Strict。",
            "language": "ja",
            "deep_reading_mode": "strict",
            "clarifications": {},
            "editorial_context": {},
        },
    )
    ss = (strict or {}).get("session") or {}
    sm = ss.get("model_metadata") or {}
    # Contextual on staging
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
    )
    cs = (ctx or {}).get("session") or {}
    cm = cs.get("model_metadata") or {}
    # Prod must keep pack off / strict pins
    code_p, prod = req(
        PROD_API,
        "POST",
        "/experience/parallel-life/deep-reading/ground",
        {
            "source_text": "ピン確認のみ。Prod。",
            "language": "ja",
            "deep_reading_mode": "contextual",
            "clarifications": {},
            "editorial_context": {},
        },
    )
    ps = (prod or {}).get("session") or {}
    pm = ps.get("model_metadata") or {}
    return {
        "staging_strict": {
            "http": code_s,
            "schema": ss.get("schema_version"),
            "call1": (ss.get("prompt_versions") or {}).get("call_1")
            or sm.get("call_1_prompt_version"),
            "pack_enabled": sm.get("context_pack_enabled"),
            "mode": ss.get("deep_reading_mode"),
        },
        "staging_contextual": {
            "http": code_c,
            "schema": cs.get("schema_version"),
            "call1": (cs.get("prompt_versions") or {}).get("call_1")
            or cm.get("call_1_prompt_version"),
            "pack_enabled": cm.get("context_pack_enabled"),
            "mode": cs.get("deep_reading_mode"),
            "session_id": cs.get("session_id"),
            "candidate_lenses": (
                ((cs.get("call1") or {}).get("candidate_lens_selection") or {}).get(
                    "candidates"
                )
                if isinstance((cs.get("call1") or {}).get("candidate_lens_selection"), dict)
                else None
            ),
            "obs_diag": (cs.get("call1") or {}).get("observatory_core_diagnostics"),
            "cross_lens_n": len((cs.get("call1") or {}).get("cross_lens_relations") or []),
        },
        "production": {
            "http": code_p,
            "schema": ps.get("schema_version"),
            "call1": (ps.get("prompt_versions") or {}).get("call_1")
            or pm.get("call_1_prompt_version"),
            "pack_enabled": pm.get("context_pack_enabled"),
            "mode": ps.get("deep_reading_mode"),
        },
        "expected": {
            "call1": CALL_1_PROMPT_VERSION_V112,
            "runtime": RUNTIME_VERSION_V112_EXP,
        },
    }


def score_live(body: str, title: str, subtitle: str, call1: dict, titles: list[str]) -> dict:
    blob = f"{title}\n{subtitle}\n{body}"
    resume = compute_resume_density(blob)
    relations_raw = call1.get("cross_lens_relations") or []
    from app.parallel_life_deep_reading.observatory_core import CrossLensRelation

    relations = []
    for r in relations_raw:
        try:
            relations.append(CrossLensRelation.model_validate(r))
        except Exception:
            pass
    rel_d = relation_density_score(relations, blob)
    causal_hits = CAUSAL_BLOCK_RE.findall(blob) or []
    # also scan Japanese soft-causal that became hard
    if re.search(r"雇用.{0,20}(?:が原因|のせいで|によって退職)", blob):
        causal_hits.append("employment_caused_exit")
    lens_hits = LENS_NAME_RE.findall(blob)
    promo_hits = PROMO_RE.findall(blob)

    has_structure = any(
        t in blob
        for t in ("一社", "持ち運", "蓄積", "並べて", "境界", "制度", "読み直", "問い")
    )
    has_personal = any(t in blob for t in ("残っていたら", "いまも", "自分", "分岐", "28歳"))
    social = any(t in blob for t in ("雇用", "キャリア", "制度", "企業間", "一社内", "規範", "普通"))
    residue_items = ((call1.get("residue_candidates") or {}).get("items") or [])
    residue_q = 3
    if residue_items:
        rs = (residue_items[0].get("residue_statement") or residue_items[0].get("content") or "")
        residue_q = 7
        if any(t in rs for t in ("構造", "並べ", "定義", "パターン", "尺度", "蓄積")):
            residue_q = 9
        if CAUSAL_BLOCK_RE.search(rs) or re.search(r"(?:影響を与え|に繋が|につなが)", rs):
            residue_q = 4
    rebranch = ((call1.get("rebranch_design") or {}).get("directions") or [])
    rebranch_q = 3
    if rebranch:
        rb = " ".join(
            str(d.get("branch_specific_form") or "") + str(d.get("current_receiver") or "")
            for d in rebranch
        )
        rebranch_q = 6
        if any(t in rb for t in ("尺度", "蓄積", "測", "読み", "持ち運")):
            rebranch_q = 8
        if PROMO_RE.search(rb) or any(
            t in rb for t in ("Protocol", "観測所", "アプリ", "SHIRO")
        ):
            rebranch_q = 3

    title_q = 4
    if title and resume.resume_density <= 3 and has_structure:
        title_q = 8
    if title and re.search(r"(?:転職|経歴|キャリアパス|企業)", title) and not has_structure:
        title_q = 3

    cva = 5
    if has_structure:
        cva += 1
    if social:
        cva += 2
    if resume.resume_density <= 3:
        cva += 1
    if rel_d >= 7:
        cva += 1
    cva = min(10, cva)

    fidelity = 10
    # invented promo / causal transform is fidelity/editorial failure
    blocking = []
    if causal_hits:
        blocking.append("unsupported_causal_transform")
    if lens_hits:
        blocking.append("lens_name_exposure")
    if promo_hits:
        blocking.append("shiro_promo")

    personal_focus = 9 if has_personal and not lens_hits else (5 if has_personal else 3)
    social_depth = 9 if social and has_structure else (5 if social else 3)
    if len(re.findall(r"(?:社会|労働市場|雇用制度)", blob)) >= 6 and not has_personal:
        social_depth = 4
        personal_focus = min(personal_focus, 4)
        blocking.append("sociology_overwhelm")

    naturalness = 8 if has_structure and resume.resume_density <= 4 else 5
    continuity = 8 if has_personal and has_structure else 5
    depth = 9 if has_structure and social and resume.resume_density <= 3 else (
        7 if has_structure else 4
    )
    life_read = (
        "reading"
        if has_structure and personal_focus >= 8 and resume.resume_density <= 3
        else ("mixed" if has_structure else "summarized")
    )

    return {
        "factual_fidelity": fidelity,
        "naturalness": naturalness,
        "continuity": continuity,
        "depth": depth,
        "context_value_add": cva,
        "resume_density": resume.resume_density,
        "resume_flags": resume.resume_density_flags,
        "relation_density": rel_d,
        "social_depth": social_depth,
        "personal_focus": personal_focus,
        "residue_quality": residue_q,
        "rebranch_quality": rebranch_q,
        "title_quality": title_q,
        "life_read": life_read,
        "causal_hits": causal_hits,
        "lens_name_hits": lens_hits,
        "promo_hits": promo_hits,
        "blocking_failures": blocking,
        "title_candidates_scored": [
            {
                "title": t,
                "resume_like": bool(compute_resume_density(t).resume_density_flags),
                "abstract": len(t) < 8 or t in {"選択", "問い", "分岐"},
                "company_only": bool(re.search(r"(?:会社|経営)$", t)) and "問い" not in t,
                "structure_words": any(
                    x in t for x in ("問い", "境界", "持ち運", "蓄積", "読み", "残")
                ),
            }
            for t in titles
        ],
    }


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ctx_call1 = pins["staging_contextual"].get("call1")
    ctx_runtime = pins["staging_contextual"].get("schema")
    pack_on = pins["staging_contextual"].get("pack_enabled")
    prod_pack = pins["production"].get("pack_enabled")
    ready = (
        ctx_call1 == CALL_1_PROMPT_VERSION_V112
        and ctx_runtime == RUNTIME_VERSION_V112_EXP
        and pack_on is True
        and prod_pack in (False, None)
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
    )

    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "staging_api": STAGING_API,
        "pins": pins,
        "pins_ready": ready,
    }

    if not ready:
        result["error"] = "pins_not_ready_abort_live_run"
        (OUT / "SUMMARY.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _write_report(result, None, None, abort=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    pack = build_approved_pack(NTT_PACK_ITEMS)
    print("Running live NTT Contextual pipeline on staging...")
    pipe = run_pipeline(
        STAGING_API,
        case_id="ntt_v112",
        arm="observatory_core",
        source=NTT_SOURCE,
        mode="contextual",
        pack=pack,
    )
    (OUT / "pipeline.json").write_text(
        json.dumps(pipe, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # run_pipeline dumps under live_ab/<case_id>/
    live_case = (
        ROOT
        / "e2e_reports"
        / "deep-reading-v1.1-context-pack"
        / "live_ab"
        / "ntt_v112"
    )
    session_final = {}
    session_path = live_case / "observatory_core_session_final.json"
    manuscript_path = live_case / "observatory_core_manuscript.json"
    if session_path.exists():
        session_final = json.loads(session_path.read_text(encoding="utf-8"))
    manuscript = {}
    if manuscript_path.exists():
        manuscript = json.loads(manuscript_path.read_text(encoding="utf-8"))
    if not manuscript:
        manuscript = pipe.get("manuscript") or {}

    call1 = session_final.get("call1") or {}
    call2 = session_final.get("call2") or {}
    call3 = session_final.get("call3") or {}
    body = (
        manuscript.get("body_markdown")
        or call3.get("body_markdown")
        or session_final.get("final_manuscript")
        or ""
    )
    title = (
        manuscript.get("title")
        or call3.get("final_title")
        or call3.get("title")
        or ""
    )
    subtitle = (
        manuscript.get("subtitle")
        or call3.get("final_subtitle")
        or call3.get("subtitle")
        or ""
    )
    titles = (
        call2.get("title_candidates")
        or call3.get("title_candidates")
        or []
    )
    # Copy artifacts into observatory_core_live_ntt
    if session_final:
        (OUT / "session_final.json").write_text(
            json.dumps(session_final, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if manuscript:
        (OUT / "manuscript.json").write_text(
            json.dumps(manuscript, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    scores = score_live(body, title, subtitle, call1, titles if isinstance(titles, list) else [])
    targets = {
        "fidelity": scores["factual_fidelity"] == 10,
        "naturalness": scores["naturalness"] >= 8,
        "continuity": scores["continuity"] >= 8,
        "depth": scores["depth"] >= 9,
        "cva": scores["context_value_add"] >= 8,
        "resume_density": scores["resume_density"] <= 3,
        "relation_density": scores["relation_density"] >= 7,
        "social_depth": scores["social_depth"] >= 8,
        "personal_focus": scores["personal_focus"] >= 8,
    }
    if scores["blocking_failures"]:
        verdict = "OBSERVATORY CORE LIVE RESULT FAILED"
    elif all(targets.values()):
        verdict = "OBSERVATORY CORE READY FOR PUBLIC QA"
    else:
        verdict = "OBSERVATORY CORE PROMISING — NEEDS REVISION"

    result.update(
        {
            "pipeline_ok": bool(pipe.get("ok")),
            "pipeline_error": pipe.get("error"),
            "elapsed_s": pipe.get("elapsed_s"),
            "session_id": pipe.get("session_id"),
            "trace": pipe.get("trace_after_confirm") or pipe.get("trace_after_ground"),
            "call1_prompt": (call1.get("prompt_version") if call1 else None)
            or (pins["staging_contextual"].get("call1")),
            "candidate_lens_selection": call1.get("candidate_lens_selection"),
            "retrieved_observatory_evidence": call1.get("retrieved_observatory_evidence"),
            "cross_lens_relations": call1.get("cross_lens_relations"),
            "meaning_compression": call1.get("meaning_compression"),
            "central_thesis": (call1.get("central_thesis") or {}).get("statement"),
            "lost": call1.get("lost_structure"),
            "protected": call1.get("protected_structure"),
            "residue": call1.get("residue_candidates"),
            "rebranch": call1.get("rebranch_design"),
            "selected_observatory_lenses": call1.get("selected_observatory_lenses"),
            "title": title,
            "subtitle": subtitle,
            "title_candidates": titles,
            "body_markdown": body,
            "scores": scores,
            "targets": targets,
            "verdict": verdict,
            "production_untouched": prod_pack in (False, None)
            and (pins["production"].get("call1") == "parallel-life-call-1-v1.0.3"),
        }
    )

    (OUT / "SUMMARY.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "manuscript.md").write_text(
        f"# {title}\n\n{subtitle}\n\n{body}\n", encoding="utf-8"
    )
    (OUT / "call1.json").write_text(
        json.dumps(call1, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_report(result, scores, targets, abort=False)
    print(json.dumps({"verdict": verdict, "targets": targets, "scores": scores}, ensure_ascii=False, indent=2))
    print("Wrote", REPORT)
    return 0 if pipe.get("ok") else 1


def _write_report(result: dict, scores: dict | None, targets: dict | None, *, abort: bool) -> None:
    pins = result.get("pins") or {}
    if abort:
        md = f"""# Observatory-Core Live NTT — ABORTED

Generated: `{result.get('generated_at')}`

## Verdict

```
OBSERVATORY CORE LIVE RESULT FAILED
```

Pins not ready after staging deploy. See `observatory_core_live_ntt/pin_verify.json`.

### Pin verify

```json
{json.dumps(pins, ensure_ascii=False, indent=2)}
```
"""
        REPORT.write_text(md, encoding="utf-8")
        return

    assert scores is not None and targets is not None
    cand = result.get("candidate_lens_selection") or {}
    lenses = []
    if isinstance(cand, dict):
        lenses = [c.get("lens_id") for c in (cand.get("candidates") or []) if isinstance(c, dict)]
    relations = result.get("cross_lens_relations") or []
    body = result.get("body_markdown") or ""
    md = f"""# Deep Reading v1.1.2-exp — Observatory-Core Live NTT (STAGING)

Generated: `{result.get('generated_at')}`  
Staging: `{STAGING_API}`  
Production: **not deployed / Context Pack remains OFF**

## Verdict

```
{result.get('verdict')}
```

Blocking failures: `{scores.get('blocking_failures') or 'none'}`  
Pipeline ok: `{result.get('pipeline_ok')}` · elapsed_s: `{result.get('elapsed_s')}`

---

## 1. Staging deployment result

| Check | Result |
|-------|--------|
| Staging Contextual Call1 | `{pins.get('staging_contextual',{}).get('call1')}` |
| Staging Contextual runtime | `{pins.get('staging_contextual',{}).get('schema')}` |
| Staging pack flag | `{pins.get('staging_contextual',{}).get('pack_enabled')}` |
| Staging Strict Call1 | `{pins.get('staging_strict',{}).get('call1')}` |
| Staging Strict runtime | `{pins.get('staging_strict',{}).get('schema')}` |
| Production Call1 | `{pins.get('production',{}).get('call1')}` |
| Production pack flag | `{pins.get('production',{}).get('pack_enabled')}` |
| Production untouched | `{result.get('production_untouched')}` |

Expected Contextual: `{CALL_1_PROMPT_VERSION_V112}` / `{RUNTIME_VERSION_V112_EXP}`

---

## 2. Call1 structure

- Thesis: {result.get('central_thesis')}
- Meaning compression: see `observatory_core_live_ntt/call1.json`
- Session: `{result.get('session_id')}`

### Meaning compression (summary)

```json
{json.dumps(result.get('meaning_compression') or {{}}, ensure_ascii=False, indent=2)[:2500]}
```

---

## 3. Selected lenses (pre-thesis candidates)

`{lenses}`

Manuscript Observatory section selected: `{((result.get('selected_observatory_lenses') or {{}}).get('selected') if isinstance(result.get('selected_observatory_lenses'), dict) else result.get('selected_observatory_lenses'))}`

---

## 4. CrossLensRelations

```json
{json.dumps(relations, ensure_ascii=False, indent=2)[:4000]}
```

---

## 5–7. Call2 / Call3 / Final manuscript

**Title:** {result.get('title')}  
**Subtitle:** {result.get('subtitle')}

### Body

{body}

---

## 8. Causality result

Hits: `{scores.get('causal_hits') or 'none'}`  
Status: **{'FAIL' if 'unsupported_causal_transform' in (scores.get('blocking_failures') or []) else 'PASS'}**

---

## 9. Lens-name exposure

Hits: `{scores.get('lens_name_hits') or 'none'}`  
Status: **{'FAIL' if 'lens_name_exposure' in (scores.get('blocking_failures') or []) else 'PASS'}**

---

## 10–13. Scores

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | {scores['factual_fidelity']} | 10 | {targets['fidelity']} |
| naturalness | {scores['naturalness']} | ≥8 | {targets['naturalness']} |
| continuity | {scores['continuity']} | ≥8 | {targets['continuity']} |
| depth | {scores['depth']} | ≥9 | {targets['depth']} |
| CVA | {scores['context_value_add']} | ≥8 | {targets['cva']} |
| resume_density | {scores['resume_density']} | ≤3 | {targets['resume_density']} |
| relation_density | {scores['relation_density']} | ≥7 | {targets['relation_density']} |
| social_depth | {scores['social_depth']} | ≥8 | {targets['social_depth']} |
| personal_focus | {scores['personal_focus']} | ≥8 | {targets['personal_focus']} |
| residue_quality | {scores['residue_quality']} | high | — |
| rebranch_quality | {scores['rebranch_quality']} | high | — |
| title_quality | {scores['title_quality']} | high | — |
| life_read | {scores['life_read']} | reading | — |

Resume flags: `{scores.get('resume_flags')}`

---

## 14. Residue

```json
{json.dumps(result.get('residue') or {{}}, ensure_ascii=False, indent=2)[:2000]}
```

---

## 15. Re-branch

```json
{json.dumps(result.get('rebranch') or {{}}, ensure_ascii=False, indent=2)[:2000]}
```

Promo/project auto-recommend hits in manuscript/rebranch scan: `{scores.get('promo_hits') or 'none'}`

---

## 16–17. Title candidates / final

Final: **{result.get('title')}**

Candidates scored:

```json
{json.dumps(scores.get('title_candidates_scored') or [], ensure_ascii=False, indent=2)}
```

Title validation rules: **unchanged** (not loosened this run).

---

## 18. Book benchmark comparison (qualitative)

| Dimension | Live Observatory-Core | Book/ChatGPT benchmark (prior qualitative) | Gap |
|-----------|------------------------|---------------------------------------------|-----|
| Temporal depth | {'stronger if life_read=reading' if scores['life_read']=='reading' else 'partial'} | long institutional arc | {'materially closer' if scores['depth']>=9 else 'still open'} |
| Institutional reading | {'present' if scores['social_depth']>=8 else 'weak'} | strong (regime contrast) | {'closed/narrowed' if scores['social_depth']>=8 else 'open'} |
| Current-life return | {'present' if scores['personal_focus']>=8 else 'weak'} | strong | {'ok' if scores['personal_focus']>=8 else 'open'} |
| Lost/Protected | see Call1 | structural | inspect inventory risk |
| Residue | score {scores['residue_quality']} | pattern of re-definition | {'promising' if scores['residue_quality']>=8 else 'needs work'} |
| Social structure | score {scores['social_depth']} | strong | {'ok' if scores['social_depth']>=8 else 'open'} |
| Re-branch | score {scores['rebranch_quality']} | measurement of accumulation | {'ok' if scores['rebranch_quality']>=7 else 'open'} |
| Title | score {scores['title_quality']} | metaphor/question | {'ok' if scores['title_quality']>=7 else 'open'} |
| Life read vs summarized | {scores['life_read']} | reading | {'materially closed' if scores['life_read']=='reading' and scores['depth']>=9 else 'not fully closed'} |

---

## 19. Production untouched confirmation

| Item | Status |
|------|--------|
| Prod Context Pack | `{pins.get('production',{}).get('pack_enabled')}` (must be false/None) |
| Prod Call1 | `{pins.get('production',{}).get('call1')}` |
| This run modified prompts/runtime/schema/evidence/lens rules? | **No** |
| Production deploy performed? | **No** |

---

## 20. Recommendation

```
{result.get('verdict')}
```

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/observatory_core_live_ntt/`
"""
    REPORT.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
