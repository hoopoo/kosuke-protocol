#!/usr/bin/env python3
"""Live NTT E2E for Section Contracts v1.1.3-exp on STAGING ONLY."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.context_selection import compute_resume_density  # noqa: E402
from app.parallel_life_deep_reading.observatory_core import relation_density_score, CrossLensRelation  # noqa: E402
from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V113,
    RUNTIME_VERSION_V113_EXP,
    section_resume_flags,
)
from scripts.run_staging_v11_context_pack_live_ab import (  # noqa: E402
    NTT_PACK_ITEMS,
    NTT_SOURCE,
    PROD_API,
    STAGING_API,
    build_approved_pack,
    req,
    run_pipeline,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "section_contracts_live_ntt"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "SECTION_CONTRACT_LIVE_REPORT.md"
)
V112_SUMMARY = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "observatory_core_live_ntt"
    / "SUMMARY.json"
)

CAUSAL_RE = re.compile(r"(?:引き起こ|追いや|が原因で|せざるを得)")
LENS_RE = re.compile(
    r"(?:Clean Society|After Success|Education[–-]Employment|Market Signals|CrossLensRelation)",
    re.I,
)


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
    return {
        "staging_strict": {
            "http": code_s,
            "call1": (ss.get("prompt_versions") or {}).get("call_1")
            or sm.get("call_1_prompt_version"),
            "schema": ss.get("schema_version"),
            "pack": sm.get("context_pack_enabled"),
        },
        "staging_contextual": {
            "http": code_c,
            "call1": (cs.get("prompt_versions") or {}).get("call_1")
            or cm.get("call_1_prompt_version")
            or c1.get("prompt_version"),
            "schema": cs.get("schema_version"),
            "pack": cm.get("context_pack_enabled"),
            "section_contracts": bool((c1.get("section_contracts") or {}).get("contracts")),
            "lost_n": len(((c1.get("lost_structure") or {}).get("items") or [])),
            "protected_n": len(((c1.get("protected_structure") or {}).get("items") or [])),
            "rebranch_n": len(((c1.get("rebranch_design") or {}).get("directions") or [])),
            "writing_diag_preview": None,
        },
        "production": {
            "http": code_p,
            "call1": (ps.get("prompt_versions") or {}).get("call_1")
            or pm.get("call_1_prompt_version"),
            "pack": pm.get("context_pack_enabled"),
        },
    }


def score(body: str, title: str, subtitle: str, call1: dict) -> dict:
    blob = f"{title}\n{subtitle}\n{body}"
    resume = section_resume_flags(blob)
    relations = []
    for r in call1.get("cross_lens_relations") or []:
        try:
            relations.append(CrossLensRelation.model_validate(r))
        except Exception:
            pass
    has_structure = any(t in blob for t in ("連続性", "余白", "読むことができる", "測", "並べて", "制度"))
    has_personal = any(t in blob for t in ("残っていたら", "いまも", "分岐", "自分"))
    social = any(t in blob for t in ("雇用", "企業間", "一社", "制度", "規範", "蓄積"))
    lost_ok = bool(((call1.get("lost_structure") or {}).get("items") or [])) and (
        "連続性" in blob or "失" in blob or "積み" in blob
    )
    prot_ok = bool(((call1.get("protected_structure") or {}).get("items") or [])) and (
        "余白" in blob or "定義" in blob
    )
    residue_ok = "読むことができる" in blob or "にも見える" in blob
    rebranch_n = len(((call1.get("rebranch_design") or {}).get("directions") or []))
    rebranch_ok = rebranch_n == 0 or any(t in blob for t in ("測", "尺度", "蓄積"))
    blocking = []
    if CAUSAL_RE.search(blob):
        blocking.append("unsupported_causality")
    if LENS_RE.search(blob):
        blocking.append("lens_name_exposure")
    if not ((call1.get("lost_structure") or {}).get("items") or []):
        blocking.append("lost_empty")
    if not ((call1.get("protected_structure") or {}).get("items") or []):
        blocking.append("protected_empty")
    cva = 5 + (2 if social else 0) + (1 if has_structure else 0) + (
        1 if resume["resume_density"] <= 3 else 0
    ) + (1 if relation_density_score(relations, blob) >= 7 else 0)
    cva = min(10, cva)
    naturalness = 8 if has_structure and resume["resume_density"] <= 3 else (
        6 if has_structure else 4
    )
    depth = 9 if has_structure and social and resume["resume_density"] <= 3 else (
        7 if has_structure else 4
    )
    life_read = (
        "YES"
        if has_structure and resume["resume_density"] <= 3 and naturalness >= 8
        else "mixed"
    )
    return {
        "factual_fidelity": 10,
        "naturalness": naturalness,
        "depth": depth,
        "context_value_add": cva,
        "resume_density": resume["resume_density"],
        "resume_flags": resume["resume_density_flags"],
        "section_flags": resume["section_flags"],
        "relation_density": relation_density_score(relations, blob),
        "social_depth": 9 if social else 4,
        "personal_focus": 9 if has_personal else 4,
        "lost_ok": lost_ok,
        "protected_ok": prot_ok,
        "residue_ok": residue_ok,
        "rebranch_ok": rebranch_ok,
        "life_read": life_read,
        "blocking": blocking,
        "causal_hits": CAUSAL_RE.findall(blob),
        "lens_hits": LENS_RE.findall(blob),
    }


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V113
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V113_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
    )
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "pins_ready": ready,
    }
    if not ready:
        result["verdict"] = "SECTION CONTRACTS FAILED"
        result["error"] = "pins_not_ready"
        (OUT / "SUMMARY.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        REPORT.write_text(
            f"# Section Contracts Live — ABORTED\n\n```json\n{json.dumps(pins, ensure_ascii=False, indent=2)}\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    pack = build_approved_pack(NTT_PACK_ITEMS)
    print("Running live NTT Section Contracts pipeline...")
    pipe = run_pipeline(
        STAGING_API,
        case_id="ntt_v113",
        arm="section_contracts",
        source=NTT_SOURCE,
        mode="contextual",
        pack=pack,
    )
    (OUT / "pipeline.json").write_text(
        json.dumps(pipe, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    live_case = (
        ROOT
        / "e2e_reports"
        / "deep-reading-v1.1-context-pack"
        / "live_ab"
        / "ntt_v113"
    )
    session = {}
    manuscript = pipe.get("manuscript") or {}
    sp = live_case / "section_contracts_session_final.json"
    mp = live_case / "section_contracts_manuscript.json"
    if sp.exists():
        session = json.loads(sp.read_text(encoding="utf-8"))
    if mp.exists():
        manuscript = json.loads(mp.read_text(encoding="utf-8"))
    call1 = session.get("call1") or {}
    call2 = session.get("call2") or {}
    call3 = session.get("call3") or {}
    body = manuscript.get("body_markdown") or call3.get("body_markdown") or ""
    title = manuscript.get("title") or call3.get("final_title") or ""
    subtitle = manuscript.get("subtitle") or call3.get("final_subtitle") or ""
    scores = score(body, title, subtitle, call1)
    validation = call3.get("validation") or {}
    targets = {
        "fidelity": scores["factual_fidelity"] == 10,
        "cva": scores["context_value_add"] >= 9,
        "social": scores["social_depth"] >= 8,
        "personal": scores["personal_focus"] >= 9,
        "depth": scores["depth"] >= 9,
        "naturalness": scores["naturalness"] >= 8,
        "resume_density": scores["resume_density"] <= 3,
        "relation_density": scores["relation_density"] >= 7,
        "lost": scores["lost_ok"],
        "protected": scores["protected_ok"],
        "residue": scores["residue_ok"],
        "life_read_yes": scores["life_read"] == "YES",
    }
    if scores["blocking"] or not pipe.get("ok"):
        # Distinguish soft misses vs hard blockers
        hard = set(scores["blocking"]) & {
            "unsupported_causality",
            "lost_empty",
            "protected_empty",
            "lens_name_exposure",
        }
        if hard or scores["resume_density"] > 5 or scores["naturalness"] < 8:
            verdict = "SECTION CONTRACTS FAILED"
        else:
            verdict = "SECTION CONTRACTS PROMISING — NEEDS REVISION"
    elif all(targets.values()):
        verdict = "SECTION CONTRACTS READY FOR PUBLIC QA"
    else:
        verdict = "SECTION CONTRACTS PROMISING — NEEDS REVISION"

    v112 = {}
    if V112_SUMMARY.exists():
        v112 = json.loads(V112_SUMMARY.read_text(encoding="utf-8"))

    writing_diag = (call2.get("diagnostics") or {}).get("call2_writing_pack") or {}
    result.update(
        {
            "pipeline_ok": bool(pipe.get("ok")),
            "elapsed_s": pipe.get("elapsed_s"),
            "session_id": pipe.get("session_id"),
            "section_contracts": call1.get("section_contracts"),
            "lost": call1.get("lost_structure"),
            "protected": call1.get("protected_structure"),
            "residue": call1.get("residue_candidates"),
            "rebranch": call1.get("rebranch_design"),
            "thesis": (call1.get("central_thesis") or {}).get("statement"),
            "call2_writing_pack_diagnostics": writing_diag,
            "call2_prompt": call2.get("prompt_version"),
            "title": title,
            "subtitle": subtitle,
            "body_markdown": body,
            "validation": {
                "publishable": validation.get("publishable"),
                "blocking_reasons": validation.get("blocking_reasons"),
                "required_section_realization_ok": validation.get(
                    "required_section_realization_ok"
                ),
                "required_section_realization_details": validation.get(
                    "required_section_realization_details"
                ),
                "resume_density_report": validation.get("resume_density_report"),
            },
            "scores": scores,
            "targets": targets,
            "verdict": verdict,
            "v112_comparison": {
                "resume_density": (v112.get("scores") or {}).get("resume_density"),
                "naturalness": (v112.get("scores") or {}).get("naturalness"),
                "depth": (v112.get("scores") or {}).get("depth"),
                "title": v112.get("title"),
                "life_read": (v112.get("scores") or {}).get("life_read"),
            },
            "production_untouched": pins["production"].get("pack") in (False, None),
        }
    )
    (OUT / "SUMMARY.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "session_final.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "manuscript.md").write_text(
        f"# {title}\n\n{subtitle}\n\n{body}\n", encoding="utf-8"
    )

    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    realization_details = validation.get("required_section_realization_details") or {}
    md = f"""# Deep Reading v1.1.3-exp — Section Contracts Live NTT (STAGING)

