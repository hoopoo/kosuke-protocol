# Deep Reading Model Isolation A/B Report

**Date:** 2026-08-07  
**Purpose:** Determine whether remaining fidelity / Japanese-naturalness gaps are primarily model capability vs prompt architecture.  
**Controls:** Call 1/2/3 prompts, runtime validation, schemas, fixtures, publication gates, frontend — **unchanged**.  
**Call 1:** Frozen confirmed payloads from `e2e_reports/deep-reading-v1.0.4-full-live-run/*/call1.json` (same for all configs).  
**Artifacts:** `e2e_reports/deep-reading-model-ab/` (`MODEL_AB_RAW.json`, per-config bodies).

## Model matrix

| Config | Call 2 | Call 3 |
|--------|--------|--------|
| A Baseline | `gpt-4o-mini` | `gpt-4o-mini` |
| B Balanced | `gpt-5.6-terra` | `gpt-5.6-terra` |
| C Editorial | `gpt-5.6-terra` | `gpt-5.6-sol` |
| D Maximum | `gpt-5.6-sol` | `gpt-5.6-sol` |

Pass bar: fidelity **10**, naturalness **≥8**, continuity **≥8**, runtime blocking **0**.

---

## Aggregate cost / latency / tokens

Estimated USD uses approximate short-context list prices  
(`4o-mini` $0.15/$0.60, Terra $2.50/$15, Sol $5/$25 per 1M in/out).  
Latency is wall-clock Call2+Call3 per case, averaged.

| Config | Total est. cost (4 cases) | Avg latency / case | Prompt tokens | Completion tokens | Runtime publish |
|--------|---------------------------:|-------------------:|--------------:|------------------:|-----------------|
| A Baseline | **$0.0067** | **10.8s** | 29,906 | 3,749 | 4/4 |
| B Terra/Terra | **$0.139** (~21×) | **12.9s** | 21,894 | 5,612 | 4/4 |
| C Terra/Sol | **$0.282** (~42×) | **28.8s** | 25,226 | 9,118 | 3/4 |
| D Sol/Sol | **$0.413** (~61×) | **42.8s** | 22,153 | 12,099 | 4/4 |

---

## 1. Baseline (A) — gpt-4o-mini / gpt-4o-mini

| Case | Fid | Nat | Cont | Spec | Residue | Closing | Title | Runtime block | Pass bar |
|------|----:|----:|-----:|-----:|--------:|--------:|------:|---------------|----------|
| 1 | 8 | 7 | 8 | 7 | 8 | 7 | 8 | 0 | No |
| 2 | 7 | 7 | 7 | 7 | 7 | 7 | 7 | 0 | No |
| 3 | 6 | 7 | 7 | 6 | 7 | 6 | 7 | 0 | No |
| 4 | 9 | 8 | 8 | 7 | 8 | 8 | 8 | 0 | Near |

**Pattern:** Runtime clean, but manuscripts still invent evaluative/causal bridges.

### Problematic excerpts (A)

- Case1: 「選択の重みを感じさせるものである」
- Case2: 「大きな転機となった」「密接に結びついている」「家族がどのように形成されてきた」「息子との時間を大切にしながら」
- Case3: 「新しい学びや人との出会いを経験することができた」「早稲田大学での学びが私の基盤となっている」「理解を深めている」
- Case4: mostly restrained; short but acceptable

---

## 2. Terra / Terra (B)

| Case | Fid | Nat | Cont | Spec | Residue | Closing | Title | Runtime block | Pass bar |
|------|----:|----:|-----:|-----:|--------:|--------:|------:|---------------|----------|
| 1 | **10** | **9** | **9** | 9 | **10** | 9 | 9 | 0 | **Yes** |
| 2 | **10** | **9** | **9** | 9 | **10** | 9 | 9 | 0 | **Yes** |
| 3 | **9** | **8** | **9** | 9 | 9 | 9 | 8 | 0 | Near (fid 9) |
| 4 | **10** | **9** | **9** | 9 | **10** | 9 | 9 | 0 | **Yes** |

**Pattern:** Largest quality jump. Coexistence / “材料はない” / Residue are natural. Little invented biography.

### Residual issues (B)

- Case3: 「別の大学へ進学することがあった。」 — tense/modality slip (sounds realized). Prefer 「別の大学へ進む道もあった」.
- Soft watch token 「結びつ」 appears only inside allowed 「結びつける材料はない」 (grounded non-causal use).

---

## 3. Terra / Sol (C)

| Case | Fid | Nat | Cont | Spec | Residue | Closing | Title | Runtime block | Pass bar |
|------|----:|----:|-----:|-----:|--------:|--------:|------:|---------------|----------|
| 1 | **10** | **9** | **9** | 9 | 9 | 9 | 9 | 0 | **Yes** |
| 2 | **10** | **8** | **8** | 9 | **10** | 9 | 9 | 0 | **Yes** |
| 3 | **10** | **8** | **8** | 9 | 9 | 9 | 8* | **title_validation_failed** | No (runtime) |
| 4 | **10** | **9** | **9** | 9 | **10** | 9 | 8 | 0 | **Yes** |

\*Title `19歳の合格と、文章やプロトコルをまとめる現在` is factually good; failed only `title_not_linked_to_central_thesis` (Call1 thesis token match), not causal-frame.

**Pattern:** Call3 Sol improves polish and disclaimer precision. Section headings appear more often (slight “chapter” feel → naturalness 8). Case3 body is strong but not publishable under current title gate.

---

## 4. Sol / Sol (D)

