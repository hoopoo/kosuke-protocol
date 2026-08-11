# Parallel Life Deep Reading v1.1.8-exp — Branch Semantics Report

Generated: 2026-08-08  
Scope: implementation + deterministic tests only  
**No live Public QA in this pass. Production untouched.**

## Recommendation

```
BRANCH SEMANTICS READY FOR LIVE QA
```

---

## 1. BranchSemantics schema

New module: `app/parallel_life_deep_reading/branch_semantics.py`

Fields (all optional / may be empty):

| Field | Role |
|-------|------|
| `domain` | hint only (`career`…`unknown`) — not a thesis template |
| `changed_dimension` | what part of life diverged |
| `chosen_structure` / `unchosen_structure` | grounded path sketches |
| `central_tension` | active tension (not always measurement) |
| `lost_verifiability` | what can no longer be known/continued |
| `protected_possibility` | what remained possible/unclosed |
| `present_residue` | what of the old branch is still active now |
| `possible_rebranch_modes` | `choose` / `preserve` / `reconsider` / `revisit` / `leave_unresolved` / `not_act` / `observe` / `redefine` |
| `sensitive_boundaries` | causality / affect / medical limits |
| `evidence_ids` | grounding anchors |
| `confidence` | detector confidence |

Pipeline (Contextual):

```
Grounded Branch
→ BranchSemantics
→ Approved Context Pack
→ Observatory / CrossLens
→ MeaningCompression
→ Central Thesis
→ SectionContracts
→ Interpretive Claims
→ Call 2 / Call 3
```

Wired in `runtime_validation.apply_call1_runtime_gates` before Observatory.

---

## 2. Career-specific logic removed

Removed / demoted as **generic defaults** from SectionContracts:

- branch_point: 「勤務先の一点ではなく…持ち運ぶ道」 → only when employment evidence
- chosen_path: 「所属が変わるたびに自分の仕事を定義し直す」 → employment-only
- Lost: institutional ruler default → `lost_verifiability`
- Protected: work-redefinition default → `protected_possibility`
- Residue: always-measurement → `present_residue` / active tension
- Re-branch: 「役職や年収…長期の積み重ね」 → modes from BranchSemantics
- Observatory empty claim: employment parallel → soft generic when no EE evidence
- thesis_closure: `arc_measurement_thread` → `arc_tension_thread`

Career language remains available when BranchSemantics + explicit employment evidence support it (NTT path).

---

## 3. `_has_employment_regime` fix

- Removed bare `残る` / `移る` triggers
- Requires explicit markers: 転職 / 勤務 / 一社 / 外資 / NTT / 役職 / 年収 / 長期雇用 / …
- Prefer BranchSemantics `diagnostics.explicit_employment_evidence`
- Local-stay / romance leave language no longer implies employment regime

---

## 4. Clarification 400 fix

`DeepReadingService.confirm(action=approve)` when status is:

- `needs_additional_input`
- `structural_ambiguity`
- missing residue (soft)

→ **HTTP 200** session response with:

- `status`
- `questions`
- `clarification_required: true`

Does **not** raise `DeepReadingGenerationError`.

Material contradictions / true malformed approve still error (v1.0.1 case09 preserved).

---

## 5. Deterministic 10-case semantics matrix

`tests/test_deep_reading_v118_branch_semantics.py` — **10/10 passed**

| Case | Domain | changed_dimension (shape) | Career leak | Re-branch modes (shape) |
|------|--------|---------------------------|-------------|-------------------------|
| A career | career | institutional belonging/mobility | allowed | redefine/choose when salary Q |
| B family | family | family configuration | none | leave_unresolved / preserve / observe |
| C education | education | educational opportunity | none | reconsider / observe |
| D romance | romance | relationship continuity | none | observe / revisit / leave_unresolved |
| E health | health | bodily capacity/adaptation | none | preserve / observe / not_act |
| F entrepreneurship | entrepreneurship/career/mixed | ownership/stability | controlled | reconsider / preserve / choose |
| G creative | creative | expression/livelihood time | none | choose / preserve / revisit |
| H vague | unknown/mixed | thin | none | leave_unresolved / not_act / observe |
| I zero-lens | place | place/everyday belonging | none | preserve / reconsider |
| J sensitive | health | bodily + work interruption | none | sensitive_boundaries set |

Negative tests passed:

- family ↛ 役職・年収 / 仕事を定義し直す
- romance ↛ 蓄積 / 制度内評価
- education ↛ automatic career mobility / 定義し直す
- creative ↛ salary metric re-branch
- health ↛ causal invention in semantics
- bare stay/leave ↛ employment regime

---

## 6. NTT regression

Deterministic NTT/career fixture:

- domain=`career`
- `_has_employment_regime` true
- Lost / Protected / Re-branch contracts present with interpretive claims
- Career measurement Re-branch still available when question is 役職や年収

Related regressions: v113/v114/v116/v117/v118 — **33 passed**.

---

## 7. Remaining known risks

1. **Live LLM Call1** may still emit career-flavored Lost/Protected before server repair; repair + contracts now overwrite from BranchSemantics, but prose quality needs live QA.
2. **Observatory evidence store** still employment-skewed; 0-lens remains common for romance/creative — thresholds not loosened; store not expanded.
3. **Domain detector** is heuristic; `mixed` / mis-tags possible on short inputs — contracts must stay evidence-bound (already).
4. **Frontend** must consume HTTP 200 + `clarification_required` (not treat as error toast).
5. Staging deploy + FORCE_CONTAINER_RESTART still required before live Public QA sees pins.

---

## 8. Production untouched confirmation

| Surface | Status |
|---------|--------|
| Strict Call1 pin | still `parallel-life-call-1-v1.0.3` |
| Strict runtime | still `parallel-life-runtime-v1.0.6` |
| Title validation | unchanged |
| Publication gates | not loosened |
| Observatory thresholds / evidence store | not expanded; matching may use BranchSemantics as hint only |
| Active Contextual pins | `parallel-life-call-1-v1.1.8-exp` / `parallel-life-runtime-v1.1.8-exp` |
| Manifest | `PRODUCTION_MANIFEST_v1.1.8-exp.json` |

---

## Version pins

```
Call 1 Contextual: parallel-life-call-1-v1.1.8-exp
Runtime Contextual: parallel-life-runtime-v1.1.8-exp
Call 2 Contextual: parallel-life-call-2-v1.1.8-exp
Call 3 Contextual: parallel-life-call-3-v1.1.8-exp
```

## Next step

Staging deploy → re-run the same 10 Public QA cases (no auto-tune mid-batch).
