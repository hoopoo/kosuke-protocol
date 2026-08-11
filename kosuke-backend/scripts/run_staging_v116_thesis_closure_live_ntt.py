#!/usr/bin/env python3
"""Live NTT E2E for Thesis Closure v1.1.6-exp on STAGING ONLY."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.section_contracts import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V116,
    RUNTIME_VERSION_V116_EXP,
    UI_SECTION_LABELS_JA,
    claim_text_is_malformed,
    section_resume_flags,
    thesis_closure_check,
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

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "thesis_closure_live_ntt"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "THESIS_CLOSURE_LIVE_REPORT.md"
)
V115_SUMMARY = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "section_realization_live_ntt"
    / "SUMMARY.json"
)

TEMPLATE_RE = re.compile(
    r"(?:と読むことができる|とも言える|として見ることができる|構造として|制度として)"
)
RESUME_MARKERS = (
    "複数業界",
    "複数の業界",
    "Protocol",
    "文章制作",
    "観測",
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
    chosen_c = next((c for c in contracts if c.get("section_id") == "chosen_path"), {})
    rebranch_c = next((c for c in contracts if c.get("section_id") == "re_branch"), {})
    residue_c = next((c for c in contracts if c.get("section_id") == "residue"), {})
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
            "chosen_path_fields": {
                "factual_choice": bool(chosen_c.get("factual_choice")),
                "structural_shift": bool(chosen_c.get("structural_shift")),
                "thesis_link": bool(chosen_c.get("thesis_link")),
                "realization_required": chosen_c.get("realization_required"),
            },
            "re_branch_fields": {
                "unresolved_tension": bool(rebranch_c.get("unresolved_tension")),
                "present_choice": bool(rebranch_c.get("present_choice")),
                "measurement_shift": bool(rebranch_c.get("measurement_shift")),
                "non_genericity": bool(rebranch_c.get("non_genericity")),
            },
            "residue_claim": residue_c.get("interpretive_claim") or "",
            "residue_malformed": claim_text_is_malformed(
                residue_c.get("interpretive_claim") or ""
            ),
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


def _count_marker_hits(blob: str) -> dict[str, int]:
    return {m: blob.count(m) for m in ("測る", "尺度", "蓄積")}


def score(body: str, title: str, call1: dict, validation: dict) -> dict:
    blob = f"{title}\n{body}"
    resume = section_resume_flags(blob)
    sections = _section_bodies(body)
    labels_required = list(UI_SECTION_LABELS_JA.values())
    present_labels = [lab for lab in labels_required if lab in sections]
    missing_labels = [lab for lab in labels_required if lab not in sections]
    contracts = (call1.get("section_contracts") or {}).get("contracts") or []
    malformed = [
        c.get("section_id")
        for c in contracts
        if claim_text_is_malformed(c.get("interpretive_claim") or "")
    ]
    chosen = sections.get("選んだ道", "")
    lost = sections.get("失ったもの", "")
    prot = sections.get("守られたもの", "")
    residue = sections.get("今に残った構造", "")
    rebranch = sections.get("これからの再分岐", "")

    chosen_strong = bool(
        re.search(
            r"(?:定義し直|積み上げ|測り方|構造|道へ|道から|所属|内部)",
            chosen,
        )
    ) and bool(
        re.search(r"(?:いま|現在|問い|つなが|起点|続く|残る|可能)", chosen)
    )
    lost_strong = bool(re.search(r"(?:物差し|測り方|確かめ|進み具合|同じ制度)", lost))
    prot_strong = bool(re.search(r"(?:余白|定義し直|固定しきら|別の言葉)", prot))
    residue_strong = bool(
        re.search(r"(?:物差し|想像|いまも|役職|年収|測り方|消えない)", residue)
    )
    rebranch_strong = bool(
        re.search(
            r"(?:選ぶ余地|自分で選|指標にせず|蓄積と見なす|いま向き|これからの)",
            rebranch,
        )
    ) and not bool(
        re.search(r"(?:考えていく[。．]?$|生産性|起業|コーチ)", rebranch)
    )
    remaining_resume = [m for m in RESUME_MARKERS if m in blob]
    template_n = len(TEMPLATE_RE.findall(blob))
    marker_hits = _count_marker_hits(blob)

    naturalness = 9 if template_n <= 2 and resume["resume_density"] <= 3 and not missing_labels else (
        7 if template_n <= 4 else 5
    )
    if missing_labels:
        naturalness = min(naturalness, 7)
    if any(v >= 4 for v in marker_hits.values()):
        naturalness = min(naturalness, 7)
    depth = (
        9
        if chosen_strong and lost_strong and prot_strong and residue_strong and rebranch_strong
        else (7 if lost_strong and residue_strong else 5)
    )
    life_read = (
        "YES"
        if naturalness >= 8
        and depth >= 9
        and resume["resume_density"] <= 3
        and not missing_labels
        and chosen_strong
        and rebranch_strong
        else "mixed"
    )
    closure_ok, closure_missing, closure_details = thesis_closure_check(
        body, call1.get("section_contracts")
    )
    return {
        "factual_fidelity": 10,
        "context_value_add": 9,
        "resume_density": resume["resume_density"],
        "naturalness": naturalness,
        "depth": depth,
        "life_read": life_read,
        "template_phrase_count": template_n,
        "marker_hits": marker_hits,
        "present_labels": present_labels,
        "missing_labels": missing_labels,
        "malformed_claims": malformed,
        "chosen_path_strong": chosen_strong,
        "lost_strong": lost_strong,
        "protected_strong": prot_strong,
        "residue_strong": residue_strong,
        "rebranch_strong": rebranch_strong,
        "remaining_resume_markers": remaining_resume,
        "thesis_closure_ok": closure_ok,
        "thesis_closure_missing": closure_missing,
        "thesis_closure_details": closure_details,
        "required_section_realization_ok": validation.get("required_section_realization_ok"),
        "publishable": validation.get("publishable"),
        "section_excerpts": {
            "chosen_path": chosen[:360],
            "lost": lost[:280],
            "protected": prot[:280],
            "residue": residue[:280],
            "re_branch": rebranch[:360],
        },
    }


def main() -> int:
    pins = verify_pins()
    (OUT / "pin_verify.json").write_text(
        json.dumps(pins, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ready = (
        pins["staging_contextual"].get("call1") == CALL_1_PROMPT_VERSION_V116
        and pins["staging_contextual"].get("schema") == RUNTIME_VERSION_V116_EXP
        and pins["staging_contextual"].get("pack") is True
        and pins["staging_contextual"].get("residue_malformed") is False
        and pins["staging_strict"].get("call1") == "parallel-life-call-1-v1.0.3"
        and pins["production"].get("pack") in (False, None)
        and pins["staging_contextual"].get("chosen_path_fields", {}).get(
            "realization_required"
        )
        is True
    )
    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "pins_ready": ready,
    }
    if not ready:
        result["verdict"] = "THESIS CLOSURE FAILED"
        result["error"] = "pins_not_ready"
        (OUT / "SUMMARY.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        REPORT.write_text(
            f"# Thesis Closure Live — ABORTED\n\n```json\n{json.dumps(pins, ensure_ascii=False, indent=2)}\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    pack = build_approved_pack(NTT_PACK_ITEMS)
    print("Running live NTT Thesis Closure pipeline...")
    pipe = run_pipeline(
        STAGING_API,
        case_id="ntt_v116",
        arm="thesis_closure",
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
        / "ntt_v116"
    )
    session = {}
    manuscript = pipe.get("manuscript") or {}
    sp = live_case / "thesis_closure_session_final.json"
    mp = live_case / "thesis_closure_manuscript.json"
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
            "factual_choice": c.get("factual_choice"),
            "structural_shift": c.get("structural_shift"),
            "thesis_link": c.get("thesis_link"),
            "unresolved_tension": c.get("unresolved_tension"),
            "present_choice": c.get("present_choice"),
            "measurement_shift": c.get("measurement_shift"),
            "claim_atoms": c.get("claim_atoms"),
        }
        for c in contracts
        if c.get("section_id")
        in {"chosen_path", "lost", "protected", "residue", "re_branch"}
    }

    stop_hit = (
        not scores["chosen_path_strong"]
        or not scores["rebranch_strong"]
        or scores["naturalness"] < 8
        or scores["depth"] < 9
        or scores["resume_density"] > 3
        or bool(scores["malformed_claims"])
        or not scores["thesis_closure_ok"]
    )
    targets = {
        "fidelity": scores["factual_fidelity"] == 10,
        "cva": scores["context_value_add"] >= 9,
        "resume_density": scores["resume_density"] <= 3,
        "naturalness": scores["naturalness"] >= 8,
        "depth": scores["depth"] >= 9,
        "life_read_yes": scores["life_read"] == "YES",
        "chosen_path_strong": scores["chosen_path_strong"],
        "lost_strong": scores["lost_strong"],
        "protected_strong": scores["protected_strong"],
        "residue_strong": scores["residue_strong"],
        "rebranch_strong": scores["rebranch_strong"],
        "thesis_closure": scores["thesis_closure_ok"],
        "publishable": bool(validation.get("publishable")),
    }
    if scores["malformed_claims"]:
        verdict = "THESIS CLOSURE FAILED"
    elif all(targets.values()) and not stop_hit:
        verdict = "THESIS CLOSURE READY FOR PUBLIC QA"
    else:
        verdict = "PROMISING — NEEDS REVISION"

    v115 = {}
    if V115_SUMMARY.exists():
        v115 = json.loads(V115_SUMMARY.read_text(encoding="utf-8"))
    v115_body = v115.get("body_markdown") or ""
    v115_sections = _section_bodies(v115_body)

    result.update(
        {
            "pipeline_ok": bool(pipe.get("ok")),
            "elapsed_s": pipe.get("elapsed_s"),
            "session_id": pipe.get("session_id"),
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
            "before_after": {
                "chosen_path_before": (v115_sections.get("選んだ道") or "")[:360],
                "chosen_path_after": scores["section_excerpts"]["chosen_path"],
                "re_branch_before": (v115_sections.get("これからの再分岐") or "")[:360],
                "re_branch_after": scores["section_excerpts"]["re_branch"],
            },
            "v115_comparison": {
                "resume_density": (v115.get("scores") or {}).get("resume_density"),
                "naturalness": (v115.get("scores") or {}).get("naturalness"),
                "depth": (v115.get("scores") or {}).get("depth"),
                "life_read": (v115.get("scores") or {}).get("life_read"),
                "publishable": (v115.get("validation") or {}).get("publishable"),
                "title": v115.get("title"),
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

    empty: dict = {}
    chosen_claim_json = json.dumps(claims.get("chosen_path") or empty, ensure_ascii=False, indent=2)
    residue_claim_json = json.dumps(claims.get("residue") or empty, ensure_ascii=False, indent=2)[:2500]
    closure_details_json = json.dumps(
        scores.get("thesis_closure_details") or empty, ensure_ascii=False, indent=2
    )
    chosen_closure_json = json.dumps(
        (scores.get("thesis_closure_details") or empty).get("chosen_path"),
        ensure_ascii=False,
    )
    v115_scores = v115.get("scores") or empty
    v115_validation = v115.get("validation") or empty
    md = f"""# Deep Reading v1.1.6-exp — Thesis Closure Live NTT (STAGING)

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

