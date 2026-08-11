# Parallel Life Deep Reading v1.0.1 — Deployment Readiness Report

**Date:** 2026-08-07  
**Source of truth:** `app/parallel_life_deep_reading/PRODUCTION_MANIFEST_v1.0.1.json`  
**Prior product decision:** PUBLIC RELEASE READY WITH NON-BLOCKING FOLLOW-UP — V1.0.1  
**This task:** deployment readiness only (no prompt/schema/runtime/fixture/model changes)

---

## Final deploy decision

# DEPLOY READY WITH NON-BLOCKING OPERATIONS FOLLOW-UP — V1.0.1

Safety blockers (06/08/09/10) pass. Backend **237** tests pass. Frontend lint/build pass. Happy-path API flow publishes. Frozen four-case suite is **mostly green but title-gate stochastic** on university Case3 — monitor and retry; do not treat as a new v1.0.1 safety regression.

---

## 1. Manifest verification

| Check | Result |
|-------|--------|
| Active production source | `PRODUCTION_MANIFEST_v1.0.1.json` |
| Label | Parallel Life Deep Reading Production v1.0.1 |
| Runtime in manifest | `parallel-life-runtime-v1.0.5` |
| Runtime in code (`SCHEMA_VERSION`) | `parallel-life-runtime-v1.0.5` — **match** |
| Frozen v1.0 manifest | **Untouched** — still `PRODUCTION V1.0 / FROZEN`, runtime `v1.0.4` |
| Prompts in v1.0.1 | Call1 `v1.0.2`, Call2/3 `v1.0.3` — **unchanged** |
| Models in v1.0.1 | Call1 `gpt-4o-mini`, Call2/3 `gpt-5.6-terra` |

---

## 2. Model verification

| Call | Expected | Live pin |
|------|----------|----------|
| Call 1 | gpt-4o-mini | `CALL_1_MODEL` / env default **gpt-4o-mini** |
| Call 2 | gpt-5.6-terra | **gpt-5.6-terra** |
| Call 3 | gpt-5.6-terra | **gpt-5.6-terra** |
| Models version | parallel-life-production-models-v1.0 | **match** |

Standard + legacy Editorial routes remain separate (`/experience/parallel-life`, editorial endpoints). Deep Reading routes: 7 handlers under `/experience/parallel-life/deep-reading/*`.

---

## 3. Runtime verification

| Component | Version |
|-----------|---------|
| Runtime | `parallel-life-runtime-v1.0.5` |
| Call 1 prompt | `parallel-life-call-1-v1.0.2` |
| Call 1 schema | `parallel-life-call-1-schema-v1.0.2` |
| Call 2 prompt | `parallel-life-call-2-v1.0.3` |
| Call 3 prompt | `parallel-life-call-3-v1.0.3` |

No prompt / schema / runtime / fixture edits made during this readiness task.

---

## 4. Regression result (frozen 4)

Artifacts: `frozen4-smoke*.log`, `e2e_reports/deep-reading-production-v1.0-final/FINAL_PRODUCTION_RAW.json`, plus recovery `smoke_extra.json`.

| Run | Result |
|-----|--------|
| Deploy smoke #1 | **3/4** — Case3 `title_validation_failed` (`title_not_linked_to_central_thesis`) |
| Retry #2 | Case1 Call1 JSON parse flake; Case3 **published**; Case2/4 published |
| Retry #3 | **3/4** — Case3 title flake again |
| Targeted Case3 recovery | **published** on first attempt |
| Happy-path smoke | **published** |

**Interpretation:** factual/publication safety holds (failed titles do **not** publish). Case3 title↔thesis link is stochastic under Terra; ops should allow user retry. Not a Case 06/08/09/10 regression.

---

## 5. Blocker-case smoke result

Dir: `e2e_reports/deep-reading-v1.0.1-deploy/blocker-smoke/`

| Case | Expected | Observed |
|------|----------|----------|
| 06 | publishable; no unsupported sensitive causal thesis | **PASS** — pub=True; thesis coexistence form; no ことで+楽 / 良い選択 |
| 08 | publishable; no unrealized modality | **PASS** — pub=True; no `ことがあった`; 地方 framed as 行くことはなかった |
| 09 | safe stop; confirmation blocked | **PASS** — `needs_additional_input`; confirm=False; Call2 not reached |
| 10 | safe stop; structural ambiguity | **PASS** — `structural_ambiguity`; confirm=False |

