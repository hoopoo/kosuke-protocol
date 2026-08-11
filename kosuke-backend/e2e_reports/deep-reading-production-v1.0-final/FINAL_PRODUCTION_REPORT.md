# Parallel Life Deep Reading — Final Production Confirmation

**Date:** 2026-08-07  
**Purpose:** Final production confirmation under the intended deployment model split (not an optimization cycle).  
**Artifacts:** `FINAL_PRODUCTION_RAW.json`, `case1/`–`case4/`,  
`app/parallel_life_deep_reading/PRODUCTION_MANIFEST.json`

## Freeze decision

# PRODUCTION V1.0 / FROZEN

All four regression cases met the final pass bar under production prompts, runtime validation, and the production model split.

---

## 1. Production model configuration

| Call | Model | Notes |
|------|-------|-------|
| Call 1 | `gpt-4o-mini` (stable / `OPENAI_MODEL`) | Unchanged stable configuration |
| Call 2 | `gpt-5.6-terra` | Production pin |
| Call 3 | `gpt-5.6-terra` | Production pin |

- **Models version:** `parallel-life-production-models-v1.0`
- Standard mode models: **not changed**
- Legacy Editorial: **not changed**
- Per-session metadata records Call 1/2/3 models, prompt versions, and runtime validation version

---

## 2. Prompt versions

| Component | Version | Changed this run? |
|-----------|---------|-------------------|
| Call 1 prompt | `parallel-life-call-1-v1.0.2` | No |
| Call 1 schema | `parallel-life-call-1-schema-v1.0.2` | No |
| Call 2 prompt | `parallel-life-call-2-v1.0.3` | No |
| Call 3 prompt | `parallel-life-call-3-v1.0.3` | No |

---

## 3. Runtime version

| Component | Version | Changed this run? |
|-----------|---------|-------------------|
| Runtime validation | `parallel-life-runtime-v1.0.4` | No |
| Fixtures | `deep-reading-fixtures-v1.0` (four regression cases) | Content unmodified |
| Publication gates / UI | — | Unchanged |

---

## 4. Case 1 result — Fertility / family (retrospective counterfactual only)

| Field | Result |
|-------|--------|
| Publishable | **Yes** |
| Title | 三人で暮らす現在、残る問い |
| Title validation | passed (`title_supported_by_central_thesis=true`, no causal-frame violation) |
| Residue | validated + represented in manuscript |
| Observatory | omitted (evidence-gated) |
| Re-branch | omitted |
| Runtime blockers | none |

Body keeps the three-person present life, company management, affection facts, and the second-child question as an open present question without inventing intervening biography.

---

## 5. Case 2 result — Fertility / family (explicit later discussion and decision)

| Field | Result |
|-------|--------|
| Publishable | **Yes** |
| Title | 三人で暮らす家の、答えのない問い |
| Title validation | passed |
| Residue | validated + represented |
| Observatory | omitted |
| Re-branch | omitted |
| Runtime blockers | none |
| Decision retention | 話し合 / やめた retained |

Distinguishes the later treatment discussion/decision from Case 1’s question-only structure. Section headings are present (mild essay feel) but do not invent facts.

---

## 6. Case 3 result — First-choice Waseda admission (**title focus**)

| Field | Result |
|-------|--------|
| Publishable | **Yes** |
| Title | 別の大学を考える現在 |
| Title validation | **passed** |
| Thesis link | `title_supported_by_central_thesis=true` |
| Causal-frame title | **false** (no unsupported 影響 / 原点 / きっかけ framing) |
| Residue | validated + represented |
| Observatory | omitted |
| Re-branch | omitted |
| Runtime blockers | none |

Prior Terra/Sol failure mode `title_not_linked_to_central_thesis` did **not** recur. Title is supported by the manuscript and linked to the central thesis without unsupported impact/origin framing. Body refuses alternate-university outcome invention.

---

## 7. Case 4 result — Creative work vs corporate career

| Field | Result |
|-------|--------|
| Publishable | **Yes** |
| Title | 制作の現在と、創作中心の人生という問い |
| Title validation | passed |
| Residue | validated + represented |
| Observatory | omitted |
| Re-branch | omitted |
| Runtime blockers | none |

Corporate past and present making (観測サイト / 文章 / プロトコル) coexist with the creative-life question; no invented creative biography.

---

## 8. Fidelity scores (manual)

| Case | Fidelity | Notes |
|------|---------:|-------|
| 1 | **10/10** | All claims map to grounded facts / confirmed question |
| 2 | **10/10** | Decision fact retained; no invented second-child life |
| 3 | **10/10** | Admission + unchosen path + present work; CF outcomes refused |
| 4 | **10/10** | Corporate / making / creative question bounded |

---

## 9. Naturalness scores (manual)

| Case | Naturalness | Notes |
|------|------------:|-------|
| 1 | **9/10** | Direct narrative; light structural repetition |
| 2 | **8/10** | Readable; section headings slightly essay-like |
| 3 | **8/10** | Compact; minor unrealized-path modality stiffness |
| 4 | **9/10** | Controlled coexistence language |

Pass bar: **≥ 8/10** — all pass.

---

## 10. Continuity scores (manual)

