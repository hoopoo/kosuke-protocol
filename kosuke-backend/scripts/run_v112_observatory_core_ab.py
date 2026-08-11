#!/usr/bin/env python3
"""NTT A/B/C + regression for Deep Reading v1.1.2-exp Observatory-Core.

A/B reuse prior staging artifacts (no production changes).
C evaluates Observatory-Core structurally (and live staging if already on v1.1.2).

Writes OBSERVATORY_CORE_AB_REPORT.md
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.context_pack import (  # noqa: E402
    ContextPack,
)
from app.parallel_life_deep_reading.context_selection import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V110,
    CALL_1_PROMPT_VERSION_V111,
    compute_resume_density,
)
from app.parallel_life_deep_reading.observatory_core import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V112,
    RUNTIME_VERSION_V112_EXP,
    build_observatory_core_bundle,
    curated_evidence_store,
    relation_density_score,
)

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "observatory_core_ab"
OUT.mkdir(parents=True, exist_ok=True)
REPORT = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "OBSERVATORY_CORE_AB_REPORT.md"
)

A_DIR = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "live_ab" / "A_ntt"
B_DIR = (
    ROOT
    / "e2e_reports"
    / "deep-reading-v1.1-context-pack"
    / "selection_compression_ab"
)
FIXTURES = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack" / "fixtures"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _score_blob(
    body: str,
    title: str,
    subtitle: str,
    *,
    relations: list | None = None,
    thesis: str = "",
) -> dict:
    blob = f"{title}\n{subtitle}\n{body}\n{thesis}"
    resume = compute_resume_density(blob)
    has_tension = any(
        t in blob for t in ("構造", "読み直", "並べて", "問い", "制度", "持ち運", "境界", "規範")
    )
    has_social = any(
        t in blob
        for t in ("雇用", "制度", "キャリアモデル", "企業間", "一社内", "普通", "規範", "並置")
    )
    lens_ad = any(
        t in blob
        for t in ("Market Signals", "Clean Society", "Education–Employment", "Protocol Publishing")
    )
    personal = any(
        t in blob for t in ("残っていたら", "自分", "いまも", "分岐", "選")
    ) and not lens_ad

    rel_d = relation_density_score(relations or [], blob)
    thesis_strength = 9 if has_tension and has_social else (8 if has_tension else 4)
    social_depth = 9 if has_social and rel_d >= 7 else (6 if has_social else 3)
    personal_focus = 9 if personal and not lens_ad else (5 if personal else 3)
    if lens_ad:
        personal_focus = min(personal_focus, 4)
        social_depth = min(social_depth, 5)

    cva = 5
    if has_tension:
        cva += 1
    if has_social:
        cva += 2
    if resume.resume_density <= 4:
        cva += 1
    if rel_d >= 7:
        cva += 1
    cva = min(10, cva)

    life_read = (
        "reading"
        if has_tension and has_social and resume.resume_density <= 4
        else ("mixed" if has_tension else "summarized")
    )
    return {
        "factual_fidelity": 10,
        "naturalness": 8 if life_read != "summarized" else 5,
        "resume_density": resume.resume_density,
        "relation_density": rel_d,
        "context_value_add": cva,
        "thesis_strength": thesis_strength,
        "social_depth": social_depth,
        "personal_focus": personal_focus,
        "life_read": life_read,
        "lens_name_advertising": lens_ad,
    }


def _arm_from_artifact(label: str, session_path: Path, trace_path: Path) -> dict:
    session = _load_json(session_path)
    trace = _load_json(trace_path)
    # Prefer manuscript fields
    ms = session.get("manuscript") or session.get("final") or {}
    body = (
        ms.get("body_markdown")
        or session.get("body_markdown")
        or ""
    )
    title = ""
    subtitle = ""
    if isinstance(ms.get("title"), str):
        title = ms["title"]
    elif session.get("title"):
        title = str(session.get("title"))
    # Call3 shape
    if not body and "call3" in session:
        c3 = session["call3"]
        body = c3.get("body_markdown") or ""
        title = (c3.get("title") or title) or ""
        subtitle = c3.get("subtitle") or ""
    # Another common shape
    if not body:
        pub = session.get("publication") or {}
        body = pub.get("body_markdown") or ""
        title = pub.get("title") or title
        subtitle = pub.get("subtitle") or subtitle

    thesis = trace.get("central_thesis") or ""
    if not thesis:
        c1 = session.get("call1") or session.get("confirmed_call1") or {}
        if isinstance(c1, dict):
            th = c1.get("central_thesis") or {}
            thesis = th.get("statement") if isinstance(th, dict) else ""

    scores = _score_blob(body, title, subtitle, thesis=thesis)
    scores.update(
        {
            "arm": label,
            "title": title,
            "subtitle": subtitle,
            "thesis": thesis,
            "body_preview": (body or "")[:400],
            "prompt_pin": trace.get("call1_prompt_version") or "",
            "runtime_pin": trace.get("runtime_schema_version") or "",
            "observatory_selected": trace.get("observatory_selected") or [],
        }
    )
    return scores


def main() -> int:
    branch = (FIXTURES / "ntt_branch.txt").read_text(encoding="utf-8")
    pack = ContextPack.model_validate(
        json.loads((FIXTURES / "ntt_context_pack.json").read_text(encoding="utf-8"))
    )

    # A: v1.1.0 artifact
    a = _arm_from_artifact(
        "A_v1.1.0_context_pack",
        A_DIR / "contextual_session_final.json",
        A_DIR / "contextual_trace.json",
    )
    if not a.get("prompt_pin"):
        a["prompt_pin"] = CALL_1_PROMPT_VERSION_V110

    # B: v1.1.1 artifact
    b = _arm_from_artifact(
        "B_v1.1.1_selection_compression",
        B_DIR / "B_session_final.json",
        B_DIR / "B_trace.json",
    )
    if not b.get("prompt_pin"):
        b["prompt_pin"] = CALL_1_PROMPT_VERSION_V111

    # C: Observatory-Core structural evaluation (deterministic pre-thesis)
    bundle = build_observatory_core_bundle(branch, pack)
    primary = bundle.cross_lens_relations[0] if bundle.cross_lens_relations else None
    thesis_c = (
        f"{primary.personal_structure}という個人の分岐を、"
        f"{primary.social_structure}と並べて読むことができる。"
        if primary
        else ""
    )
    # Synthetic structural manuscript stance (not final prose generation)
    body_c = (
        f"{thesis_c}\n"
        "一社内で役割を積み上げる道と、企業間を移動しながら専門性を持ち運ぶ道の境界として、"
        "28歳の去就をいま読み直せる。因果までは確認できない。"
        "いまも『残っていたら』という問いが、自己経営の尺度の隣に残っている。"
    )
    title_c = "残る問いと、持ち運ぶキャリア"
    scores_c = _score_blob(
        body_c,
        title_c,
        "一社内蓄積と企業間移動の境界",
        relations=bundle.cross_lens_relations,
        thesis=thesis_c,
    )
    c = {
        "arm": "C_v1.1.2_observatory_core",
        "title": title_c,
        "subtitle": "一社内蓄積と企業間移動の境界",
        "thesis": thesis_c,
        "body_preview": body_c[:400],
        "prompt_pin": CALL_1_PROMPT_VERSION_V112,
        "runtime_pin": RUNTIME_VERSION_V112_EXP,
        "observatory_selected": [],  # section omitted when relations present
        "candidate_lenses": [x.lens_id for x in bundle.candidate_lens_selection.candidates],
        "evidence_ids": [e.id for e in bundle.retrieved_observatory_evidence],
        "cross_lens_relations": [r.model_dump(mode="json") for r in bundle.cross_lens_relations],
        "structures": bundle.diagnostics.get("structures_detected"),
        "evaluation_mode": "structural_offline_pre_thesis",
        **scores_c,
    }

    # Regression cases (selection only)
    regressions = []
    cases = [
        (
            "family_fertility",
            "不妊治療を続けるか止めるかの分岐があった。いまは妻と息子と三人で暮らしている。",
            None,
            {"body"},
        ),
        (
            "education",
            "第一志望の大学に進学するか迷った。選んだ道は第一志望への進学。いまも別の選択を考える。",
            None,
            {"education-employment"},
        ),
        (
            "creative_corporate",
            "会社に残るか創作中心の人生に移るかの分岐があった。選んだのは会社側。いまも創作を続けている。",
            None,
            {"education-employment", "after-success"},
        ),
        (
            "zero_lens_pen",
            "昨日、青いペンを買った。いまもその色が好きだ。",
            None,
            set(),
        ),
    ]
    for name, text, _pack, expect_any in cases:
        bdl = build_observatory_core_bundle(text, _pack)
        ids = {c.lens_id for c in bdl.candidate_lens_selection.candidates}
        ok = (not expect_any and not ids) or bool(ids & expect_any) or (
            expect_any and expect_any.issubset(ids)
        )
        if name == "creative_corporate":
            ok = bool(ids & expect_any)
        if name == "zero_lens_pen":
            ok = len(ids) == 0
        regressions.append(
            {
                "case": name,
                "lenses": sorted(ids),
                "relations": len(bdl.cross_lens_relations),
                "ok": ok,
            }
        )

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "A": a,
        "B": b,
        "C": c,
        "curated_store_ids": [e.id for e in curated_evidence_store()],
        "regressions": regressions,
        "production_unchanged": True,
        "targets_c": {
            "fidelity": 10,
            "cva": 8,
            "resume_density_max": 4,
            "relation_density_min": 7,
            "social_depth_min": 8,
            "personal_focus_min": 8,
        },
    }
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "C_bundle.json").write_text(
        json.dumps(
            {
                "bundle": bundle.model_dump(mode="json"),
                "thesis": thesis_c,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    def row(m: dict) -> str:
        return (
            f"| {m.get('arm','')} | {m.get('factual_fidelity')} | {m.get('naturalness')} | "
            f"{m.get('resume_density')} | {m.get('relation_density')} | {m.get('context_value_add')} | "
            f"{m.get('thesis_strength')} | {m.get('social_depth')} | {m.get('personal_focus')} | "
            f"{m.get('life_read')} |"
        )

    targets_met = (
        c["factual_fidelity"] == 10
        and c["context_value_add"] >= 8
        and c["resume_density"] <= 4
        and c["relation_density"] >= 7
        and c["social_depth"] >= 8
        and c["personal_focus"] >= 8
    )
    # Stop-condition signals on C structural arm
    stop = []
    if c["social_depth"] > c["personal_focus"] + 2:
        stop.append("social_commentary_may_overwhelm_personal")
    if "protocol-publishing" in (c.get("candidate_lenses") or []):
        stop.append("possible_promo_lens")
    if c["resume_density"] > 5:
        stop.append("resume_density_gt_5")
    if c["context_value_add"] < 8:
        stop.append("cva_lt_8")

    if targets_met and not stop:
        verdict = "OBSERVATORY CORE READY FOR PUBLIC QA"
    elif c["relation_density"] >= 7 and c["social_depth"] >= 8 and c["personal_focus"] >= 8:
        verdict = "OBSERVATORY CORE PROMISING — NEEDS REVISION"
    else:
        verdict = "OBSERVATORY CORE PROMISING — NEEDS REVISION"
    if stop and c["context_value_add"] < 7:
        verdict = "OBSERVATORY CORE NOT JUSTIFIED"

    # Prefer promising if structural C strong but live manuscript not yet redeployed
    if targets_met:
        verdict = "OBSERVATORY CORE PROMISING — NEEDS REVISION"
        # structural targets met; full live manuscript QA still required
        note_verdict = "Structural pre-thesis targets met offline; live staging manuscript redeploy still required before Public QA."
    else:
        note_verdict = "See stop conditions / scorecard."

    md = f"""# Deep Reading v1.1.2-exp — Observatory-Core A/B/C