| Case | Fid | Nat | Cont | Spec | Residue | Closing | Title | Runtime block | Pass bar |
|------|----:|----:|-----:|-----:|--------:|--------:|------:|---------------|----------|
| 1 | **10** | **8** | **9** | 9 | 9 | 9 | 9 | 0 | **Yes** |
| 2 | **10** | **9** | **9** | 9 | **10** | **10** | 9 | 0 | **Yes** |
| 3 | **10** | **9** | **9** | 9 | **10** | 9 | 9 | 0 | **Yes** |
| 4 | **10** | **9** | **9** | 9 | **10** | 9 | 9 | 0 | **Yes** |

**Pattern:** Best overall editorial control. Explicitly refuses unsupported intervening biography (“ここにある事実だけではたどれない”). Cost/latency highest.

---

## 5. Per-case quality comparison (fidelity / naturalness / continuity)

| Case | A | B | C | D |
|------|---|---|---|---|
| 1 | 8/7/8 | **10/9/9** | **10/9/9** | **10/8/9** |
| 2 | 7/7/7 | **10/9/9** | **10/8/8** | **10/9/9** |
| 3 | 6/7/7 | 9/8/9 | 10/8/8* | **10/9/9** |
| 4 | 9/8/8 | **10/9/9** | **10/9/9** | **10/9/9** |

\*C3 not runtime-publishable (title thesis link).

---

## 6. Exact problematic excerpts (cross-config highlights)

### Baseline-only inventions (absent or fixed in B/C/D)

- 「大きな転機となった」
- 「密接に結びついている」
- 「新しい学びや人との出会いを経験」
- 「早稲田大学での学びが私の基盤」
- 「選択の重みを感じさせる」

### Remaining soft issues even on strong models

- B3: 「別の大学へ進学することがあった」
- C/D: occasional `##` section headings (continuity OK, slightly report-like)
- C3: title gate false negative vs editorial quality (`title_not_linked_to_central_thesis`)

---

## 7. Quality delta from baseline

| Metric | A → B | A → C | A → D |
|--------|-------|-------|-------|
| Mean fidelity | +2.25 | +2.5* | +2.5 |
| Mean naturalness | +1.75 | +1.5* | +1.75 |
| Mean continuity | +1.5 | +1.25* | +1.75 |
| Cases meeting pass bar | 0 → **3** | 0 → **3** (+1 body-strong/runtime-fail) | 0 → **4** |
| Unsupported meaning completion | frequent → rare | rare | rare |

\*Ignoring C3 as non-publishable for mean, or counting body-only scores.

**Conclusion:** The gap is **primarily model capability**. Same prompts/gates produce fidelity-10 manuscripts once Call2/Call3 move off `gpt-4o-mini`.

---

## 8. Cost delta (4-case bundle vs A)

| Config | Est. cost | Δ vs A |
|--------|----------:|-------:|
| A | $0.0067 | — |
| B | $0.139 | **+$0.132** (~21×) |
| C | $0.282 | **+$0.275** (~42×) |
| D | $0.413 | **+$0.406** (~61×) |

---

## 9. Latency delta (avg wall / case vs A)

| Config | Avg latency | Δ vs A |
|--------|------------:|-------:|
| A | 10.8s | — |
| B | 12.9s | **+2.1s** (~1.2×) |
| C | 28.8s | **+18.0s** (~2.7×) |
| D | 42.8s | **+32.0s** (~4.0×) |

Terra/Terra is nearly latency-neutral vs mini while vastly better quality. Sol in Call3 or both drives latency up sharply.

---

## 10. Best configuration

**Best quality:** D Sol/Sol (4/4 pass bar).  
**Best quality/cost/latency tradeoff:** **B Terra/Terra** (3/4 hard pass; case3 at fidelity 9 from a single modality slip).  
**Best editorial polish without full Sol draft cost:** C Terra/Sol — but title-gate brittleness on case3 currently hurts publish rate.

---

## 11. Are prompt changes still necessary?

**Not as the primary lever.** Prompt architecture already forces runtime 0-block on mini; quality shortfall is meaning-completion under mini.

Still useful *secondary* prompt/runtime polish (not required to prove the model thesis):

1. Prefer 「道もあった」 over 「進学することがあった」
2. Discourage `##` mini-chapters if continuous essay is preferred
3. Soften title↔thesis token match so fact-true titles like C3 are not rejected

These are small; they are not what created the 7–8 fidelity ceiling on mini.

---

## 12. Recommended production model split

**Recommended default:**

| Stage | Model | Rationale |
|-------|-------|-----------|
| Call 1 | keep current (`gpt-4o-mini` or existing) | Not under test; grounding already usable |
| Call 2 | **`gpt-5.6-terra`** | Main fidelity/naturalness leap; cost moderate; latency near baseline |
| Call 3 | **`gpt-5.6-terra`** (default) or **`gpt-5.6-sol`** if editorial polish is prioritized | Terra/Terra already meets bar on 3/4; Sol Call3 helps polish but adds cost/latency and title-gate risk |

Escalate to Sol/Sol only for premium tiers or failed Terra retries.

---

## 13. Freeze recommendation

**Do not freeze production configuration yet.**

Freeze production *model split* only after:

1. Switch Call2/Call3 to Terra (or chosen split) in config — without further prompt redesign  
2. Re-run the same four frozen Call1 cases once on the chosen split  
3. Confirm 4/4 meet fidelity 10 / naturalness≥8 / continuity≥8 with runtime blockers 0  

On this A/B evidence, **Terra/Terra is the freeze candidate**; Sol/Sol is the quality ceiling reference.

**Production prompts/gates should remain frozen during that confirmation run** — this report shows the remaining gap is model-dominated, not prompt-dominated.