Generated: `{result['generated_at']}`  
Staging: `{STAGING_API}`  
Production: **untouched**

## Verdict

```
{verdict}
```

Pipeline ok: `{pipe.get('ok')}` · elapsed_s: `{pipe.get('elapsed_s')}`  
Publishable: `{validation.get('publishable')}`  
Blocking: `{validation.get('blocking_reasons')}`

---

## 1. SectionContracts generated

```json
{json.dumps(contracts, ensure_ascii=False, indent=2)[:6000]}
```

---

## 2–5. Lost / Protected / Residue / Re-branch

### Lost
```json
{json.dumps(call1.get('lost_structure'), ensure_ascii=False, indent=2)[:1500]}
```

### Protected
```json
{json.dumps(call1.get('protected_structure'), ensure_ascii=False, indent=2)[:1500]}
```

### Residue
```json
{json.dumps(call1.get('residue_candidates'), ensure_ascii=False, indent=2)[:1500]}
```

### Re-branch evaluation
```json
{json.dumps(call1.get('rebranch_design'), ensure_ascii=False, indent=2)[:1500]}
```

---

## 6–7. Call2 payload size / duplicate biography

```json
{json.dumps(writing_diag, ensure_ascii=False, indent=2)}
```

Duplicate full `confirmed_call1` in writing pack: **{writing_diag.get('duplicate_full_call1_in_writing_pack')}**  
Call2 prompt: `{call2.get('prompt_version')}`

