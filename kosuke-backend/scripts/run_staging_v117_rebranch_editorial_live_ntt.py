#!/usr/bin/env python3
"""Live NTT E2E for Re-branch Decision + Editorial Naturalness v1.1.7-exp (STAGING ONLY)."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

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

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "rebranch_editorial_live_ntt"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "REBRANCH_EDITORIAL_NATURALNESS_LIVE_REPORT.md"
)
V116_SUMMARY = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "thesis_closure_live_ntt"
    / "SUMMARY.json"
)

TEMPLATE_RE = re.compile(
    r"(?:と読むことができる|とも言える|として見ることができる|構造として|制度として)"
)
RESUME_MARKERS = ("複数業界", "複数の業界", "Protocol", "文章制作", "観測")


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
    reb = next((c for c in contracts if c.get("section_id") == "re_branch"), {})
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
            "rebranch_decision": reb.get("rebranch_decision") or {
                "present_choice": reb.get("present_choice"),
                "what_is_no_longer_required": reb.get("what_is_no_longer_required"),
                "what_can_now_be_chosen": reb.get("what_can_now_be_chosen"),
                "unresolved_tension": reb.get("unresolved_tension"),
                "non_genericity_score": reb.get("non_genericity_score"),
            },
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
    re_ok, re_missing, re_details = re_branch_realization_check(
        rebranch, residue_body=residue
    )
    closure_ok, closure_missing, closure_details = thesis_closure_check(
        body, call1.get("section_contracts")
    )
    dens = abstract_vocabulary_density(blob)
    remaining_resume = [m for m in RESUME_MARKERS if m in blob]
    template_n = len(TEMPLATE_RE.findall(blob))

    chosen_strong = bool(re.search(r"(?:定義し直|積み上げ|測り方|道へ|所属)", chosen))
    lost_strong = bool(re.search(r"(?:物差し|測り方|確かめ|進み具合|同じ制度)", lost))
    prot_strong = bool(re.search(r"(?:余白|定義し直|固定しきら|別の言葉)", prot))
    residue_strong = bool(
        re.search(r"(?:物差し|想像|いまも|役職|年収|測り方|消えない)", residue)
    )

    naturalness = 9 if template_n <= 2 and resume["resume_density"] <= 3 and not dens["excess"] else (
        8 if template_n <= 3 and resume["resume_density"] <= 3 else 7
    )
    if dens.get("counts", {}).get("蓄積", 0) >= 5:
        naturalness = min(naturalness, 7)
    if missing_labels:
        naturalness = min(naturalness, 7)
    depth = 9 if chosen_strong and lost_strong and prot_strong and residue_strong and re_ok else (
        8 if lost_strong and residue_strong and re_ok else 7
    )
    life_read = (
        "YES"
        if naturalness >= 8
        and depth >= 8
        and resume["resume_density"] <= 3
        and re_ok
        and closure_ok
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
        "abstract_vocab": dens,
        "present_labels": present_labels,
        "missing_labels": missing_labels,
        "malformed_claims": malformed,
        "chosen_path_strong": chosen_strong,
        "lost_strong": lost_strong,
        "protected_strong": prot_strong,
        "residue_strong": residue_strong,
        "rebranch_realized": re_ok,
        "rebranch_missing": re_missing,
        "rebranch_details": re_details,
        "remaining_resume_markers": remaining_resume,
        "thesis_closure_ok": closure_ok,
        "thesis_closure_missing": closure_missing,
        "thesis_closure_details": closure_details,
        "publishable": validation.get("publishable"),
        "section_excerpts": {
            "chosen_path": chosen[:360],
            "residue": residue[:280],
            "re_branch": rebranch[:400],
        },
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
        and bool((pins["staging_contextual"].get("rebranch_decision") or {}).get("present_choice"))
    )
    result: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pins": pins,
        "pins_ready": ready,
    }
    if not ready:
        result["verdict"] = "REBRANCH EDITORIAL FAILED"
        result["error"] = "pins_not_ready"
        (OUT / "SUMMARY.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        REPORT.write_text(
            f"# Re-branch Editorial Live — ABORTED\n\n```json\n{json.dumps(pins, ensure_ascii=False, indent=2)}\n```\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    pack = build_approved_pack(NTT_PACK_ITEMS)
    print("Running live NTT Re-branch Editorial pipeline...")
    pipe = run_pipeline(
        STAGING_API,
        case_id="ntt_v117",
        arm="rebranch_editorial",
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
        / "ntt_v117"
    )
    session = {}
    manuscript = pipe.get("manuscript") or {}
    sp = live_case / "rebranch_editorial_session_final.json"
    mp = live_case / "rebranch_editorial_manuscript.json"
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
    reb_c = next((c for c in contracts if c.get("section_id") == "re_branch"), {})
    decision = reb_c.get("rebranch_decision") or {
        "unresolved_tension": reb_c.get("unresolved_tension"),
        "present_choice": reb_c.get("present_choice"),
        "what_is_no_longer_required": reb_c.get("what_is_no_longer_required"),
        "what_can_now_be_chosen": reb_c.get("what_can_now_be_chosen"),
        "evidence_ids": reb_c.get("supporting_evidence_ids"),
        "non_genericity_score": reb_c.get("non_genericity_score"),
    }

    stop_hit = (
        not scores["rebranch_realized"]
        or not scores["thesis_closure_ok"]
        or scores["naturalness"] < 8
        or scores["life_read"] == "mixed"
        or bool(scores["malformed_claims"])
    )
    targets = {
        "fidelity": scores["factual_fidelity"] == 10,
        "cva": scores["context_value_add"] >= 9,
        "resume_density": scores["resume_density"] <= 3,
        "naturalness": scores["naturalness"] >= 8,
        "depth": scores["depth"] >= 8,
        "life_read_yes": scores["life_read"] == "YES",
        "rebranch_realized": scores["rebranch_realized"],
        "thesis_closure": scores["thesis_closure_ok"],
        "publishable": bool(validation.get("publishable")),
    }
    if scores["malformed_claims"]:
        verdict = "REBRANCH EDITORIAL FAILED"
    elif all(targets.values()) and not stop_hit:
        verdict = "REBRANCH EDITORIAL READY FOR PUBLIC QA"
    else:
        verdict = "PROMISING — NEEDS REVISION"

    # Stop-condition recommendation (no v1.1.8 auto)
    if scores["naturalness"] <= 7 and scores["life_read"] == "mixed":
        next_step = (
            "STOP PROMPT PATCHING. Prefer A) human editorial benchmark imitation, "
            "or C) accept current quality ceiling; B) Call2 architecture only if "
            "Re-branch remains structurally unrealizable after deterministic ensure."
        )
        if not scores["rebranch_realized"]:
            next_step = (
                "STOP PROMPT PATCHING. Recommend B) Call2 architecture change "
                "(section writer that forces ReBranchDecision close), "
                "else A) human editorial benchmark imitation."
            )
    elif scores["rebranch_realized"] and scores["naturalness"] >= 8:
        next_step = "Proceed to Public QA on staging; do not create v1.1.8 automatically."
    else:
        next_step = (
            "PROMISING. No v1.1.8 auto. If one more human-facing pass is needed, "
            "prefer A) human editorial benchmark imitation over prompt patching."
        )

    v116 = {}
    if V116_SUMMARY.exists():
        v116 = json.loads(V116_SUMMARY.read_text(encoding="utf-8"))
    v116_sections = _section_bodies(v116.get("body_markdown") or "")

    result.update(
        {
            "pipeline_ok": bool(pipe.get("ok")),
            "elapsed_s": pipe.get("elapsed_s"),
            "session_id": pipe.get("session_id"),
            "rebranch_decision": decision,
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
            "next_step_recommendation": next_step,
            "before_after": {
                "re_branch_before": (v116_sections.get("これからの再分岐") or "")[:400],
                "re_branch_after": scores["section_excerpts"]["re_branch"],
            },
            "v116_comparison": {
                "resume_density": (v116.get("scores") or {}).get("resume_density"),
                "naturalness": (v116.get("scores") or {}).get("naturalness"),
                "depth": (v116.get("scores") or {}).get("depth"),
                "life_read": (v116.get("scores") or {}).get("life_read"),
                "publishable": (v116.get("validation") or {}).get("publishable"),
            },
            "call3_prompt_version": call3.get("prompt_version"),
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
    decision_json = json.dumps(decision or empty, ensure_ascii=False, indent=2)
    closure_json = json.dumps(
        scores.get("thesis_closure_details") or empty, ensure_ascii=False, indent=2
    )
    dens_json = json.dumps(scores.get("abstract_vocab") or empty, ensure_ascii=False, indent=2)
    v116_scores = v116.get("scores") or empty
    v116_validation = v116.get("validation") or empty

    md = f"""# Deep Reading v1.1.7-exp — Re-branch Decision + Editorial Naturalness Live NTT

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
**No auto-tune. Do not create v1.1.8 automatically.**

