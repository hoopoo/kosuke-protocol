# Parallel Life Deep Reading v1.0.1 — Full Live E2E Report

**Date:** 2026-08-07  
**Model:** `gpt-4o-mini` (configured `OPENAI_MODEL`)  
**Auth:** live `OPENAI_API_KEY` succeeded  
**Call 1:** frozen `parallel-life-call-1-v1.0.1` / schema `parallel-life-call-1-schema-v1.0.1`  
**Call 2 / Call 3:** frozen `parallel-life-call-2-v1.0` / `parallel-life-call-3-v1.0`  
**Prompts modified during this run:** No  
**Code / Call 1 modified during this run:** No  

Artifacts: `e2e_reports/deep-reading-v1.0.1-full-live-run/`  
Machine dump: `FULL_LIVE_RAW.json`

---

## Executive result

| Case | Pipeline reached Call 3 | Runtime publishable | Verdict |
|---|---|---|---|
| 1 Fertility / counterfactual only | Yes | **No** (`residue_centrality_failed`) | **FAIL** |
| 2 Fertility / later discussion+decision | Yes | **No** (`residue_centrality_failed`) | **FAIL** |
| 3 University first-choice | Yes | **No** (`residue_centrality_failed`) | **FAIL** |
| 4 Creative vs corporate | Yes | **No** (`residue_centrality_failed`) | **FAIL** |

**All four cases completed Call 1 → confirmation → Call 2 → Call 3 → publication gate.**  
**None published.** Shared hard blocker: Call 1 returned **zero Residue candidates** in every case, so the deterministic gate set `residue_centrality_failed` even when body length and other checks were acceptable.

Separately, manuscript quality fails the freeze bar: invented biography, unsupported causal claims, and (cases 2–4) chaptered essay structure. **Production Candidate must not be frozen.**

---

## Shared runtime observation (all cases)

```
residue_ok = bool(call1.residue_candidates.items) and len(body) > 200
```

Call 1 selected lenses = `[]`, Re-branch directions = `[]` for all four.  
Observatory / Re-branch omission is consistent with empty evidence-gated design.  
Residue emptiness is **not** treated as optional by the gate → universal non-publish.

---

## Case 1 — Fertility / retrospective counterfactual only

### 1. Call 1 confirmation summary
- Status: `ready_for_user_confirmation` → user approve → `ready_for_draft`
- Coverage: complete
- Questions: 「今も、二人目を持っていたらどうだったかと考えることがある。」
- Actual secondary: 0 (correct for this case)
- Retrospective counterfactual: present
- Residue: **0**
- Observatory: none
- Re-branch: none
- Thesis (model): 「不妊治療を経て子どもを授かり、妻と息子と三人で暮らす人生を選んだことは、現在の幸せに繋がっている。」

### 2. Call 2 draft result
- Continuous short essay (~620 chars), 1 heading (title only) — **not** chapter-by-chapter
- No long verbatim copy of source
- No sentence fragments detected by runtime
- No Observatory / Re-branch body sections
- Independent gate blocker already: `residue_centrality_failed`
- Invented / unsupported material present (see excerpts)

### 3. Call 3 final result
- Largely same as Call 2 (little structural rewrite)
- Status: `validation_failed`, publishable=false
- Blocking: `residue_centrality_failed` only (runtime)

### 4. Selected title
`不妊治療を経て選んだ人生` — title validation **passed**

### 5. Observatory Lenses
None selected / omitted

### 6. Re-branch result
Omitted (no publishable directions)

### 7. Runtime validation
| Check | Result |
|---|---|
| unsupported_scene | 0 |
| contradiction | 0 (detector empty) |
| generic_advice | 0 |
| sentence_fragments | 0 |
| copied_long_input | 0 |
| observatory_takeover | false |
| title | passed |
| residue_centrality | **false** |
| publishable | **false** |

### 8. Japanese quality scores (manual / 10)

| Dimension | Score |
|---|---|
| A Naturalness | 7 |
| B Continuity | 8 |
| C Specificity | 5 |
| D Repetition control | 6 |
| E Residue quality | 3 |
| F Observatory relevance | n/a (omitted) |
| G Re-branch specificity | n/a (omitted) |
| H Closing quality | 6 |
| I Title quality | 6 |
| J Factual fidelity | **4** |