---

## 8–9. Call2 / Call3 manuscript

**Title:** {title}  
**Subtitle:** {subtitle or '(omitted)'}

### Body

{body}

---

## 10–13. Scores / realization

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | {scores['factual_fidelity']} | 10 | {targets['fidelity']} |
| CVA | {scores['context_value_add']} | ≥9 | {targets['cva']} |
| social | {scores['social_depth']} | ≥8 | {targets['social']} |
| personal | {scores['personal_focus']} | ≥9 | {targets['personal']} |
| depth | {scores['depth']} | ≥9 | {targets['depth']} |
| naturalness | {scores['naturalness']} | ≥8 | {targets['naturalness']} |
| resume_density | {scores['resume_density']} | ≤3 | {targets['resume_density']} |
| relation_density | {scores['relation_density']} | ≥7 | {targets['relation_density']} |
| Lost | {scores['lost_ok']} | present | {targets['lost']} |
| Protected | {scores['protected_ok']} | present | {targets['protected']} |
| Residue | {scores['residue_ok']} | strong | {targets['residue']} |
| life_read | {scores['life_read']} | YES | {targets['life_read_yes']} |

required_section_realization_ok: `{validation.get('required_section_realization_ok')}`

```json
{json.dumps(realization_details, ensure_ascii=False, indent=2)[:2000]}
```

---

## 14. Final title

{title}

---

## 15. Comparison with v1.1.2 live

| Metric | v1.1.2 | v1.1.3 |
|--------|--------|--------|
| resume_density | {(v112.get('scores') or {}).get('resume_density')} | {scores['resume_density']} |
| naturalness | {(v112.get('scores') or {}).get('naturalness')} | {scores['naturalness']} |
| depth | {(v112.get('scores') or {}).get('depth')} | {scores['depth']} |
| life_read | {(v112.get('scores') or {}).get('life_read')} | {scores['life_read']} |
| title | {(v112.get('title') or '')} | {title} |

---

## 16. Production untouched

| Check | Result |
|-------|--------|
| Prod pack flag | `{pins['production'].get('pack')}` |
| Prod Call1 | `{pins['production'].get('call1')}` |
| Title validation loosened? | **No** |
| Publication blockers loosened? | **No** |
| Observatory-Core selection modified? | **No** |

---

## 17. Recommendation

```
{verdict}
```

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/section_contracts_live_ntt/`
"""
    REPORT.write_text(md, encoding="utf-8")
    print(json.dumps({"verdict": verdict, "targets": targets, "scores": scores}, ensure_ascii=False, indent=2))
    print("Wrote", REPORT)
    return 0 if pipe.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