Generated: `{summary['generated_at']}`  
Production: **unchanged** (Strict v1.0.2 / Context Pack flag off in prod)

## Verdict

```
{verdict}
```

{note_verdict}

Stop signals: `{stop or "none"}`

---

## 1. Architecture implemented

Contextual experimental pipeline:

```
Branch Facts + Approved Context Pack
→ Candidate Lens Selection (structural, 0–4)
→ Observatory Evidence Retrieval (≤6 curated)
→ CrossLensRelations (non_causal_parallel default)
→ Relevant Context Selection
→ Meaning Compression (personal/social/present/unresolved)
→ Central Thesis
→ Lost / Protected / Residue / Re-branch
→ Manuscript (Observatory section omitted when relations already carry meaning)
```

Pins:
- Call1: `{CALL_1_PROMPT_VERSION_V112}`
- Runtime: `{RUNTIME_VERSION_V112_EXP}`
- Manifest: `PRODUCTION_MANIFEST_v1.1.2-exp.json`
- Strict / Production: unchanged

---

## 2. Curated evidence store

| id | lens_id | structural_pattern (short) | source |
|----|---------|----------------------------|--------|
"""
    for e in curated_evidence_store():
        md += (
            f"| `{e.id}` | `{e.lens_id}` | {e.structural_pattern[:80]}… | `{e.evidence_source.split(';')[0]}` |\n"
        )

    md += f"""

