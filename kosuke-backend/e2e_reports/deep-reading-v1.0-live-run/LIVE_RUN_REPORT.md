# Parallel Life Deep Reading v1.0 — Live E2E Report (valid API key)

**Date:** 2026-08-07  
**Model:** `gpt-4o-mini-2024-07-18`  
**Implementation modified during run:** No  
**Prompts modified during run:** No  

## Executive verdict

**All four cases: FAIL**

OpenAI authentication succeeded. Call 1 LLM responses were returned for every case, but **Call 1 runtime parsing crashed** on schema/type mismatches. Therefore:

- user confirmation stage was not reached via the service
- Call 2 draft was not generated
- Call 3 edit/validate was not generated
- final visible manuscripts do not exist

Raw Call 1 JSON was captured and manually inspected for editorial signals.

---

## Blocking defect (shared)

### Exact error

```text
AttributeError: 'bool' object has no attribute 'get'
# or
AttributeError: 'str' object has no attribute 'get'
```

### Where

`parse_call1_payload` / Call 1 grounding path (`app/parallel_life_deep_reading/grounding.py`)

### Cause

LLM returned fields with wrong types relative to the runtime schema. Observed mismatches:

| Field | Expected | Observed |
|---|---|---|
| `input_sufficiency` | object | `bool` or `str` |
| `user_confirmation_view` | object | `bool` or `str` |
| `central_thesis` | object | `str` |
| `rebranch_design` | array | `object` |
| `lost_structure` / `protected_structure` | array | `object` |
| `grounded_input.facts` etc. | typed fact objects with ids | bare strings / alternate keys (`explicit_fact`, etc.) |

### Ownership

**Call 1** (prompt schema underspecified for the model) **+ Call 1 parser** (not defensive against shape drift).  
Not frontend. Runtime gates for Lens/Re-branch/scene were not reached on live output.

---

## Case results

### Case 1 — Fertility / retrospective counterfactual only

| Capture item | Result |
|---|---|
| Call 1 output | Raw JSON captured; service parse **FAIL** |
| user confirmation view | Missing/invalid (`bool`) |
| branch classifications | Manual: `secondary_branches=[]`; counterfactual-like text present as string list |
| Observatory lenses | selected `[]`; evaluated present but unused by service |
| Call 2 / Call 3 / final manuscript | **not produced** |
| Re-branch publishability | Raw candidate exists but generic; `support_ids=[]` |
| unsupported scene / generic advice / title validation | **not run** |
| final validation | **not run** |

**Manual Call 1 content issues**
- 「二人目を持っていたらどうだったか」が `user_feeling` に入り、`user_question` になっていない
- fact IDs なし（string list）
- Residue 空
- Re-branch: 「選択の影響を深く掘り下げる」など一般的

**Verdict:** **FAIL**  
**Belongs to:** Call 1 (classification + schema) / parser

---

### Case 2 — Same case + explicit later discussion/decision

| Capture item | Result |
|---|---|
| Call 1 output | Raw JSON captured; parse **FAIL** |
| Expected `actual_secondary_branch` | Partially hinted only as `{"branch_type":"later_branch",...}` — **not** typed `actual_secondary_branch` with `explicit_evidence_ids` |
| Question vs feeling | 「二人目を持っていたら…」が再び `user_feeling` |
| Observatory | selected `[]` |
| Call 2 / Call 3 | **not produced** |

**Verdict:** **FAIL**  
**Belongs to:** Call 1 (failed to emit required secondary classification schema)

---

### Case 3 — First-choice university admission

| Capture item | Result |
|---|---|
| Call 1 output | Raw JSON captured; parse **FAIL** |
| Grounding quality | Severely incomplete: `grounded_input` が `chosen_path` / `unchosen_path` のみ。合格事実・現在文脈・問いの構造化が欠落 |
| Rejection inversion | Cannot fully verify in final manuscript (none). Raw thesis is generic about 進路 |
| Observatory | selected `[]` |
| Call 2 / Call 3 | **not produced** |

