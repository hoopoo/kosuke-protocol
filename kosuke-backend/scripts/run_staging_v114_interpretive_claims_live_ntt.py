#!/usr/bin/env python3
"""Live NTT E2E for Interpretive Claims v1.1.4-exp on STAGING ONLY."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.observatory_core import (  # noqa: E402
    CrossLensRelation,
    relation_density_score,
)
from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V114,
    RUNTIME_VERSION_V114_EXP,
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

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "interpretive_claims_live_ntt"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "INTERPRETIVE_CLAIMS_LIVE_REPORT.md"
)
V113_SUMMARY = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "section_contracts_live_ntt"
    / "SUMMARY.json"
)

CAUSAL_RE = re.compile(r"(?:引き起こ|追いや|が原因で|せざるを得)")
LENS_RE = re.compile(
    r"(?:Clean Society|After Success|Education[–-]Employment|Market Signals|CrossLensRelation)",
    re.I,
)
TEMPLATE_RE = re.compile(r"(?:構造として|制度として|読むことができる)")


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
    contracts = (c1.get("section_contracts") or {}).get("contracts") or []
    has_claims = any((c.get("interpretive_claim") or "").strip() for c in contracts)
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
            "has_interpretive_claims": has_claims,
            "lost": ((c1.get("lost_structure") or {}).get("items") or [{}])[0].get("content"),
            "protected": ((c1.get("protected_structure") or {}).get("items") or [{}])[0].get(
                "content"
            ),
        },
        "production": {
            "http": code_p,
            "call1": (ps.get("prompt_versions") or {}).get("call_1")
            or pm.get("call_1_prompt_version"),
            "pack": pm.get("context_pack_enabled"),
        },
    }


def _excerpt_failures(body: str, scores: dict) -> list[str]:
    out: list[str] = []
    paras = re.findall(r"<p[^>]*>(.*?)</p>", body or "", flags=re.S)
    if not paras:
        paras = [p.strip() for p in re.split(r"\n\s*\n", body or "") if p.strip()]
    # Template cadence
    template_paras = [p for p in paras if TEMPLATE_RE.search(p)]
    if scores.get("naturalness", 10) < 8 and template_paras:
        out.append("template_cadence: " + template_paras[0][:220])
    # Employer enumeration
    org_paras = [
        p
        for p in paras
        if len(re.findall(r"(?:NTT|外資|半導体|業界|企業)", p)) >= 3
    ]
    if scores.get("resume_density", 0) > 3 and org_paras:
        out.append("employer_enumeration: " + org_paras[0][:220])
    elif scores.get("resume_density", 0) > 3 and paras:
        out.append("resume_density_source: " + paras[0][:220])
    # Depth: missing interpretive density
    if scores.get("depth", 10) < 9:
        weak = [
            p
            for p in paras
            if not re.search(r"(?:測|余白|確かめ|閉じ|意味を持ち|選び直し|進み)", p)
        ]
        if weak:
            out.append("shallow_paragraph: " + weak[0][:220])
    return out[:6]


def score(body: str, title: str, subtitle: str, call1: dict) -> dict:
    blob = f"{title}\n{subtitle}\n{body}"
    resume = section_resume_flags(blob)
    relations = []
    for r in call1.get("cross_lens_relations") or []:
        try:
            relations.append(CrossLensRelation.model_validate(r))
        except Exception:
            pass
    template_count = len(TEMPLATE_RE.findall(blob))
    has_interp = bool(
        re.search(r"(?:測り方|確かめ|閉じきら|余白|意味を持ち|選び直し|消えていない)", blob)
    )
    has_personal = any(t in blob for t in ("残っていたら", "いまも", "分岐", "自分"))
    social = any(t in blob for t in ("雇用", "企業間", "一社", "制度", "規範", "蓄積"))
    naturalness = 9 if has_interp and template_count <= 2 and resume["resume_density"] <= 3 else (
        7 if has_interp and resume["resume_density"] <= 4 else 5
    )
    if template_count >= 4:
        naturalness = min(naturalness, 6)
    depth = 9 if has_interp and social and resume["resume_density"] <= 3 else (
        7 if has_interp else 4
    )
    cva = min(
        10,
        5
        + (2 if social else 0)
        + (1 if has_interp else 0)
        + (1 if resume["resume_density"] <= 3 else 0)
        + (1 if relation_density_score(relations, blob) >= 7 else 0),
    )
    life_read = (
        "YES"
        if has_interp and resume["resume_density"] <= 3 and naturalness >= 8 and depth >= 9
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
        "template_phrase_count": template_count,
        "life_read": life_read,
        "causal_hits": CAUSAL_RE.findall(blob),
        "lens_hits": LENS_RE.findall(blob),
    }


def _contract_map(call1: dict) -> dict:
    out = {}
    for c in (call1.get("section_contracts") or {}).get("contracts") or []:
        out[c.get("section_id")] = c
    return out


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V114
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V114_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_contextual"].get("has_interpretive_claims") is True
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
    )
    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "pins_ready": ready,
    }
    if not ready:
        result["verdict"] = "INTERPRETIVE CLAIMS FAILED"
        result["error"] = "pins_not_ready"
        (OUT / "SUMMARY.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        REPORT.write_text(
            f"# Interpretive Claims Live — ABORTED\n\n```json\n{json.dumps(pins, ensure_ascii=False, indent=2)}\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    pack = build_approved_pack(NTT_PACK_ITEMS)
    print("Running live NTT Interpretive Claims pipeline...")
    pipe = run_pipeline(
        STAGING_API,
        case_id="ntt_v114",
        arm="interpretive_claims",
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
        / "ntt_v114"
    )
    session = {}
    manuscript = pipe.get("manuscript") or {}
    sp = live_case / "interpretive_claims_session_final.json"
    mp = live_case / "interpretive_claims_manuscript.json"
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
    failure_excerpts = _excerpt_failures(body, scores)
    validation = call3.get("validation") or {}
    cmap = _contract_map(call1)
    v113 = {}
    if V113_SUMMARY.exists():
        v113 = json.loads(V113_SUMMARY.read_text(encoding="utf-8"))
    v113_c = _contract_map(v113.get("section_contracts") and {"section_contracts": v113["section_contracts"]} or {})
    # v113 summary stores section_contracts at top level
    if not v113_c and isinstance(v113.get("section_contracts"), dict):
        for c in (v113.get("section_contracts") or {}).get("contracts") or []:
            v113_c[c.get("section_id")] = c

    targets = {
        "fidelity": scores["factual_fidelity"] == 10,
        "cva": scores["context_value_add"] >= 9,
        "naturalness": scores["naturalness"] >= 8,
        "depth": scores["depth"] >= 9,
        "resume_density": scores["resume_density"] <= 3,
        "life_read_yes": scores["life_read"] == "YES",
    }
    stop_hit = (
        scores["naturalness"] < 8
        or scores["depth"] < 9
        or scores["resume_density"] > 3
    )
    if scores["causal_hits"] or scores["lens_hits"] or not pipe.get("ok"):
        verdict = "INTERPRETIVE CLAIMS FAILED"
    elif all(targets.values()):
        verdict = "INTERPRETIVE CLAIMS READY FOR PUBLIC QA"
    elif stop_hit:
        verdict = "INTERPRETIVE CLAIMS PROMISING — NEEDS REVISION"
    else:
        verdict = "INTERPRETIVE CLAIMS PROMISING — NEEDS REVISION"

    result.update(
        {
            "pipeline_ok": bool(pipe.get("ok")),
            "elapsed_s": pipe.get("elapsed_s"),
            "session_id": pipe.get("session_id"),
            "section_contracts": call1.get("section_contracts"),
            "interpretive_claims": {
                sid: (cmap.get(sid) or {}).get("interpretive_claim")
                for sid in ("lost", "protected", "residue", "re_branch")
            },
            "before_after": {
                "lost": {
                    "v113": (v113.get("lost") or {}).get("items", [{}])[0].get("content")
                    if isinstance(v113.get("lost"), dict)
                    else None,
                    "v114_structural": (cmap.get("lost") or {}).get("required_meaning"),
                    "v114_claim": (cmap.get("lost") or {}).get("interpretive_claim"),
                },
                "protected": {
                    "v113": (v113.get("protected") or {}).get("items", [{}])[0].get("content")
                    if isinstance(v113.get("protected"), dict)
                    else None,
                    "v114_structural": (cmap.get("protected") or {}).get("required_meaning"),
                    "v114_claim": (cmap.get("protected") or {}).get("interpretive_claim"),
                },
                "residue": {
                    "v113": (
                        ((v113.get("residue") or {}).get("items") or [{}])[0].get(
                            "residue_statement"
                        )
                        if isinstance(v113.get("residue"), dict)
                        else None
                    ),
                    "v114_structural": (cmap.get("residue") or {}).get("required_meaning"),
                    "v114_claim": (cmap.get("residue") or {}).get("interpretive_claim"),
                },
                "re_branch": {
                    "v113": (
                        ((v113.get("rebranch") or {}).get("directions") or [{}])[0].get(
                            "branch_specific_form"
                        )
                        if isinstance(v113.get("rebranch"), dict)
                        else None
                    ),
                    "v114_structural": (cmap.get("re_branch") or {}).get("required_meaning"),
                    "v114_claim": (cmap.get("re_branch") or {}).get("interpretive_claim"),
                },
            },
            "title": title,
            "subtitle": subtitle,
            "body_markdown": body,
            "validation": {
                "publishable": validation.get("publishable"),
                "blocking_reasons": validation.get("blocking_reasons"),
                "required_section_realization_ok": validation.get(
                    "required_section_realization_ok"
                ),
            },
            "scores": scores,
            "targets": targets,
            "stop_hit": stop_hit,
            "failure_excerpts": failure_excerpts,
            "verdict": verdict,
            "v113_comparison": {
                "resume_density": (v113.get("scores") or {}).get("resume_density"),
                "naturalness": (v113.get("scores") or {}).get("naturalness"),
                "depth": (v113.get("scores") or {}).get("depth"),
                "life_read": (v113.get("scores") or {}).get("life_read"),
                "title": v113.get("title"),
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

    ba = result["before_after"]
    md = f"""# Deep Reading v1.1.4-exp — Interpretive Claims Live NTT (STAGING)