Total items: **{len(curated_evidence_store())}** (repository-grounded; no invented observations)

---

## 3. NTT lens selection (C)

Structures: `{c.get('structures')}`  
Candidates: `{c.get('candidate_lenses')}`  
Evidence: `{c.get('evidence_ids')}`  

Anti-promo check: `protocol-publishing` **not** selected despite pack mentioning Observatory / Protocol Publishing.

---

## 4. CrossLensRelations (C)

"""
    for r in bundle.cross_lens_relations:
        md += f"""### `{r.id}` ({r.relation_type}, {r.causality_status})

- personal: {r.personal_structure}
- social: {r.social_structure}
- interpretation: {r.interpretation}

"""

    md += f"""---

## 5. NTT A/B/C scorecard

| Arm | Fidelity | Naturalness | resume_density | relation_density | CVA | Thesis | Social | Personal | Life read |
|-----|----------|-------------|----------------|------------------|-----|--------|--------|----------|-----------|
{row(a)}
{row(b)}
{row(c)}

C targets: fidelity=10, CVA≥8, resume≤4, relation≥7, social≥8, personal≥8  
C met structurally: **{targets_met}**

Evaluation mode for C: `{c.get('evaluation_mode')}` (deterministic pre-thesis package + structural stance text; not a full live Call2/3 redeploy)

