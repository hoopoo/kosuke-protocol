# Parallel Life Deep Reading v1.1.0-rc1 — RC Freeze Report

Generated: `2026-08-08T19:30:00+00:00`  
Freeze mode: **no editorial retune / no prompt tune / no gate loosen / Context Pack stays OFF in production**

## Final decision

```
RC FROZEN — CONTEXTUAL BETA NOT PUBLIC
```

---

## 1. Immutable RC manifest

| Item | Value |
|------|-------|
| Manifest | `kosuke-backend/app/parallel_life_deep_reading/PRODUCTION_MANIFEST_v1.1.0-rc1.json` |
| Product | `Parallel Life Deep Reading v1.1.0-rc1` |
| Status | `RELEASE CANDIDATE — CONTEXTUAL BETA NOT PUBLIC` |
| Production manifests untouched | `PRODUCTION_MANIFEST.json`, `PRODUCTION_MANIFEST_v1.0.2.json` (**not modified**) |

### Approved RC pins (code + manifest)

| Surface | Pin |
|---------|-----|
| Call 1 (Contextual) | `parallel-life-call-1-v1.1.9` |
| Call 2 (Contextual) | `parallel-life-call-2-v1.1.11` |
| Call 3 (Contextual) | `parallel-life-call-3-v1.1.11` |
| Runtime (Contextual) | `parallel-life-runtime-v1.1.11` |
| Call 1 / Runtime (Strict / production path) | `parallel-life-call-1-v1.0.3` / `parallel-life-runtime-v1.0.6` |
| Models | Call1 `gpt-4o-mini` · Call2/3 `gpt-5.6-terra` (`parallel-life-production-models-v1.0`) |

Historical `*-exp` constants remain for A/B labels; **active** Contextual pins drop the `-exp` suffix for RC freeze labeling only. Editorial / gate behavior is unchanged from v1.1.11-exp Track A+B.

---

## 2. Production feature flags

| Flag | Production | Staging |
|------|------------|---------|
| `DEEP_READING_ENABLED` | `true` | `true` |
| `DEEP_READING_CONTEXT_PACK_ENABLED` | **`false`** | `true` (flag-gated beta only) |
| Contextual Mode public | **OFF** (FE only opens mode-ask when `context_pack_enabled`) | staging-only |
| Strict Mode | unchanged default | unchanged |

Verification:

- Wrangler production vars: `DEEP_READING_CONTEXT_PACK_ENABLED = "false"` (`cloudflare/api-container/wrangler.toml`)
- Default Python env (flag unset): `context_pack_feature_enabled() == False`
- Live probe:
  - Production `.../deep-reading/enabled` → `{"enabled":true}` (no pack field on current prod deploy; FE defaults `contextPackEnabled=false`)
  - Staging → `{"enabled":true,"context_pack_enabled":true}`

**Contextual beta is not production-public.**

Staging hygiene: removed leftover `FORCE_CONTAINER_RESTART` from staging wrangler vars (no behavior change).

---

## 3. User-facing error sanitization (UX only)

Gates / blocking_reasons payloads are unchanged.

Frontend mapping added in `confirmationUx.ts` (`humanizeBlockingReason` / `formatBlockingReasons`):

- Never displays: `required_section_unrealized:*`, `semantic_domain_leak`, `title_validation_failed`, `thesis_closure_missing:*`, or other snake_case/internal identifiers
- Default copy: 「この内容では、まだ十分な読み取り結果を作れませんでした。」
- Optional clarification in normal Japanese (e.g. いまも残る問い / 選んだ道 / 分かれ目)

Unit test: `kosuke-frontend/.../confirmationUx.test.ts` — **passed**

DEV-only `DeepReadingDiagnosticsPanel` may still show raw codes (not production UI).

---

## 4. Known defect backlog (recorded, not patched)

Targeted **v1.1.x** work — do not chase 10/10 publishability:

| ID | Case | Issue |
|----|------|-------|
| `ent-residue` | entrepreneurship | Residue realization intermittent (`required_section_unrealized:residue`) |
| `place-chosen-lost` | zero_lens | Chosen Path / Lost underrealization |
| `sensitive-branch-point` | sensitive | Branch Point underrealization |
| `creative-chosen-depth` | creative | Shallow Chosen Path quality (publishable but thin) |

Source classification: `RELEASE_CANDIDATE_READINESS_REPORT.md` (A×6 / C×3 / D×1).

---

## 5. Observatory status (accurate)

| Claim | Status |
|-------|--------|
| Observatory-Core architecture | **exists** |
| Candidate lenses generated | **yes** (in Contextual Call1 path) |
| Current QA selected lenses | **0** (v1.1.11 Public QA) |
| Public Observatory section frequency in RC QA | **0** |
| Observatory Evidence expansion | **v1.2 backlog** |

Do **not** claim production Observatory depth that QA has not demonstrated.

---

## 6. Final RC verification (deterministic only)

### Pytest (local)

```
74 passed in 0.39s
```

Suites:

- `test_deep_reading_v1110_deterministic_realization.py`
- `test_deep_reading_v1111_targeted_editorial.py`
- `test_deep_reading_v11_context_pack.py`
- `test_deep_reading_v111_selection_compression.py`
- `test_deep_reading_v119_branch_authority.py`
- `test_deep_reading_v118_branch_semantics.py`
- `test_deep_reading_runtime.py`
- `test_deep_reading_v101_blockers.py`

Plus FE: `confirmationUx.test.ts` — all assertions passed.

### Frozen QA artifacts (v1.1.11 Public QA — behavior baseline)

From `PUBLIC_QA_V1111_RAW.json` / Track B report:

| Check | Result |
|-------|--------|
| hard safety failures | **0** |
| semantic domain leak | **0** |
| clarification loop / dead-end | **0** (Track A exit path frozen) |
| validator FN regression (Track A) | **0** (`track_a_regression_cases=0`) |
| label mutation | **0** (locked labels / restore path frozen) |
| production Strict behavior | **unchanged** (v1.0.2 manifest + Strict prompts untouched) |
| Context Pack production | **OFF** |

No live 10-case re-QA in this freeze (per instruction: deterministic regression only).

---

## 7. Freeze scope notes

- **In scope:** RC manifest, pin label freeze, production flag confirmation, UX sanitization, backlog/Observatory documentation, deterministic regression, this report
- **Out of scope / not done:** prompt/editorial retune, gate loosening, Context Pack production enablement, production deploy, full live re-QA, automatic defect patches
- Staging live containers may still advertise prior `*-exp` pin strings until a voluntary staging redeploy; **code constants and RC manifest are frozen to the approved non-`exp` pins**

---

## References

- `PRODUCTION_MANIFEST_v1.1.0-rc1.json`
- `e2e_reports/deep-reading-v1.1-release/RELEASE_CANDIDATE_READINESS_REPORT.md`
- `e2e_reports/deep-reading-v1.1-public-qa/TARGETED_EDITORIAL_V1111_REPORT.md`
- `e2e_reports/deep-reading-v1.1-public-qa/DETERMINISTIC_REALIZATION_V1110_REPORT.md`
- `e2e_reports/deep-reading-v1.1-public-qa/PUBLIC_QA_V1111_RAW.json`