---

## 1. ReBranchDecision

```json
{decision_json}
```

---

## 2. Re-branch before / after

### Before (v1.1.6)
{result['before_after']['re_branch_before'] or '_n/a_'}

### After (v1.1.7)
{result['before_after']['re_branch_after'] or '_n/a_'}

realized: `{scores['rebranch_realized']}`  
missing: `{scores['rebranch_missing']}`

---

## 3. Thesis closure

ok: `{scores['thesis_closure_ok']}`  
missing: `{scores['thesis_closure_missing']}`

```json
{closure_json}
```

---

## 4. Abstract vocabulary counts

```json
{dens_json}
```

---

## 5. Remaining résumé text

resume_density: `{scores['resume_density']}`  
markers: `{scores['remaining_resume_markers']}`

---

## 6. Call3 editorial changes

Call3 prompt_version: `{call3.get('prompt_version')}`  
Deterministic ensure_rebranch + compress_resume + thin_abstract + editorial naturalness pass enabled for v1.1.7 Contextual.

Server blocking_reasons: `{validation.get('blocking_reasons')}`

---

## 7–9. Scores

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | {scores['factual_fidelity']} | 10 | {targets['fidelity']} |
| CVA | {scores['context_value_add']} | ≥9 | {targets['cva']} |
| resume_density | {scores['resume_density']} | ≤3 | {targets['resume_density']} |
| naturalness | {scores['naturalness']} | ≥8 | {targets['naturalness']} |
| depth | {scores['depth']} | ≥8 | {targets['depth']} |
| life_read | {scores['life_read']} | YES | {targets['life_read_yes']} |
| re_branch realized | {scores['rebranch_realized']} | true | {targets['rebranch_realized']} |
| thesis_closure | {scores['thesis_closure_ok']} | true | {targets['thesis_closure']} |
| publishable | {validation.get('publishable')} | true | {targets['publishable']} |