Flags: abstract 「絆」「希望」「幸せ」連鎖; mild self-help close 「これからも…楽しみに」; causal overclaim.

### 9. Exact problematic excerpts
- Invented duration/struggle: 「長い間、子どもを持つことを望んでいましたが、なかなか実現しなかったため、治療を決断したのです。」
- Unsupported emotional causality: 「不妊治療を受けることで、私たち夫婦はお互いの絆をさらに深め」
- Unsupported strengthening: 「困難を乗り越えたからこそ、今のように強くなった」
- Question preserved (good): 「今でも、二人目を持っていたらどうだったかと考えることがあります。」

### 10. Verdict
**FAIL** — factual fidelity ≠ 10; residue gate blocks publish; naturalness &lt; 8.

---

## Case 2 — Fertility + explicit later discussion/decision

### 1. Call 1 confirmation summary
- Status: ready → confirmed
- Actual secondary: **1** (expected) — description includes 話し合い／やめた evidence path
- Question retained as question
- Residue: **0**
- Observatory / Re-branch: none

### 2. Call 2 draft result
- ~795 chars, **5 headings** → chapter-by-chapter feel **true**
- Later decision present in draft body
- Gate: `residue_centrality_failed`
- Invented rationale for stopping treatment

### 3. Call 3 final result
- Keeps sectioned structure (`## 家族の形を作る` … `## 結論`)
- Decision retained as narrative: 話し合い → やめる
- Exact token `やめた` absent (`やめることに決めました`) — meaning kept, string check brittle
- publishable=false (`residue_centrality_failed`)

### 4. Selected title
`不妊治療と家族の選択` (body H1 differs slightly) — title validation **passed**

### 5–6. Observatory / Re-branch
Omitted / omitted

### 7. Runtime validation
Same pattern as Case 1: only hard blocker `residue_centrality_failed`. Scenes/advice/fragments/copy = 0.

### 8. Japanese quality scores

| Dimension | Score |
|---|---|
| A Naturalness | 6 |
| B Continuity | 5 |
| C Specificity | 6 |
| D Repetition control | 5 |
| E Residue quality | 4 |
| F Observatory | n/a |
| G Re-branch | n/a |
| H Closing | 5 |
| I Title | 6 |
| J Factual fidelity | **5** |

Flags: blog-like H2 stack; 「宝物」「色を添えて」; invented motive for stopping treatment; 「結論」section.

### 9. Exact problematic excerpts
- Good (decision present): 「妻と話し合いました。結果として、私たちはその治療をやめることに決めました。」
- Invented motive: 「家族の形を維持し、息子に十分な愛情を注ぐためには、私たちの選択が重要だと感じたからです。」
- Chapter scaffolding: `## 結論` + stock satisfaction close

### 10. Verdict
**FAIL** — actual_secondary surfaced in prose (strength), but invented causality + sectioned essay + residue gate.

---

## Case 3 — First-choice university admission

### 1. Call 1 confirmation summary
- Named entities available in confirmation path
- Question: 別の大学ならどう変わったか
- Residue / Observatory / Re-branch: empty
- Thesis claims career influence (already interpretive)

### 2. Call 2 draft result
- ~1263 chars, **6 headings**, chapter-by-chapter feel **true**
- Tokens retained in final body: 第一志望 / 早稲田大学第一文学部 / 合格 / 進学 = **all true**
- Heavy invented campus life

### 3. Call 3 final result
- Same essay architecture; little compression of invention
- publishable=false (`residue_centrality_failed`)

### 4. Selected title
`早稲田大学第一文学部への進学とその影響` — passed title validation

### 5–6. Observatory / Re-branch
Omitted / omitted

### 7. Runtime validation
Blocker: residue only. Scene/advice detectors did **not** flag サークル/ゼミ (gap in scene heuristics).

### 8. Japanese quality scores

| Dimension | Score |
|---|---|
| A Naturalness | 6 |
| B Continuity | 5 |
| C Specificity | 4 |
| D Repetition control | 4 |
| E Residue quality | 3 |
| F Observatory | n/a |
| G Re-branch | n/a |
| H Closing | 5 |
| I Title | 7 |
| J Factual fidelity | **3** |

