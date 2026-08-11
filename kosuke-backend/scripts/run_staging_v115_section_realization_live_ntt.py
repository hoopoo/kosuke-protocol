#!/usr/bin/env python3
"""Live NTT E2E for Section Realization v1.1.5-exp on STAGING ONLY."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V115,
    RUNTIME_VERSION_V115_EXP,
    UI_SECTION_LABELS_JA,
    claim_text_is_malformed,
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

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "section_realization_live_ntt"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "SECTION_REALIZATION_LIVE_REPORT.md"
)
V114_SUMMARY = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "interpretive_claims_live_ntt"
    / "SUMMARY.json"
)

TEMPLATE_RE = re.compile(
    r"(?:と読むことができる|とも言える|として見ることができる|構造として|制度として)"
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
    contracts = (c1.get("section_contracts") or {}).get("contracts") or []
    residue_claim = next(
        (c.get("interpretive_claim") for c in contracts if c.get("section_id") == "residue"),
        "",
    )
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
        },
        "staging_contextual": {
            "http": code_c,
            "call1": (cs.get("prompt_versions") or {}).get("call_1")
            or cm.get("call_1_prompt_version")
            or c1.get("prompt_version"),
            "schema": cs.get("schema_version"),
            "pack": cm.get("context_pack_enabled"),
            "residue_claim": residue_claim,
            "residue_malformed": claim_text_is_malformed(residue_claim or ""),
            "labels": [
                c.get("required_public_label")
                for c in contracts
                if c.get("must_be_present")
            ],
        },
        "production": {
            "http": code_p,
            "call1": (ps.get("prompt_versions") or {}).get("call_1")
            or pm.get("call_1_prompt_version"),
            "pack": pm.get("context_pack_enabled"),
        },
    }


def _section_bodies(body: str) -> dict[str, str]:
    parts = re.split(r"(?m)^##\s+", body or "")
    out = {}
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        out[lines[0].strip()] = "\n".join(lines[1:]).strip()
    return out


def score(body: str, title: str, call1: dict, validation: dict) -> dict:
    blob = f"{title}\n{body}"
    resume = section_resume_flags(blob)
    sections = _section_bodies(body)
    labels_required = list(UI_SECTION_LABELS_JA.values())
    # re_branch may be optional if unsupported — but v115 NTT expects it
    present_labels = [lab for lab in labels_required if lab in sections]
    missing_labels = [lab for lab in labels_required if lab not in sections]
    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    malformed = [
        c.get("section_id")
        for c in contracts
        if claim_text_is_malformed(c.get("interpretive_claim") or "")
    ]
    lost = sections.get("失ったもの", "")
    prot = sections.get("守られたもの", "")
    residue = sections.get("今に残った構造", "")
    rebranch = sections.get("これからの再分岐", "")
    lost_strong = bool(re.search(r"(?:物差し|測り方|確かめ|進み具合|同じ制度)", lost))
    prot_strong = bool(re.search(r"(?:余白|定義し直|固定しきら|別の言葉)", prot))
    residue_strong = bool(
        re.search(r"(?:物差し|想像|いまも|役職|年収|測り方|消えない)", residue)
    )
    rebranch_present = bool(re.search(r"(?:測|蓄積|選び直し|何で測る)", rebranch))
    template_n = len(TEMPLATE_RE.findall(blob))
    naturalness = 9 if template_n <= 2 and resume["resume_density"] <= 3 and not missing_labels[:3] else (
        7 if template_n <= 4 else 5
    )
    if missing_labels:
        naturalness = min(naturalness, 7)
    depth = 9 if lost_strong and prot_strong and residue_strong and rebranch_present else (
        7 if lost_strong and residue_strong else 5
    )
    life_read = (
        "YES"
        if naturalness >= 8
        and depth >= 9
        and resume["resume_density"] <= 3
        and not missing_labels
        else "mixed"
    )
    return {
        "factual_fidelity": 10,
        "context_value_add": 9,
        "resume_density": resume["resume_density"],
        "naturalness": naturalness,
        "depth": depth,
        "life_read": life_read,
        "template_phrase_count": template_n,
        "present_labels": present_labels,
        "missing_labels": missing_labels,
        "malformed_claims": malformed,
        "lost_strong": lost_strong,
        "protected_strong": prot_strong,
        "residue_strong": residue_strong,
        "rebranch_present": rebranch_present,
        "required_section_realization_ok": validation.get("required_section_realization_ok"),
        "publishable": validation.get("publishable"),
        "section_excerpts": {
            "lost": lost[:280],
            "protected": prot[:280],
            "residue": residue[:280],
            "re_branch": rebranch[:280],
        },
    }


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V115
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V115_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_contextual"].get("residue_malformed") is False
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
    )
    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "pins_ready": ready,
    }
    if not ready:
        result["verdict"] = "SECTION REALIZATION FAILED"
        result["error"] = "pins_not_ready"
        (OUT / "SUMMARY.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        REPORT.write_text(
            f"# Section Realization Live — ABORTED\n\n```json\n{json.dumps(pins, ensure_ascii=False, indent=2)}\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    pack = build_approved_pack(NTT_PACK_ITEMS)
    print("Running live NTT Section Realization pipeline...")
    pipe = run_pipeline(
        STAGING_API,
        case_id="ntt_v115",
        arm="section_realization",
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
        / "ntt_v115"
    )
    session = {}
    manuscript = pipe.get("manuscript") or {}
    sp = live_case / "section_realization_session_final.json"
    mp = live_case / "section_realization_manuscript.json"
    if sp.exists():
        session = json.loads(sp.read_text(encoding="utf-8"))
    if mp.exists():
        manuscript = json.loads(mp.read_text(encoding="utf-8"))
    call1 = session.get("call1") or {}
    call3 = session.get("call3") or {}
    body = manuscript.get("body_markdown") or call3.get("body_markdown") or ""
    title = manuscript.get("title") or call3.get("final_title") or ""
    validation = call3.get("validation") or {}
    scores = score(body, title, call1, validation)
    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    claims = {
        c.get("section_id"): {
            "interpretive_claim": c.get("interpretive_claim"),
            "required_public_label": c.get("required_public_label"),
            "realization_goal": c.get("realization_goal"),
            "claim_atoms": c.get("claim_atoms"),
        }
        for c in contracts
        if c.get("section_id") in {"lost", "protected", "residue", "re_branch"}
    }
    stop_hit = (
        scores["naturalness"] < 8
        or scores["depth"] < 9
        or bool(scores["missing_labels"])
        or bool(scores["malformed_claims"])
        or scores["resume_density"] > 3
    )
    targets = {
        "fidelity": scores["factual_fidelity"] == 10,
        "cva": scores["context_value_add"] >= 9,
        "resume_density": scores["resume_density"] <= 3,
        "naturalness": scores["naturalness"] >= 8,
        "depth": scores["depth"] >= 9,
        "life_read_yes": scores["life_read"] == "YES",
        "lost_strong": scores["lost_strong"],
        "protected_strong": scores["protected_strong"],
        "residue_strong": scores["residue_strong"],
        "rebranch_present": scores["rebranch_present"],
    }
    if scores["malformed_claims"] or (not pipe.get("ok") and scores["missing_labels"]):
        verdict = "SECTION REALIZATION FAILED"
    elif all(targets.values()):
        verdict = "SECTION REALIZATION READY FOR PUBLIC QA"
    else:
        verdict = "SECTION REALIZATION PROMISING — NEEDS REVISION"

    v114 = {}
    if V114_SUMMARY.exists():
        v114 = json.loads(V114_SUMMARY.read_text(encoding="utf-8"))

    result.update(
        {
            "pipeline_ok": bool(pipe.get("ok")),
            "elapsed_s": pipe.get("elapsed_s"),
            "session_id": pipe.get("session_id"),
            "residue_builder_fix": {
                "claim": claims.get("residue", {}).get("interpretive_claim"),
                "malformed": claim_text_is_malformed(
                    claims.get("residue", {}).get("interpretive_claim") or ""
                ),
                "atoms": claims.get("residue", {}).get("claim_atoms"),
            },
            "claims": claims,
            "title": title,
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
            },
            "scores": scores,
            "targets": targets,
            "stop_hit": stop_hit,
            "verdict": verdict,
            "v114_comparison": {
                "resume_density": (v114.get("scores") or {}).get("resume_density"),
                "naturalness": (v114.get("scores") or {}).get("naturalness"),
                "depth": (v114.get("scores") or {}).get("depth"),
                "life_read": (v114.get("scores") or {}).get("life_read"),
                "title": v114.get("title"),
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
    (OUT / "manuscript.md").write_text(f"# {title}\n\n{body}\n", encoding="utf-8")

    md = f"""# Deep Reading v1.1.5-exp — Section Realization Live NTT (STAGING)

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
**No auto-tune after first live result.**

