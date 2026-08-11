# Deep Reading Production Candidate v1.0.3 — Full Live Report

**Date:** 2026-08-07  
**Goal:** Eliminate plausible but unsupported meaning completion (causality / affect / role-behavior) without redesigning Call 1/2/3 architecture.  
**Fixtures:** unchanged (case1–4).

## Versions

| Component | Version | Changed? |
|-----------|---------|----------|
| Call 1 prompt | `parallel-life-call-1-v1.0.2` | No (present-anchor wording clarified only) |
| Call 1 schema | `parallel-life-call-1-schema-v1.0.2` | No |
| Call 2 prompt | `parallel-life-call-2-v1.0.2` | Yes (narrow) |
| Call 3 prompt | `parallel-life-call-3-v1.0.2` | Yes (narrow) |
| Runtime | `deep-reading-runtime-v1.0.3` | Yes |

## Unit tests

74 Deep Reading–related tests passed (including `test_deep_reading_v103_overreach.py` A–F + variants).

---

## Completion report

### 1. Present-anchor rule verification

**Enforced in runtime** (`validate_residue_candidate`):

- Present anchors may only be present-life facts / feelings / `ctx_*`.
- Forbidden as present: `user_question`, `unknown`, `model_inference`.
- Missing present anchor → reject; no substitution with `user_question`.

**Test D:** 「二人目がいたらどうだったか」 may be a past/question anchor, but cannot satisfy `present_anchor_ids`.

Live: all four cases used non-question present IDs (`fact4` / `feeling1` / `fact3`).

### 2. Whether Call 1 changed

**No functional redesign.** Kept v1.0.2 prompt + schema. Only clarified that `present_anchor_ids` cannot be `user_question` / `unknown` / `model_inference` / thesis itself.

### 3. Call 2 changes (→ v1.0.2)

- Fact-bounded interpretation: no unsupported causality / affect / role-behavior.
- Prefer coexistence / comparison / open question / qualified inference.
- Require continuous prose + Residue weave; do not end as input restatement.
- Preserve `present_anchor` facts/feelings in body.

### 4. Call 3 changes (→ v1.0.2)

- Semantic-overreach pass before polish (blocking categories include causality / affect / role).
- Rewrite in context; model sees excerpts before deterministic strip.
- Causality finalize prefers present-clause preservation over hard delete.

### 5–7. Detectors

| Category | Implementation |
|----------|----------------|
| `unsupported_causality` | Assertion patterns + `causality_strength` 0–3; open-question exception; sensitive max association |
| `unsupported_affect` | Emotion lexicon; no synonym upgrade (楽しい ≠ 満足) |
| `unsupported_role_behavior` | Role/behavior phrases require explicit grounding |

### 8. Runtime gate changes

Blocking counters:

- `unsupported_causality_count`
- `unsupported_affect_count`
- `unsupported_role_behavior_count`

(+ existing personal detail / scene / advice / residue / thesis gates)

Independent recalculation in `recalculate_publication_gate`.  
Diagnostic: `manual_fidelity_gap_possible` when publishable but residual soft phrases remain.

### 9. Tests

`tests/test_deep_reading_v103_overreach.py`: A–F + spelling variants + neutralize present-clause + open-Q + 喜び/もたらす / 選択の結果 / 影響を受け.

---

## 10. Four-case live results (final run)

Artifacts: `e2e_reports/deep-reading-v1.0.3-full-live-run/`

### Case 1 — fertility / retrospective only

| Item | Result |
|------|--------|
| Call 1 Residue | 1 validated; present=`fact4` (三人家族・経営) |
| Call 2 unsupported c/a/r/p/s | 0/0/0/0/0 |
| Call 3 | publishable; blockers=[] |
| Final counters | all unsupported_* = 0; contradiction=0; advice=0 |
| Publication | **Yes** |
| Factual fidelity | **10/10** |
| Naturalness | **8/10** |
| Continuity | **9/10** |
| Remaining overreach | none material |