Session isolation on blocker smoke: 4/4 unique UUIDs.

---

## 6. Backend tests

```
poetry run pytest
237 passed, 1 warning
```

Includes `tests/test_deep_reading_v101_blockers.py` and full Deep Reading / app suite.

---

## 7. Frontend tests / build

| Command | Result |
|---------|--------|
| `npm run lint` | **exit 0** (no findings) |
| `npm run build` (`tsc -b && vite build`) | **exit 0** — dist produced |
| Configured unit tests | **none** in `package.json` |

Chunk size warning only (non-blocking).

---

## 8. Error-state verification

Reviewed API (`app/main.py`) + UI (`ParallelLifePage`, `ConfirmationView`, `DiagnosticsPanel`).

| Condition | Backend | UI / user-visible |
|-----------|---------|-------------------|
| OpenAI timeout / provider failure | `DeepReadingGenerationError` → HTTP 500 with Japanese generic generation message (no stack in body) | `err.message` or `copy.errorGeneration` |
| OpenAI auth / missing key | `DeepReadingLLMRequiredError` → **503** Japanese config message | Same error surface |
| Call 1 schema failure | Session status `schema_validation_failed` | Dedicated recovery screen + retry / abort (no raw JSON) |
| Clarification required | `needs_additional_input` + questions | Amber「追加質問」block + answer CTA |
| Contradiction (Case 09) | Gate + approve raises **400** Japanese contradiction message | Questions +「確認が必要な点」; approve click may error until fixed (**see §9**) |
| Structural ambiguity (Case 10) | `structural_ambiguity` + clarifications | Same confirmation UI with questions |
| Call 2 retryable failure | GenerationError → 400/503 | Error string; regenerate/retry paths exist |
| Call 3 validation failure | `validation_failed` / incomplete | Blocking reasons shown as short labels; retry CTA |

**Must not appear (verified by code review):**

- Stack traces in HTTP `detail` (exceptions converted to short strings)
- Raw prompt text
- API keys
- Diagnostics JSON in production (`DeepReadingDiagnosticsPanel` returns `null` unless `import.meta.env.DEV`)

**Note:** FastAPI may return structured validation errors for malformed requests; client uses `err.detail` — keep request payloads well-formed from UI.

---

## 9. Safe-stop UX

| Case | Intentional? | Notes |
|------|--------------|-------|
| 09 | **Yes (backend)** | Contradiction listed; neutral clarification; thesis deferred; Call2 blocked |
| 10 | **Yes (backend)** | Structural ambiguity; ≤2 clarifications; no Residue |

**Non-blocking UX follow-up (do not redesign now):**

- 「この内容で進める」is only disabled when `current_context` empty — **not** when status is contradiction / ambiguity. User may click approve and see a Japanese error. Prefer v1.1 disable-approve-until-resolved (backlog U01).
- No dedicated “これは故障ではありません” banner; copy is understandable but could be clearer (U02).

Not release-critical crash UX.

---

## 10. Observability readiness

| Metric | Available today? | Where |
|--------|------------------|-------|
| session_id | Yes | session / API response |
| production manifest | Partial | file on disk; not always stamped on every response |
| runtime version | Yes | `model_metadata.runtime_validation_version` / session.schema_version |
| model versions | Yes | `model_metadata` call_1/2/3 |
| final status | Yes | session.status |
| confirmation reached | Yes | confirmation_timestamp / confirmed_by_user |
| clarification count | Partial | derivable; lightly set on approve path |
| validation result | Yes | call3.validation |
| retry counts | Yes | draft/edit/generation_attempt_count |
| latency | **Gap** | harness-only unless infra APM added |
| token usage | **Gap** | not persisted on session |
| estimated cost | **Gap** | not persisted on session |
| failure_category | Partial / gap | schema error in metadata; not full taxonomy |
| Observatory count | Yes | derivable from Call1 selection |
| Re-branch count | Yes | derivable |