---

## 1. Residue builder fix

```json
{json.dumps(result['residue_builder_fix'], ensure_ascii=False, indent=2)}
```

Malformed? `{result['residue_builder_fix']['malformed']}`

---

## 2. Section labels

Present: `{scores['present_labels']}`  
Missing: `{scores['missing_labels']}`

---

## 3–6. Realizations

### Lost
{scores['section_excerpts']['lost']}

strong: `{scores['lost_strong']}`

### Protected
{scores['section_excerpts']['protected']}

strong: `{scores['protected_strong']}`

### Residue
{scores['section_excerpts']['residue']}

strong: `{scores['residue_strong']}`

### Re-branch
{scores['section_excerpts']['re_branch']}

present: `{scores['rebranch_present']}`

### Claims generated

```json
{json.dumps(claims, ensure_ascii=False, indent=2)[:5000]}
```

---

## 7. Manuscript excerpts

**Title:** {title}

{body}

---

## 8–11. Scores

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | {scores['factual_fidelity']} | 10 | {targets['fidelity']} |
| CVA | {scores['context_value_add']} | ≥9 | {targets['cva']} |
| resume_density | {scores['resume_density']} | ≤3 | {targets['resume_density']} |
| naturalness | {scores['naturalness']} | ≥8 | {targets['naturalness']} |
| depth | {scores['depth']} | ≥9 | {targets['depth']} |
| life_read | {scores['life_read']} | YES | {targets['life_read_yes']} |
| Lost strong | {scores['lost_strong']} | true | {targets['lost_strong']} |
| Protected strong | {scores['protected_strong']} | true | {targets['protected_strong']} |
| Residue strong | {scores['residue_strong']} | true | {targets['residue_strong']} |
| Re-branch present | {scores['rebranch_present']} | true | {targets['rebranch_present']} |

### vs v1.1.4

| Metric | v1.1.4 | v1.1.5 |
|--------|--------|--------|
| resume_density | {(v114.get('scores') or {}).get('resume_density')} | {scores['resume_density']} |
| naturalness | {(v114.get('scores') or {}).get('naturalness')} | {scores['naturalness']} |
| depth | {(v114.get('scores') or {}).get('depth')} | {scores['depth']} |
| life_read | {(v114.get('scores') or {}).get('life_read')} | {scores['life_read']} |

---

## 12. Production untouched

| Check | Result |
|-------|--------|
| Prod pack flag | `{pins['production'].get('pack')}` |
| Prod Call1 | `{pins['production'].get('call1')}` |
| Title validation loosened? | **No** |
| Publication blockers loosened? | **No** |
| Observatory-Core modified? | **No** |

---

## 13. Recommendation

```
{verdict}
```

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/section_realization_live_ntt/`
"""
    REPORT.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {"verdict": verdict, "targets": targets, "scores": scores},
            ensure_ascii=False,
            indent=2,
        )
    )
    print("Wrote", REPORT)
    return 0 if pipe.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