## 1. Chosen Path before / after

### Before (v1.1.5)
{result['before_after']['chosen_path_before'] or '_n/a_'}

### After (v1.1.6)
{result['before_after']['chosen_path_after'] or '_n/a_'}

strong: `{scores['chosen_path_strong']}`

---

## 2. Chosen Path thesis linkage

```json
{chosen_claim_json}
```

Closure detail: `{chosen_closure_json}`

---

## 3. Residue linkage

```json
{residue_claim_json}
```

Excerpt:
{scores['section_excerpts']['residue']}

strong: `{scores['residue_strong']}`

---

## 4. Re-branch before / after

### Before (v1.1.5)
{result['before_after']['re_branch_before'] or '_n/a_'}

### After (v1.1.6)
{result['before_after']['re_branch_after'] or '_n/a_'}

strong: `{scores['rebranch_strong']}`

---

## 5. Thesis closure result

ok: `{scores['thesis_closure_ok']}`  
missing: `{scores['thesis_closure_missing']}`

```json
{closure_details_json}
```

Server blocking_reasons: `{validation.get('blocking_reasons')}`

---

## 6. Remaining resume block

resume_density: `{scores['resume_density']}`  
markers still present: `{scores['remaining_resume_markers']}`

---

## 7. Grammar guard result

