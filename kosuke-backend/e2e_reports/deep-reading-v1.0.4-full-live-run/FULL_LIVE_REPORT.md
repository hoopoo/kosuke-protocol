# Deep Reading Production Candidate v1.0.4 — Full Live Report

**Date:** 2026-08-07  
**Goal:** Remove awkward meta-constructions and unsupported causal framing (no architecture redesign; Call 1 frozen).

## Versions

| Component | Version |
|-----------|---------|
| Call 1 | `parallel-life-call-1-v1.0.2` (unchanged) |
| Call 1 schema | `parallel-life-call-1-schema-v1.0.2` (unchanged) |
| Call 2 | `parallel-life-call-2-v1.0.3` |
| Call 3 | `parallel-life-call-3-v1.0.3` |
| Runtime | `parallel-life-runtime-v1.0.4` |

## Unit tests

`test_deep_reading_v104_language.py` A–E (+ variants): **passed**  
Related Deep Reading suites: green with v1.0.4 version pins.

---

## Completion report

### 1. `unsupported_causal_frame`

Runtime category that blocks causal *presupposition*, including interrogatives:

- 「どのように影響を与えているのか / 影響しているのか」
- 「どのように関わっているのか」
- related frames (つなが / 形づく / 作用 / 関わ)

Also blocks evaluative meaning-completion such as 「大切な意味を持っている」「一層深める」 when unsupported.

**Rule:** do not “repair” a causal assertion by turning it into a causal question. Prefer coexistence / comparison / “結びつける材料はない”.

### 2. Title causal-frame validation

Titles containing 影響 / 原点 / きっかけ / 形成 / つながり / 決定 / 変えた / 生んだ / 残した fail unless explicit causal evidence exists in grounded corpus.

`title_causal_frame_violation` is a first-class TitleValidation field and a publication blocker. `_pick_title` skips such candidates.

### 3. `schema_leakage_prose`

Detects schema verbalization such as:

- 「この選択は、実際に選んだのは…」
- 「実際に選んだのは…」
- 「選ばなかった道として…」
- 「この分岐では…」「入力によれば…」「事実としては…」

Deterministic `repair_schema_leakage_prose` + excerpt removal; Call 3 language pass rewrites to direct narrative.

### 4. Call 2 changes (v1.0.3)

- Ban schema-leakage meta phrasing; prefer direct narrative.
- Ban causal-frame questions as a substitute for causal assertions.
- Title guidance: avoid unsupported causal-frame tokens.
- Keep present_anchor feelings/facts and Residue structure.

### 5. Call 3 final language pass (v1.0.3)

After factual rewrite/finalize, an additional language pass removes system-like scaffolding without adding content when leakage / causal-frame markers remain.

### 6. Test results

| Test | Result |
|------|--------|
| A causal frame | pass |
| B title 「早稲田進学が残した影響」 | pass (rejected) |
| C schema leakage | pass |
| D direct narrative | pass |
| E qualified comparison | pass |

---

## 7–8. Case 2 / Case 3 (targeted first runs)

Isolation runs (`ONLY_CASES=case2,case3`) reached:

- Case2: direct narrative, no schema leakage, feelings + discussion retained, Residue present → **pass bar met** in that snapshot.
- Case3: no 「影響」 title, no causal-frame question after detector tighten → **pass bar met** in that snapshot.

### 9. Exact remaining excerpts (final all-four run)

Final all-four rerun reintroduced soft overreach (LLM variance). Runtime counters stayed 0; manual review still finds:

**Case1**
- 「これらの要素は、私の現在の生活の中で大きな役割を果たしている。」
- 「45歳のときの選択が、今の私の生活にどのように結びついているのかを考えると…」

**Case2**
- 「この出来事は、私の人生において大きな転機となった。」
- Residue / 「やめた」 closing thinner than isolation run.

**Case3**
- 「学問に対する情熱を具現化した瞬間」
- 「大学生活のスタートを切る重要な出来事」
- 「大学選択がその後の人生に与える可能性については感じている。」

**Case4**
- 「過去の選択と密接に関連している。」
- 「創作に対する思いが強くなる瞬間がある。」
- 「構造的なつながりを感じることがある。」

---

## 10. All-four final rerun

| Case | Publish | Runtime unsupported_* | Manual fidelity | Naturalness | Continuity |
|------|---------|----------------------|-----------------|-------------|------------|
| 1 | Yes | all 0 | **8**/10 | 7 | 8 |
| 2 | Yes | all 0 | **8**/10 | 8 | 7 |
| 3 | Yes | all 0 | **7**/10 | 7 | 8 |
| 4 | Yes | all 0 | **7**/10 | 7 | 8 |

Runtime publication: **4/4 Yes**  
PASS bar (fidelity 10 + naturalness≥8 + continuity≥8 on all four): **FAIL**

### 11. Freeze recommendation

**Do not freeze Production Candidate v1.0.4.**

Why:

1. Targeted Case2/3 isolation quality met the narrow bar, but the final all-four live rerun did not hold fidelity 10 / naturalness≥8 across all cases.
2. Remaining failures are still “plausible meaning completion” and meta evaluation (転機 / 情熱 / 関連 / つながり), some of which are not yet covered by deterministic patterns.
3. Gates were not loosened; runtime publishability alone is insufficient while manual fidelity lags.

**What landed successfully in v1.0.4**
- Causal-frame category (questions that presuppose influence)
- Title causal-frame rejection (e.g. 「影響」)
- Schema-leakage detection + rewrite path
- Call2/3 prompt constraints + Call3 language pass
- Unit tests A–E green

**Suggested next narrow step (if continuing):** expand detectors for 「結びついているのか」「密接に関連」「情熱を具現化」「大きな転機／役割」, and require Residue sentence presence as a hard publish check rather than soft token overlap.