Flags: 「である」調の硬さ; 章立て過多; 抽象的影響論の反復; 大学パンフ調。

### 9. Exact problematic excerpts
- Preserved facts (good): 「第一志望の早稲田大学第一文学部に合格した」
- Invented prestige: 「早稲田大学は日本の名門大学の一つであり」
- Invented scenes: 「サークル活動やゼミでのディスカッション」
- Unsupported causality: 「早稲田大学で得た知識やスキルは、今の私の仕事に直接的に影響を与えている」
- Question softened toward answered speculation across long 想像 section

### 10. Verdict
**FAIL** — polarity/entities preserved, but invented campus biography and causal overreach; naturalness &lt; 8; residue gate.

---

## Case 4 — Creative work vs corporate career

### 1. Call 1 confirmation summary
- Question retained
- Residue / Observatory / Re-branch empty
- Thesis already leans interpretive about influence of not choosing creative life

### 2. Call 2 draft result
- ~1263 chars, **7 headings**, strong chapter-by-chapter / “はじめに〜結論” template
- Invented job functions (マーケ/営業/PM)
- Self-help framing

### 3. Call 3 final result
- Same template essay; publishable=false (`residue_centrality_failed`)
- Entities 会社員 / 創作 retained

### 4. Selected title
`人生の選択とその影響` — passed validation but generic / theme-level

### 5–6. Observatory / Re-branch
Omitted / omitted

### 7. Runtime validation
Residue blocker only. Generic-advice phrase list did **not** catch 「ワクワク」「さらなる成長」 style closers.

### 8. Japanese quality scores

| Dimension | Score |
|---|---|
| A Naturalness | 5 |
| B Continuity | 4 |
| C Specificity | 3 |
| D Repetition control | 4 |
| E Residue quality | 3 |
| F Observatory | n/a |
| G Re-branch | n/a |
| H Closing | 3 |
| I Title | 4 |
| J Factual fidelity | **3** |

Flags: 「はじめに/結論」作文; 「ワクワクします」; 抽象的得失論; 機械的対比反復。

### 9. Exact problematic excerpts
- Invented roles: 「マーケティング、営業、プロジェクト管理など」
- Invented affect: 「想像するだけでワクワクします」
- Unsupported reason-as-fact: 「これらの要素が、私が創作の道を選ばなかった理由の一部です。」（入力に理由は無い）
- Self-help close: 「これからも、自分の選択を大切にしながら、人生を歩んでいきたいと思います。」

### 10. Verdict
**FAIL**

---

## Cross-case findings

### A. Common strengths
1. **Pipeline integrity:** Call 1 parse/confirm → Call 2 → Call 3 all reached with live OpenAI.
2. **No long verbatim source paste** detected.
3. **No published Observatory without lenses** (empty selection → omitted).
4. **No unsupported Re-branch published** (empty → omitted).
5. Case 1 kept a relatively continuous short form (best structural draft).
6. Case 3 retained 第一志望 / 早稲田大学第一文学部 / 合格 / 進学 polarity tokens.
7. Case 2 preserved later discussion/decision in prose.
8. Title validator accepted fact-tied titles; no empty titles.

### B. Common weaknesses
1. **Residue always empty from Call 1** → universal `residue_centrality_failed`.
2. **Invented biography** not caught by scene gate (campus life, job functions, long infertility struggle).
3. **Unsupported causal claims** (“影響を与えた”, “絆が深まった”) dominate.
4. Cases 2–4 feel like **章立てレポート**, not one editorial continuum.
5. Residue / lingering-question weight is weak; closings drift to gratitude/self-help.
6. Call 3 often **does not substantially rewrite** Call 2; issues persist.

### C. Call 2-specific issues
1. Defaulting to many `##` sections (cases 2–4).
2. Expands beyond grounded facts into plausible but unsupported life detail.
3. Thesis restated as moral conclusion rather than held tension with present question.
4. Title candidates often theme-summary (“人生の選択とその影響”).