**Do not block deploy** for gaps. Prefer infra logs (request latency, 4xx/5xx) for 48–72h. No raw manuscript logging.

---

## 11. Rollback procedure

### Target

Previous known-good: **Production v1.0**  
Manifest: `PRODUCTION_MANIFEST.json` (runtime `parallel-life-runtime-v1.0.4`)  
Image / git SHA that shipped v1.0 freeze (or revert backend package to that commit).

### Steps

1. **Stop / freeze traffic** to Deep Reading if needed (load balancer / maintenance).
2. **Redeploy previous backend artifact** (v1.0 runtime). Confirm:
   - `SCHEMA_VERSION == parallel-life-runtime-v1.0.4` **or**
   - code matches frozen v1.0 commit.
3. **Frontend:** redeploy paired frontend if API response shape differs (v1.0.1 additive fields are optional; usually forward-compatible). Prefer redeploy matched pair.
4. **Verify smoke:** Standard Parallel Life generate still works; Deep Reading ground returns; frozen Case1 smoke optional.
5. **Do not run DB migrations** — Deep Reading sessions are in-memory / request-scoped; **no migration blocks rollback**.

### Emergency Deep Reading disable (if no feature flag)

No dedicated feature flag exists today. Options:

1. Temporarily remove or 503 the seven `/experience/parallel-life/deep-reading/*` routes in a hotfix deploy, **or**
2. Hide “Read deeper” CTA in frontend while keeping Standard + Editorial endpoints live.

**Standard remains available** on `/experience/parallel-life` (+ clarify/export) independent of Deep Reading.

### Re-enable v1.0.1

Redeploy v1.0.1 artifact; confirm `PRODUCTION_MANIFEST_v1.0.1.json` runtime pin `v1.0.5`.

---

## 12. 48–72h monitoring plan

**Goal:** anomaly detection only (not optimization targets).

Watch (infra + app logs):

| Signal | Watch for |
|--------|-----------|
| API error rate (5xx / 503) | Spike vs baseline |
| Schema failure rate (`schema_validation_failed`) | Sudden jump |
| Contradiction safe-stop rate (Case09-like 400 on approve / needs_additional_input) | Unexpected volume |
| Structural ambiguity rate | Unexpected volume |
| Clarification rate | Volume / drop-offs |
| Publication rate (status=complete) | Collapse |
| Validation failure rate (title / residue / modality) | Case3-like title flake cluster |
| Retry rate | Sustained elevation |
| Avg + p95 latency (ground / draft / edit) | Provider degradation |
| Avg cost / completed Deep Reading | Outlier spend |

**Cadence:** check at +2h, +12h, +24h, +48h, +72h.  
**Rollback trigger examples:** sustained 5xx, auth/config 503, or publication rate ~0 with high draft attempts.

---

## 13. v1.1 backlog

Recorded at:

`e2e_reports/deep-reading-v1.1-backlog/V1.1_BACKLOG.md`

Includes Case 02/03/04/05/07 items, current_context preservation, richer contradiction UI, broader telemetry. **Not implemented in this task.**

---

## 14. Final deploy decision

# DEPLOY READY WITH NON-BLOCKING OPERATIONS FOLLOW-UP — V1.0.1

### Non-blocking ops follow-ups

1. Monitor Case3 / university **title↔thesis** flake; user retry is safe (non-publish).
2. Prefer disabling approve when contradiction / structural_ambiguity (v1.1 UX).
3. Add APM latency + optional token/cost session fields without manuscript logging.
4. Consider emergency Deep Reading route kill-switch feature flag.

### Deploy checklist (ops)

- [ ] Backend image includes `SCHEMA_VERSION=parallel-life-runtime-v1.0.5`
- [ ] `OPENAI_API_KEY` set; Call2/3 can reach `gpt-5.6-terra`
- [ ] Frontend production build deployed (diagnostics panel hidden)
- [ ] Smoke: Standard generate OK
- [ ] Smoke: Deep Reading happy-path once in real UI
- [ ] Rollback artifact (v1.0) pinned and accessible
- [ ] On-call watching 48–72h signals above