**Verdict:** **FAIL**  
**Belongs to:** Call 1 (under-grounding) / parser

---

### Case 4 — Creative vs corporate career

| Capture item | Result |
|---|---|
| Call 1 output | Raw JSON captured; parse **FAIL** |
| Boundary mixups | 問いが `user_feeling` と `user_question` に重複的・不整合 |
| `explicit_fact` | object map（list of fact objects ではない） |
| Re-branch | generic（読者向けエッセイ等）, `support_ids=[]` |
| Call 2 / Call 3 | **not produced** |

**Verdict:** **FAIL**  
**Belongs to:** Call 1 / parser

---

## Evaluation matrix (requested dimensions)

| Dimension | Live assessment |
|---|---|
| factual consistency | **Not assessable on final manuscript.** Call 1 raw already drops/misfiles facts (esp. Case 3). |
| Japanese naturalness | N/A (no manuscript) |
| repetition | N/A |
| section continuity | N/A |
| Residue quality | **Poor at Call 1** — residue empty in all four raw outputs |
| Observatory relevance | Selected empty (may be correct), but evidence-gate objects are not reliably structured |
| Re-branch specificity | **Poor** — generic forms, empty `support_ids` |
| Closing quality | N/A |
| invented scenes | N/A (Call 3 not reached) |
| generic advice | Not in manuscript; Re-branch text already leans generic |
| title consistency | N/A |

---

## PASS / PASS WITH REVISION / FAIL

| Case | Rating |
|---|---|
| 1 Fertility counterfactual only | **FAIL** |
| 2 Fertility actual secondary | **FAIL** |
| 3 University admission | **FAIL** |
| 4 Creative vs corporate | **FAIL** |

---

## Exact problematic excerpts (from Call 1 raw)

### Schema / type failures (all cases)
- `input_sufficiency: true` or string instead of object
- `user_confirmation_view: true` / string instead of confirmation object

### Case 1 — question misfiled as feeling
> `user_feeling`: 「今も、二人目を持っていたらどうだったかと考えることがある。」

### Case 1 — generic Re-branch
> `branch_specific_form`: 「選択の影響を深く掘り下げる」 (`support_ids: []`)

### Case 2 — secondary not schema-valid actual_secondary_branch
> `{"branch_type": "later_branch", "content": "息子を授かった後、二人目を目指す治療を続けるか妻と話し合い、やめた。"}`

### Case 3 — under-grounded input
> `grounded_input` keys only: `chosen_path`, `unchosen_path`

### Case 4 — generic Re-branch
> `branch_specific_form`: 「選択の結果に関するエッセイ」 (`support_ids: []`)

---

## Runtime validation decisions

| Gate | Exercised on live final output? |
|---|---|
| actual_secondary evidence requirement | No (parse crash before runtime normalize of service path) |
| Lens evidence gate recalculation | No |
| Re-branch publishable recalculation | No |
| unsupported scene / generic advice | No |
| publication gate | No |
| Heuristic manuscript fallback | **Correctly not used** |

Offline unit fixtures previously passed these gates; **live LLM output did not reach them**.

---

## Release recommendation

**Do not release. Do not freeze Production Candidate v1.0.**

Minimum before re-test:
1. Harden Call 1 prompt with explicit JSON schema examples / required types.
2. Make Call 1 parser defensive (coerce or reject with structured error, never AttributeError).
3. Enforce fact objects with IDs; forbid bare strings for facts/questions.
4. Re-run this same 4-case live suite with **no further prompt/code changes during the run**.
5. Only then evaluate manuscript-level PASS / PASS WITH REVISION / FAIL.

---

## Artifacts

`kosuke-backend/e2e_reports/deep-reading-v1.0-live-run/`

- `case*_call1_raw.json` — raw LLM Call 1
- `case*_call1_diag.json` — parse failure diagnostics
- `case*_call1_manual_extract.json` — manual extracts
- this report