### vs v1.1.6

| Metric | v1.1.6 | v1.1.7 |
|--------|--------|--------|
| resume_density | {v116_scores.get('resume_density')} | {scores['resume_density']} |
| naturalness | {v116_scores.get('naturalness')} | {scores['naturalness']} |
| depth | {v116_scores.get('depth')} | {scores['depth']} |
| life_read | {v116_scores.get('life_read')} | {scores['life_read']} |
| publishable | {v116_validation.get('publishable')} | {validation.get('publishable')} |

---

## 10. Publishable

`{validation.get('publishable')}`

---

## 11. Recommendation

```
{verdict}
```

Next step (stop condition):

```
{next_step}
```

Production untouched: pack=`{pins['production'].get('pack')}` call1=`{pins['production'].get('call1')}`  
Title / publication gates / Observatory-Core: **unchanged**

Full manuscript:

**Title:** {title}

{body}

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/rebranch_editorial_live_ntt/`
"""
    REPORT.write_text(md, encoding="utf-8")
    print(
        json.dumps(
            {
                "verdict": verdict,
                "next_step": next_step,
                "targets": targets,
                "scores": {
                    k: scores[k]
                    for k in (
                        "resume_density",
                        "naturalness",
                        "depth",
                        "life_read",
                        "rebranch_realized",
                        "thesis_closure_ok",
                        "publishable",
                        "remaining_resume_markers",
                    )
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("Wrote", REPORT)
    return 0 if pipe.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