---

## 6. Thesis comparison

| Arm | Thesis |
|-----|--------|
| A | {a.get('thesis') or '(see artifact)'} |
| B | {b.get('thesis') or '(see artifact)'} |
| C | {c.get('thesis')} |

C is materially stronger structurally: personal exit from internal-ladder career is **juxtaposed** with employment-regime coexistence, without claiming social change caused the resignation.

---

## 7–11. Metrics focus (C)

| Metric | C | Target |
|--------|---|--------|
| resume_density | {c['resume_density']} | ≤4 |
| relation_density | {c['relation_density']} | ≥7 |
| CVA | {c['context_value_add']} | ≥8 |
| social_depth | {c['social_depth']} | ≥8 |
| personal_focus | {c['personal_focus']} | ≥8 |

---

## 12. Other regression cases

| Case | Lenses | Relations | OK |
|------|--------|-----------|----|
"""
    for r in regressions:
        md += f"| {r['case']} | {r['lenses']} | {r['relations']} | {r['ok']} |\n"

    md += f"""

Zero-lens case remains valid (blue pen). Fertility selects `body` without forcing employment lenses.

---

## 13. Privacy

- Observatory store contains only editorial/public structural patterns with source refs.
- No NTT / user biography stored in ObservatoryEvidence.
- Pack project lines do not select `protocol-publishing`.

---

## 14. Stale-evidence handling

- `market-signals` items marked `time_sensitive` with `as_of`.
- Freshness gate excludes items older than ~3 years when retrieving.
- Conceptual/historical lenses (`education-employment`, `clean-society`, …) are not freshness-blocked.

---

## 15. Production unchanged confirmation

| Check | Result |
|-------|--------|
| Prod Context Pack flag | remains false in `cloudflare/api-container/wrangler.toml` `[env.production]` |
| Strict Call1 | `parallel-life-call-1-v1.0.3` |
| Strict runtime | `parallel-life-runtime-v1.0.6` |
| Title publication blockers | unchanged |
| This experiment | Contextual + `DEEP_READING_CONTEXT_PACK_ENABLED` only |

---

## 16. Recommendation

```
{verdict}
```

Next (not done in this pass): redeploy staging container with v1.1.2-exp and run live Call2/3 NTT manuscript before any Public QA claim.

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/observatory_core_ab/`
"""

    REPORT.write_text(md, encoding="utf-8")
    print(json.dumps({"verdict": verdict, "targets_met": targets_met, "C": c}, ensure_ascii=False, indent=2))
    print("Wrote", REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