### Case 2 — fertility + discussion/decision

| Item | Result |
|------|--------|
| Call 1 Residue | 1 validated; present=`feeling1` |
| Call 2 unsupported | 0/0/0/0/0 |
| Call 3 | publishable |
| Final counters | all 0 |
| Publication | **Yes** |
| Factual fidelity | **9/10** |
| Naturalness | **7/10** |
| Continuity | **8/10** |
| Remaining overreach | Awkward line:「この選択は、実際に選んだのは…」(syntax, not invented biography). Discussion/decision retained. |

### Case 3 — university

| Item | Result |
|------|--------|
| Call 1 Residue | 1 validated; present=`fact3` |
| Call 2 unsupported causality | 1 (rewritten in Call 3) |
| Call 3 | publishable |
| Final counters | all 0 |
| Publication | **Yes** |
| Factual fidelity | **9/10** |
| Naturalness | **8/10** |
| Continuity | **8/10** |
| Remaining overreach | Open probe retained:「過去の選択が現在の生活にどのように影響を与えているのかを考えることがある。」(interrogative, not assertion; still soft causal framing). Title contains「影響」. |

### Case 4 — creative vs corporate

| Item | Result |
|------|--------|
| Call 1 Residue | 1 validated; present=`fact3` |
| Call 2 unsupported causality | 1 (cleared in Call 3) |
| Call 3 | publishable |
| Final counters | all 0 |
| Publication | **Yes** |
| Factual fidelity | **10/10** |
| Naturalness | **8/10** |
| Continuity | **8/10** |
| Remaining overreach | none material; manuscript is short/restrained |

---

## Aggregate vs PASS bar

| Requirement | Result |
|-------------|--------|
| factual fidelity = 10/10 (all) | **FAIL** (case2=9, case3=9) |
| naturalness ≥ 8/10 (all) | **FAIL** (case2=7) |
| continuity ≥ 8/10 (all) | PASS |
| unsupported_* counts = 0 | PASS (runtime) |
| contradiction = 0 | PASS |
| generic_advice published = 0 | PASS |
| all publishable | PASS |

### 11–13. Scores summary

| Case | Fidelity | Naturalness | Continuity | Publish |
|------|----------|-------------|------------|---------|
| 1 | 10 | 8 | 9 | Yes |
| 2 | 9 | 7 | 8 | Yes |
| 3 | 9 | 8 | 8 | Yes |
| 4 | 10 | 8 | 8 | Yes |

### 14. Remaining problematic excerpts

1. Case2:「この選択は、実際に選んだのは妻と息子と三人で暮らす人生だった。」
2. Case3:「過去の選択が現在の生活にどのように影響を与えているのかを考えることがある。」
3. Case3 title:「大学選択とその影響」

### 15. Publication result

Runtime: **4/4 publishable** with all blocking unsupported_* counters at 0.  
Manual PASS bar (fidelity 10 + naturalness ≥8 on all): **not met**.

### 16. Production Candidate freeze recommendation

**Do not freeze Production Candidate v1.0.3.**

Reasons:

1. Manual fidelity is not 10/10 on all four (case2 syntax / case3 soft causal framing + title).
2. Case2 naturalness below 8.
3. Open-question causality and title wording can still smuggle “影響” framing that the product goal wants minimized.
4. Call1 theses occasionally still invent causal/affect language (e.g. 幸せに繋が); out of v1.0.3 scope but still a fidelity risk upstream.

**What improved vs v1.0.2:** classic overreach phrases (成長を見守る / 満足している / 影響を与えている as bare assertion) are largely gone; Residue + present anchors are present; runtime independently blocks the new categories.

**Next narrow step (if continuing):** title gate for causal tokens; ban “影響を与えているのか” unless paired with explicit non-causal disclaimer; Call3 grammar repair for neutralized sentences; optional Call1 thesis hygiene (still no redesign of branch/Residue contracts).