| Case | Continuity |
|------|-----------:|
| 1 | **9/10** |
| 2 | **8/10** |
| 3 | **9/10** |
| 4 | **9/10** |

Pass bar: **≥ 8/10** — all pass.

---

## 11. Runtime violations

All cases: **0** for every required counter.

| Counter | C1 | C2 | C3 | C4 |
|---------|---:|---:|---:|---:|
| unsupported_personal_detail | 0 | 0 | 0 | 0 |
| unsupported_scene | 0 | 0 | 0 | 0 |
| unsupported_causality | 0 | 0 | 0 | 0 |
| unsupported_causal_frame | 0 | 0 | 0 | 0 |
| unsupported_affect | 0 | 0 | 0 | 0 |
| unsupported_role_behavior | 0 | 0 | 0 | 0 |
| contradiction | 0 | 0 | 0 | 0 |
| fact polarity inversion | 0 | 0 | 0 | 0 |
| schema_leakage_prose | 0 | 0 | 0 | 0 |
| sentence_fragments | 0 | 0 | 0 | 0 |
| generic advice published | 0 | 0 | 0 | 0 |

Independent re-scan of final bodies matched gate counts (all zero). Soft-watch token hits: none that formed unsupported causal claims.

---

## 12. Title validation

| Case | Title | Thesis-linked | Causal-frame violation | Passed |
|------|-------|:-------------:|:----------------------:|:------:|
| 1 | 三人で暮らす現在、残る問い | yes | no | **yes** |
| 2 | 三人で暮らす家の、答えのない問い | yes | no | **yes** |
| 3 | 別の大学を考える現在 | yes | no | **yes** |
| 4 | 制作の現在と、創作中心の人生という問い | yes | no | **yes** |

Case 3 specifically: title is factually valid, manuscript-supported, thesis-linked, and free of unsupported impact/influence/origin framing.

---

## 13. Cost (informational)

Estimated USD (approx. list prices: 4o-mini $0.15/$0.60, Terra $2.50/$15 per 1M in/out).

| Metric | Value |
|--------|------:|
| **Total cost (4 cases)** | **$0.116** |
| Case 1 | $0.023 |
| Case 2 | $0.030 |
| Case 3 | $0.040 |
| Case 4 | $0.023 |

| Tokens | In | Out | Total |
|--------|---:|----:|------:|
| Call 2 (all cases) | 14,563 | 3,581 | **18,144** |
| Call 3 (model calls) | 3,565 | 742 | **4,307** |

Note: Call 3’s LLM rewrite/language pass is **issue-triggered** in production code. In this run, Cases 1/2/4 Call2 drafts already cleared the gate (Call 3 still ran title selection + deterministic finalize); Case 3 incurred the Terra Call 3 model rewrite. This is production behavior, not a test bypass.

---

## 14. Latency (informational)

Wall-clock Call1→confirm→Call2→Call3 per case.

| Metric | ms |
|--------|---:|
| Case 1 | 32,599 |
| Case 2 | 30,456 |
| Case 3 | 31,829 |
| Case 4 | 22,026 |
| **Average** | **29,227** |
| **p50** | **31,142** |
| **p95** | **31,829** |

No latency optimization performed (quality-first rule).

---

## 15. Remaining risks

1. **Stochastic variance:** Terra outputs can vary across re-runs; freeze pins versions, not a single sample forever. Re-run the four fixtures before any silent drift acceptance.
2. **Call 1 thesis wording:** Case 3 Call 1 still produced a thesis containing 「影響」「重要」; manuscript/title correctly avoided publishing unsupported causal framing. Call 1 remains frozen — do not reopen unless a v1.0.x/v1.1 change is intentional.
3. **Call 3 model skip path:** When Call 2 is already publishable, Call 3 may not invoke the LLM. Title selection remains deterministic/runtime-gated; monitor if future Call 2 drafts pass gate while Japanese polish would still benefit from a language pass.
4. **Unrealized-path modality:** Occasional 「選ばなかった道には…ことがあった」 stiffness can appear; currently within naturalness ≥8 and not treated as invented biography.
5. **Cost:** ~$0.12 / four-case suite at Terra/Terra is acceptable for Deep Reading; not optimized further in this freeze.

---

## 16. Freeze decision (detail)

**Status: PRODUCTION V1.0 / FROZEN**

Frozen components (do not silently modify):

| Component | Frozen version |
|-----------|----------------|
| Call 1 prompt | `parallel-life-call-1-v1.0.2` |
| Call 1 schema | `parallel-life-call-1-schema-v1.0.2` |
| Call 2 prompt | `parallel-life-call-2-v1.0.3` |
| Call 3 prompt | `parallel-life-call-3-v1.0.3` |
| Runtime validation | `parallel-life-runtime-v1.0.4` |
| Production model split | `parallel-life-production-models-v1.0` (Call1 stable / Call2 Terra / Call3 Terra) |
| Four regression fixtures | case1 retrospective; case1+decision; Waseda; creative vs corporate |

Manifest: `app/parallel_life_deep_reading/PRODUCTION_MANIFEST.json`

Future changes **must** use `v1.0.x` or `v1.1`.