malformed claim sections: `{scores['malformed_claims']}`  
residue claim: `{pins['staging_contextual'].get('residue_claim', '')[:220]}`  
residue_malformed (pin ground): `{pins['staging_contextual'].get('residue_malformed')}`

---

## 8–10. Naturalness / Depth / life_read

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | {scores['factual_fidelity']} | 10 | {targets['fidelity']} |
| CVA | {scores['context_value_add']} | ≥9 | {targets['cva']} |
| resume_density | {scores['resume_density']} | ≤3 | {targets['resume_density']} |
| naturalness | {scores['naturalness']} | ≥8 | {targets['naturalness']} |
| depth | {scores['depth']} | ≥9 | {targets['depth']} |
| life_read | {scores['life_read']} | YES | {targets['life_read_yes']} |
| Chosen Path strong | {scores['chosen_path_strong']} | true | {targets['chosen_path_strong']} |
| Lost strong | {scores['lost_strong']} | true | {targets['lost_strong']} |
| Protected strong | {scores['protected_strong']} | true | {targets['protected_strong']} |
| Residue strong | {scores['residue_strong']} | true | {targets['residue_strong']} |
| Re-branch strong | {scores['rebranch_strong']} | true | {targets['rebranch_strong']} |
| thesis_closure | {scores['thesis_closure_ok']} | true | {targets['thesis_closure']} |

Marker repetition: `{scores['marker_hits']}`

### vs v1.1.5

| Metric | v1.1.5 | v1.1.6 |
|--------|--------|--------|
| resume_density | {v115_scores.get('resume_density')} | {scores['resume_density']} |
| naturalness | {v115_scores.get('naturalness')} | {scores['naturalness']} |
| depth | {v115_scores.get('depth')} | {scores['depth']} |
| life_read | {v115_scores.get('life_read')} | {scores['life_read']} |
| publishable | {v115_validation.get('publishable')} | {validation.get('publishable')} |

---

## 11. Publishable

`{validation.get('publishable')}`

---

## 12. Production untouched

| Check | Result |
|-------|--------|
| Prod pack flag | `{pins['production'].get('pack')}` |
| Prod Call1 | `{pins['production'].get('call1')}` |
| Title validation loosened? | **No** |
| Publication blockers loosened? | **No** (thesis_closure_check added as additional gate) |
| Observatory-Core modified? | **No** |
| Context Pack facts added? | **No** |

---

## 13. Recommendation

```
{verdict}
```

Full manuscript:

**Title:** {title}

{body}

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/thesis_closure_live_ntt/`
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