### D. Call 3-specific issues
1. Insufficient whole-document compression / de-sectioning.
2. Does not remove invented scenes when runtime gate misses them.
3. Does not restore Residue emphasis when Call 1 residue list is empty.
4. Minimal Japanese stylization beyond Call 2.

### E. Runtime-gate issues
1. **`residue_centrality` requires non-empty Call 1 residue list** — too brittle; blocks otherwise gate-clean drafts.
2. Scene detector misses サークル/ゼミ/教授/業種ロール列挙.
3. Generic-advice detector misses soft self-help closings.
4. Question→answered-speculation (long 想像 paragraphs) not blocked.
5. Contradiction / hypothesis-as-fact lists stayed empty despite causal overclaims.

### F. Prompt changes required (recommendations only — not applied)
**Do not touch Call 1 in the next patch unless Residue emptiness is explicitly accepted as Call 1 defect.** Prefer Call 2/3 first:

1. **Call 2:** Forbid inventing jobs, campus activities, motives, durations not in grounded facts; prefer omission.
2. **Call 2:** Require one continuous body; discourage `## はじめに/結論` and &gt;2 internal H2s unless outline demands.
3. **Call 2:** Center present-tense Residue / open question; avoid resolving the counterfactual.
4. **Call 3:** Explicit pass to delete unsupported invented details and flatten chapter scaffolding into continuous prose.
5. **Call 3:** If Residue candidates empty but questions exist, treat questions as Residue spine (prompt-level), without inventing answers.

Optional Call 1 follow-up (only if still empty after Call 2/3 fixes): require ≥1 residue_candidate grounded in present question / current context.

### G. Code changes required (recommendations only — not applied)
1. Soften or redefine `residue_centrality`: allow pass when `grounded.questions` are meaningfully present in body and Call 1 residue list is empty.
2. Expand unsupported-scene patterns: campus activities, named extracurriculars, enumerated corporate roles not in facts.
3. Detect unsupported causal templates: 「〜したことで〜が深まった」「直接的に影響」 without support_ids.
4. Add “sectioned essay” heuristic to Call 2 diagnostics / Call 3 pre-clean (many H2 + はじめに/結論).
5. Keep refusing heuristic long-form fallback (already correct).

### H. Can Production Candidate be frozen?
**No.**

Reasons:
- 0/4 publishable under current gate
- 0/4 reach factual fidelity 10/10
- 0/4 reach Japanese naturalness ≥ 8 with continuous editorial quality
- Systemic Residue emptiness + invention pattern

---

## Pass-criteria checklist (aggregate)

| Criterion | Case1 | Case2 | Case3 | Case4 |
|---|---|---|---|---|
| factual fidelity = 10 | Fail | Fail | Fail | Fail |
| unsupported_scene = 0 (runtime) | Pass* | Pass* | Pass* | Pass* |
| contradiction = 0 | Pass* | Pass* | Pass* | Pass* |
| theme takeover = false | Pass | Pass | Pass | Pass |
| sentence fragments = 0 | Pass | Pass | Pass | Pass |
| generic advice not published | Pass* | Pass* | Pass* | Pass* |
| Re-branch publishable or omitted | Pass | Pass | Pass | Pass |
| title passes validation | Pass | Pass | Pass | Pass |
| continuous editorial piece | Weak pass | Fail | Fail | Fail |
| naturalness ≥ 8 | Fail | Fail | Fail | Fail |
| **Case verdict** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |

\*Runtime detector value; manual review still found invented material the detectors missed.

---

## Next step (after this report)

Targeted revision order (recommended):

1. **Runtime residue gate** (code) — stop hard-failing when residue list empty but present questions carry Residue.
2. **Call 2 prompt** — anti-invention + anti-chaptering + Residue-first continuous draft.
3. **Call 3 prompt** — delete unsupported detail; flatten sections; preserve entities/polarity/questions.
4. Re-run the same four live cases **without** changing Call 1 unless Residue remains empty *and* editorial design truly needs Call 1 residue objects.

Call 1 v1.0.1 remains frozen for the next iteration unless a Call 2/3 fix proves Call 1 data is wrong (Residue emptiness is the only current Call 1 data-supply suspect).
