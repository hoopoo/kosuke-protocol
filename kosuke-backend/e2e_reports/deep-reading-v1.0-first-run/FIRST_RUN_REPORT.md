# Parallel Life Deep Reading v1.0 — Production-like First-Run E2E Report

**Date:** 2026-08-07  
**Model target:** `gpt-4o-mini` (from configured `OPENAI_MODEL`)  
**Implementation modified:** No  
**Prompts modified:** No  

## Executive result

**All four cases FAILED before manuscript generation.**

Root cause: configured `OPENAI_API_KEY` is a non-functional placeholder. OpenAI returned `401 AuthenticationError / invalid_api_key`. Call 1 never completed for any case; Call 2 / Call 3 / visible manuscripts were not produced.

Therefore content evaluation (factual consistency, Japanese naturalness, Residue, Observatory, Re-branch, Closing, invented scenes, generic advice, title) **could not be performed on real model output**.

---

## Runtime environment (no secrets)

| Item | Value |
|---|---|
| Key present in `kosuke-backend/.env` | yes |
| Key usable | **no** (placeholder) |
| Process env `OPENAI_API_KEY` | unset |
| Other known key locations | none found |
| OpenAI probe | `401 Incorrect API key provided` |
| Deep Reading wrapper | `DeepReadingGenerationError` (retriable; no heuristic fallback — correct) |

---

## Case-by-case results

### Case 1 — Fertility/family, retrospective counterfactual only

| Field | Result |
|---|---|
| Call 1 output | **not produced** |
| user confirmation view | not produced |
| branch classifications | not produced |
| selected Observatory Lenses / evidence gate | not produced |
| Call 2 draft | not produced |
| Call 3 final manuscript | not produced |
| Re-branch / publishability | not produced |
| unsupported scene detection | not run |
| generic advice detection | not run |
| title validation | not run |
| final validation | not run |
| final visible manuscript | not produced |
| Error stage | **Call 1 / LLM client** |
| Verdict | **FAIL** (blocked by credentials) |

### Case 2 — Same family case with explicit later discussion/decision

Same as Case 1: failed at Call 1 with auth error.  
Expected `actual_secondary_branch` could not be observed.  
**Verdict: FAIL** (blocked by credentials)

### Case 3 — First-choice university admission

Same failure mode at Call 1.  
Could not verify admission polarity / no rejection inversion.  
**Verdict: FAIL** (blocked by credentials)

### Case 4 — Creative work versus corporate career

Same failure mode at Call 1.  
Could not verify corporate-not-failure / Re-branch specificity.  
**Verdict: FAIL** (blocked by credentials)

---

## Exact problematic excerpts

None from manuscript generation. The only concrete failure text (sanitized):

> `AuthenticationError: Incorrect API key provided: your-api*****here`  
> wrapped as: `Deep Reading の生成に失敗しました。確認済み構造は保持されています。再試行してください。`

No invented-scene excerpts, generic-advice excerpts, or title excerpts exist in this run.

---

## Runtime validation decisions

| Decision | Observed |
|---|---|
| Heuristic long-form fallback used? | **No** (correct for Deep Reading) |
| Session preserved for retry messaging? | Error path raised; no confirmed structure yet because Call 1 failed before session persistence of Call1Result in failed ground() path (`session_id` null in summary) |
| Publish gate reached? | **No** |
| Lens / Re-branch / scene / advice gates | **Not exercised on live output** |

Note: unit/integration fixtures previously exercised these gates offline; this first-run was meant to validate live LLM + gates together and did not reach that point.

---

## Issue ownership

| Issue | Belongs to |
|---|---|
| 401 invalid API key / placeholder `.env` | **Environment / credentials** (not Call 1–3 logic, not runtime validation rules, not frontend rendering) |
| Inability to score manuscript quality | Consequence of above |

No Call 1 / Call 2 / Call 3 / frontend rendering defects were observable in this run.

---

## PASS / PASS WITH REVISION / FAIL summary

| Case | Rating |
|---|---|
| 1 Fertility counterfactual only | **FAIL** |
| 2 Fertility actual secondary | **FAIL** |
| 3 University admission | **FAIL** |
| 4 Creative vs corporate | **FAIL** |

Aggregate first-run content verdict: **FAIL — blocked**

---

## Release recommendation

**Do not release / do not freeze Production Candidate v1.0 based on this first-run.**

Required before re-running this report:

1. Provide a valid `OPENAI_API_KEY` in the runtime environment (not a placeholder).
2. Re-run the same four cases **without code/prompt changes**.
3. Only then evaluate PASS / PASS WITH REVISION / FAIL on manuscript quality and runtime gates.

Until a successful live first-run exists, release readiness remains **blocked on E2E evidence**, even though offline fixture/unit tests previously passed.

---

## Artifacts

Directory: `kosuke-backend/e2e_reports/deep-reading-v1.0-first-run/`

- `summary.json`
- `case*_full.json` (error + traceback only)
- this report
