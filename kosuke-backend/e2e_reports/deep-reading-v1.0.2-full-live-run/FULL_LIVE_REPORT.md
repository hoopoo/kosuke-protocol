# Parallel Life Deep Reading — Production Candidate v1.0.2 Full Live Report

**Date:** 2026-08-07  
**Model:** `gpt-4o-mini`  
**Versions:**
- Call 1: `parallel-life-call-1-v1.0.2` / schema `parallel-life-call-1-schema-v1.0.2` (**changed**)
- Call 2: `parallel-life-call-2-v1.0.1`
- Call 3: `parallel-life-call-3-v1.0.1`

Artifacts: `e2e_reports/deep-reading-v1.0.2-full-live-run/`

---

## 1. Exact reason residue_candidates were zero (Phase 1)

| Cause | Applies |
|---|---|
| **A. Prompt generation failure** | **Primary** — Call 1 v1.0.1 system prompt never mentioned Residue |
| **B. Schema omission/default** | **Enabling** — empty `items: []` was schema-valid; no past/present anchors |
| C–H (normalize / support / distance / sensitive / over-filter / field names) | **No** — live fixtures had `normalization_applied=[]` and empty items before any residue filter |

Diagnosis file: `e2e_reports/deep-reading-v1.0.1-full-live-run/PHASE1_RESIDUE_DIAGNOSIS.md`

## 2. Whether Call 1 changed

**Yes — focused Residue contract only** (prompt + schema fields + runtime validation/assist). No broad Call 1 redesign.

## 3. Call 1 version after repair

- Prompt: `parallel-life-call-1-v1.0.2`
- Schema: `parallel-life-call-1-schema-v1.0.2` (added `past_anchor_ids`, `present_anchor_ids`, `residue_statement`)

## 4. Call 2 changes

- Evidence Ledger (`ALLOWED_PERSONAL_EVIDENCE` / `DO_NOT_INVENT`)
- `paragraph_support` map required/parsed
- Reject draft if no validated Residue
- Stronger continuous-essay / anti-invention prompt (`v1.0.1`)
- Re-branch concrete-noun + anti-generic-verb filters

## 5. Call 3 changes

- Priority order: fidelity → remove unsupported biography → Residue/thesis → Japanese → polish
- Evidence Ledger passed into edit prompt
- Removes unsupported personal details via runtime finalize
- Version `v1.0.1`

## 6. Runtime validation changes

- Residue validate: past+present anchors, non-empty statement, not question-as-residue, not question-as-present-anchor, inference distance limits (sensitive → `near` only)
- Deterministic Residue assist when model empty **but** anchors exist (structural only)
- No Residue → `needs_additional_input` (does **not** treat question as centrality)
- `unsupported_personal_detail` first-class blocker
- Residue centrality uses validated Residue meaning + present-life anchors + closing return
- Copy detector: allow grounded fact text; don’t treat fact reuse as plagiarism
- Scene patterns extended (campus/club/seminar)

## 7. Unsupported-personal-detail detection

Patterns include: campus, club, seminar, professor, job functions, unsupplied duration, prestige, invented excitement, invented conversation (unless 話し合 evidence exists).

## 8. Paragraph support-map

Call 2 returns `paragraph_support[]`; parser fills previews; coverage recorded in diagnostics (live: **1.0** on all four).

## 9. Re-branch changes

Generic verbs rejected; form must contain a grounded concrete noun; omitted when none publishable (all four live: omitted).

## 10. Unit/integration tests

`60+` Deep Reading tests green including `tests/test_deep_reading_v102_repair.py` (campus/club/job/duration/residue/rebranch/centrality).

## 11–15. Four-case live results

| Case | Call1 Residue | Call2 personal/scenes | Call3 publish | Runtime blockers | Fidelity /10 | Naturalness /10 | Continuity /10 | Specificity /10 | Residue /10 | Re-branch /10 | Title /10 | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 validated (assist or model) | 0 / 0 | **Yes** | none | 8 | 8 | 8 | 7 | 7 | n/a omit | 6 | **PASS WITH REVISION** |
| 2 | 1 (model; present once included question — now forbidden) | 0 / 0 | **Yes** | none | 8 | 7 | 7 | 7 | 5 | n/a omit | 7 | **PASS WITH REVISION** |
| 3 | 1 | 0 / 0 | **Yes** | none | 7 | 7 | 7 | 6 | 5 | n/a omit | 6 | **FAIL** (fidelity &lt;10; soft causality) |
| 4 | 1 | 0 / 0 | **Yes** | none | 8 | 6 | 7 | 6 | 5 | n/a omit | 6 | **PASS WITH REVISION** |

### Case notes / problematic excerpts

**Case 1**
- Good: no campus/duration invention; continuous; question kept open; Residue connection present.
- Remaining: 「息子の成長を見守る喜び」— not supplied; mild emotional elaboration.
- Title `選択と家族の幸せ` is soft/generic.

**Case 2**
- Good: discussion/decision present (話し合い／やめる); continuous; no chapter stack.
- Remaining: 「現在の家族の形に満足していることが伺える」— unsupported inference; Residue statement was near-question form with question as present anchor in this run (runtime now rejects that pattern).

**Case 3**
- Good: 第一志望 / 早稲田大学第一文学部 / 合格 / 進学 retained; no club/ゼミ.
- Remaining: 「学びや人との出会い」「影響を与えている」— unsupplied causal/biographical bridge.
- Fidelity not 10/10 → **FAIL** freeze bar.

**Case 4**
- Good: no marketing/sales invention; Observatory omitted; continuous short form.
- Remaining: 「ここで重要なのは」template tone; 「影響を与えている」asserted rather than qualified as open residue.

### Manual scores detail (requested)

| Dimension | C1 | C2 | C3 | C4 |
|---|---|---|---|---|
| Factual fidelity | 8 | 8 | 7 | 8 |
| Naturalness | 8 | 7 | 7 | 6 |
| Continuity | 8 | 7 | 7 | 7 |
| Specificity | 7 | 7 | 6 | 6 |
| Residue | 7 | 5 | 5 | 5 |
| Re-branch | omit | omit | omit | omit |
| Title | 6 | 7 | 6 | 6 |

## 16. Can Production Candidate be frozen?

**No.**

Reasons:
1. Pass criteria require **factual fidelity = 10/10** on all four — not met (7–8).
2. Soft unsupported causality / emotional gloss remains in Cases 1–4.
3. Case 2 live Residue quality was below contract (question used as present anchor); fix landed after that run and needs another clean four-case pass.
4. Manuscripts are safer and shorter, but not yet freeze-grade editorial Residue centrality.

---

## Cross-case findings (post-repair)

### Strengths vs v1.0.1
- Residue no longer universally empty
- Campus/club/job-function inventions largely gone
- Chapter-report feel largely gone (0–1 headings)
- All four reached `complete` + runtime publishable after copy-detector correction
- Support-map coverage 1.0

### Remaining weaknesses
- Causal “影響” language without evidence
- Mild present-life embroidery (成長を見守る / 満足)
- Residue statements sometimes too close to questions or too abstract
- Titles still theme-summary
- Re-branch always omitted (acceptable if none specific)

### Recommended next revisions (not applied in this report cycle)
1. Harden Call 1 Residue examples: present anchors must be current_context/feeling/fact with 現在 markers; ban question IDs (code done; prompt examples strengthen).
2. Call 2/3: ban unsupplied causal verbs (“影響を与えた/ている”) unless Residue is explicitly qualified.
3. One more live four-case run after Case2-style Residue rejection is confirmed end-to-end.
4. Only then reconsider Production Candidate freeze.