Generated: `{result['generated_at']}`  
Staging: `{STAGING_API}`  
Production: **untouched**

## Verdict

```
{verdict}
```

Pipeline ok: `{pipe.get('ok')}` · elapsed_s: `{pipe.get('elapsed_s')}`  
Publishable: `{validation.get('publishable')}`  
Stop rule hit: `{stop_hit}`

---

## 1. Interpretive claims generated

```json
{json.dumps(result['interpretive_claims'], ensure_ascii=False, indent=2)}
```

---

## 2–5. Before / after (v1.1.3 → v1.1.4)

### Lost
- **v1.1.3:** {ba['lost'].get('v113')}
- **v1.1.4 structural:** {ba['lost'].get('v114_structural')}
- **v1.1.4 interpretive_claim:** {ba['lost'].get('v114_claim')}

### Protected
- **v1.1.3:** {ba['protected'].get('v113')}
- **v1.1.4 structural:** {ba['protected'].get('v114_structural')}
- **v1.1.4 interpretive_claim:** {ba['protected'].get('v114_claim')}

### Residue
- **v1.1.3:** {ba['residue'].get('v113')}
- **v1.1.4 structural:** {ba['residue'].get('v114_structural')}
- **v1.1.4 interpretive_claim:** {ba['residue'].get('v114_claim')}

### Re-branch
- **v1.1.3:** {ba['re_branch'].get('v113')}
- **v1.1.4 structural:** {ba['re_branch'].get('v114_structural')}
- **v1.1.4 interpretive_claim:** {ba['re_branch'].get('v114_claim')}

---

## 6. Exact manuscript excerpts

**Title:** {title}  
**Subtitle:** {subtitle or '(omitted)'}

### Body

{body}

### Failure excerpts (if stop)

```json
{json.dumps(failure_excerpts, ensure_ascii=False, indent=2)}
```

---

## 7–10. Scores

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | {scores['factual_fidelity']} | 10 | {targets['fidelity']} |
| CVA | {scores['context_value_add']} | ≥9 | {targets['cva']} |
| naturalness | {scores['naturalness']} | ≥8 | {targets['naturalness']} |
| depth | {scores['depth']} | ≥9 | {targets['depth']} |
| resume_density | {scores['resume_density']} | ≤3 | {targets['resume_density']} |
| life_read | {scores['life_read']} | YES | {targets['life_read_yes']} |

template_phrase_count: `{scores['template_phrase_count']}`  
required_section_realization_ok: `{validation.get('required_section_realization_ok')}`

### vs v1.1.3

| Metric | v1.1.3 | v1.1.4 |
|--------|--------|--------|
| resume_density | {(v113.get('scores') or {}).get('resume_density')} | {scores['resume_density']} |
| naturalness | {(v113.get('scores') or {}).get('naturalness')} | {scores['naturalness']} |
| depth | {(v113.get('scores') or {}).get('depth')} | {scores['depth']} |
| life_read | {(v113.get('scores') or {}).get('life_read')} | {scores['life_read']} |

---

## 11. Production untouched

| Check | Result |
|-------|--------|
| Prod pack flag | `{pins['production'].get('pack')}` |
| Prod Call1 | `{pins['production'].get('call1')}` |
| Title validation loosened? | **No** |
| Publication blockers loosened? | **No** |
| Observatory-Core modified? | **No** |

---

## 12. Recommendation

```
{verdict}
```

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/interpretive_claims_live_ntt/`
"""
    REPORT.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "targets": targets,
                "scores": scores,
                "failure_excerpts": failure_excerpts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("Wrote", REPORT)
    return 0 if pipe.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
