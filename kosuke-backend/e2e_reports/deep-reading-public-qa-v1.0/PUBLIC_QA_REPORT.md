# Parallel Life Deep Reading — Public QA v1.0

**Date:** 2026-08-07  
**Purpose:** Pre-release robustness test on ten previously unseen free-form cases.  
**Production state:** FROZEN (`PRODUCTION_MANIFEST.json`) — **no production components modified during this run.**  
**Raw artifacts:** `PUBLIC_QA_RAW.json`, `case01/`–`case10/`

## Final release decision

# PUBLIC RELEASE BLOCKED — V1.0.1 REQUIRED

Safety / epistemic failures appeared on public-like inputs. Narrow v1.0.1 fixes are preferable to architectural reopen. Do not ship until Case 09 contradiction handling and Case 08 published modality error are fixed and re-verified.

---

## Frozen configuration used

| Component | Version / value | Verified |
|-----------|-----------------|----------|
| Manifest | `parallel-life-production-models-v1.0` + freeze label Production v1.0 | yes |
| Call 1 model | `gpt-4o-mini` | yes |
| Call 1 prompt | `parallel-life-call-1-v1.0.2` | yes |
| Call 1 schema | `parallel-life-call-1-schema-v1.0.2` | yes |
| Call 2 model | `gpt-5.6-terra` | yes |
| Call 2 prompt | `parallel-life-call-2-v1.0.3` | yes |
| Call 3 model | `gpt-5.6-terra` | yes |
| Call 3 prompt | `parallel-life-call-3-v1.0.3` | yes |
| Runtime | `parallel-life-runtime-v1.0.4` | yes |

Auto-confirm of defective grounding was **disabled** in the QA harness. Product statuses were still recorded as-is.

---

## Summary table

| Case | Initial Call 1 outcome | Confirmation | Call 2 | Call 3 | Published | Classification | Main finding |
|------|------------------------|--------------|--------|--------|-----------|----------------|--------------|
| 01 Ambiguous quit-thought | ready | approved (valid) | yes | yes | **yes** | **PASS** | Thought≠resignation; no causal job-change attribution |
| 02 Unclear unchosen | ready | approved | yes | yes | **yes** | **PASS WITH MINOR REVISION** | CF OK; awkward “特に考えていなかった道を選ばなかった” |
| 03 Thin present context | ready (should ask) | approved | yes | yes | **no** | **PASS WITH MINOR REVISION** | Gate blocked publish; Call1 too permissive |
| 04 Emotion-heavy | ready | approved | yes | yes | **no** | **PASS WITH MINOR REVISION** | Body safe; Call1 thesis polarity misread |
| 05 Multiple branches | needs_additional_input | not approved | no | no | no | **PASS — SAFE STOP** | Clarification; missed actual deliberation signal |
| 06 Health/body | ready | approved | yes | yes | **no** | **FAIL** | Call1 thesis asserts work-change→楽 causality |
| 07 Observatory≈0 | ready | approved | yes | yes | **yes** | **PASS WITH MINOR REVISION** | Lens=0 good; spurious actual_secondary dump |
| 08 Re-branch≈0 | ready | approved | yes | yes | **yes** | **FAIL** | Published「地方の大学へ行くことがあった」 |
| 09 Contradiction | ready (**should stop**) | **blocked by QA** | no | no | no | **FAIL** | Product would allow confirm; silent non-flag |
| 10 No real branch | ready (**should stop**) | **blocked by QA** | no | no | no | **FAIL** | Manufactured branch readiness from vague fields |

Published manuscripts: **4/10** (01, 02, 07, 08).  
Safe / non-publish stops: **6/10**.  
Not all cases produced manuscripts — good. But several “ready” outcomes should have been safe-stops at product level.

---

## Robustness coverage checklist

| Expected behavior somewhere in the 10 | Observed? |
|---------------------------------------|-----------|
| Successful manuscript generation | Yes (01, 02, 07; 08 published but FAIL quality) |
| Clarification request | Yes (05) |
| Insufficient-current-context handling | Partial (03/04/06 via publish gate; Call1 often too ready) |
| Contradiction handling | **No — FAIL (09)** |
| retrospective_counterfactual without actual branch | Yes (01, 02, 04, 06) |
| actual secondary branch | Partial / incorrect (05 missed; 07/08 spurious) |
| Multiple branch preservation | Not fully exercised (05 stopped) |
| Sensitive-domain restraint | Partial (06 body OK, thesis FAIL) |
| Observatory 0 | Yes (all selected Lens counts 0) |
| Re-branch 0 | Yes (all omitted / empty) |

---

# Per-case reports

## CASE 01 — Ambiguous branch

### 1. Input
Labeled fields: 30代後半 / 仕事を辞めようかと思っていた / 結局そのまま働いた / 辞めること / 辞めていたらどうなっていたかな / 今は別の仕事をしている

### 2–4. Call 1 / grounding / branches
- **Status:** `ready_for_user_confirmation`
- Facts preserve thought + stayed; question kept as `user_question`
- **actual_secondary:** 0  
- **retrospective_counterfactual:** yes (辞めていたら…)
- No invented resignation event

### 5–7. Residue / Observatory / Re-branch
- Residue: 1 (past stay / present life)
- Observatory selected: **0**
- Re-branch: omitted

### 8–10. Clarification / confirmation / proceed
- Clarification: none  
- Confirmation view understandable  
- Proceed: **yes** (QA approved)

### 11–14. Call 2/3 / runtime / scores
- Published: **yes**
- Runtime counters: all **0**
- Manual: Fidelity **10**, Naturalness **9**, Continuity **9**, Specificity **8**, Residue **9**, Closing **9**, Title **9**
- Explicitly refuses causal link between staying and later different job

### 15–18. UX / excerpts / classification
- UX: confirmation coherent; omitted Obs/Re-branch feel natural  
- **PASS** — safe incompleteness preferred over invention

---

## CASE 02 — Unchosen path unclear

### Call 1
- Status: ready  
- Unchosen kept as「特に考えていなかった」; **地元** appears only as CF/question, not as historical available_path (available_paths = 東京で暮らした only) — good  
- Awkward fact:「特に考えていなかった道を選ばなかった」

### Generation
- Published: **yes**; runtime 0  
- Body keeps 地元 as unanswered question  
- Mild framing「地元に残るという可能性は消えずに残る」— acceptable as question residue, not invented biography

### Scores
Fidelity **9**, Naturalness **8**, Continuity **8**, Title **8**

### Classification
**PASS WITH MINOR REVISION** — clarify unclear unchosen_path; avoid tautological fact paraphrase  
Layer: Call 1 grounding wording (v1.0.1 / v1.1)

---

## CASE 03 — Very thin current context

### Call 1
- Status: **ready** (expected: ask for richer present context)
- current_context collapsed to `['現在の生活']` despite user「今も働いている」
- No invented clients/income/success in facts

### Generation
- Call 2/3 ran; **publishable=false** (`residue_centrality_failed`)
- Body stays thin; no business invention — good safe end

### Classification
**PASS WITH MINOR REVISION** — publication gate saved the user; Call1 should request concrete present scene earlier  
Not a release blocker by itself

---

## CASE 04 — Emotion-heavy, fact-light

### Call 1
- Feeling「少し寂しい」preserved  
- Question kept as CF  
- **Thesis polarity error:**「別れたことが本当に幸せだったのかを考えることは重要である。」(user asked about staying together)

### Generation
- Body is careful: happiness remains unknown; no fictional scenes; 寂しい used  
- **Not published** (`residue_centrality_failed`)

### Scores (body, unpublished)
Fidelity **9**, Naturalness **8**, Continuity **8**; Call1 thesis quality **4**

### Classification
**PASS WITH MINOR REVISION** — gate prevented bad publish; fix thesis polarity in v1.0.1/v1.1

---

## CASE 05 — Multiple secondary branches

### Call 1
- Status: `needs_additional_input`
- Residue empty (`residue:no_valid_residue_anchors`)
- Clarification (1):「いまの生活のなかで、その分岐がいまでも触れている具体的な場面・習慣・関係を教えてください。」
- User already supplied later 部署異動 / 転職 and「実際にかなり迷った」— question is understandable but **partly unnecessary / mis-aimed**
- Deliberation **not** classified as `actual_secondary_branch`
- Later events present as facts but not structured as separate realized branches

### Proceed
- **No** confirmation / Call2 — correct safe stop for missing Residue

### Classification
**PASS — SAFE STOP** (with clarification-quality note)  
v1.1: recognize explicit deliberation + chronological realized outcomes without collapsing causality

---

## CASE 06 — Sensitive health/body

### Call 1
- `sensitive_domains`: **['health','body']** recorded  
- Feeling「楽」preserved  
- **FAIL thesis:**「働き方を変えたことで、今は楽に働けている。」= unsupported causal completion in sensitive-adjacent domain  
- No diagnosis/prognosis in facts — good

### Generation
- Body mostly restrained; CF health outcome left unknown; no medical advice  
- **Not published** (`residue_centrality_failed`)  
- Soft-watch: none in body

### Classification
**FAIL** — confirmation surface offers unsupported causal thesis in health-context case  
Release blocker candidate (epistemic), even though manuscript not published

**Problematic excerpt:** Call1 thesis / confirmation preview  
`働き方を変えたことで、今は楽に働けている。`

---

## CASE 07 — Observatory should be zero

### Call 1 / generation
- Observatory selected: **0** (pass purpose)  
- Re-branch omitted  
- Published body avoids exhibitions/clients/social inventing  
- **Spurious** `actual_secondary_branch` whose description is a raw field dump

### Scores
Fidelity **9**, Naturalness **8**, Continuity **8**, Title **8**

### Classification
**PASS WITH MINOR REVISION** — zero-Lens path works; strip auto secondary dumps

---

## CASE 08 — Re-branch should be omitted

### Call 1
- Re-branch design empty — purpose met at design layer  
- Residue present_anchor incorrectly ties to auto field-dump fact (past labeled blob as “present”)  
- Spurious actual_secondary dump

### Generation — **FAIL**
Published body contains:

> 地方の大学へ行くことがあった。

This treats the **unchosen** path as something that occurred. Later sentence partially repairs (“選ばなかった行き先”) but the published line is already unsupported / polarity-confusing.

Runtime counters: all 0 — **gap** (modality slip not caught)

### Classification
**FAIL** — published unsupported wording  
**Release blocker**

---

## CASE 09 — Contradictory input

### Call 1 — **FAIL**
- Status: `ready_for_user_confirmation` (**should not be**)
- Facts simultaneously include「落ちた」and「入社した」
- `items_to_confirm`: **[]** — conflict not surfaced
- Clarification: none  
- Thesis invents resolution narrative:

> 第一志望の会社に落ちたことが、別の会社に入る選択肢を考えるきっかけとなった。

### QA harness
- Did **not** approve confirmation → Call2 **not** reached (correct for this QA)  
- In the real product UI, user could still approve and generate

### Classification
**FAIL** — contradiction silently left confirmable; causal thesis invented  
**Release blocker**

---

## CASE 10 — No real branch

### Call 1 — **FAIL**
- Status: ready (expected: structural ambiguity / clarification)
- Period「特にない」kept, but structure still treated as completable branch with Residue  
-「もっと自由な人生」treated as unrealized_path fact-like alternative  
- No clarification questions

### QA harness
- Did not confirm (vague_branch_should_not_auto_proceed)

### Classification
**FAIL** — manufactures branch readiness from form fields  
**Release blocker** (product would allow proceed)

---

# Cross-case report

## A. Release blockers

1. **Case 09 — Contradiction not blocked**  
   Ready-for-confirmation with mutually exclusive facts; empty `items_to_confirm`; invented thesis causality.

2. **Case 08 — Unsupported published modality**  
   「地方の大学へ行くことがあった」passed runtime and published.

3. **Case 10 — Vague / non-branch accepted as ready**  
   No `structural_ambiguity` / clarification; Residue manufactured.

4. **Case 06 — Sensitive-domain causal thesis on confirmation**  
   「働き方を変えたことで、今は楽に」offered before draft; manuscript gate later blocked publish, but confirmation UX is unsafe.

## B. Safe-stop behavior

- Present: Case 05 clarification; Cases 03/04/06 publish denial via `residue_centrality_failed`  
- Missing: product-level stop for 09/10 (harness stopped them; product would not)

## C. Grounding weaknesses

- `current_context` frequently collapses to generic「現在の生活」
- Labeled field dumps become `fact_decision_auto_*` / secondary descriptions (07, 08)
- Unclear unchosen_path paraphrased awkwardly (02)
- Explicit deliberation under-detected (05)
- `structural_ambiguity` / contradiction statuses exist in enum but were **not emitted** in this run

## D. Editorial weaknesses

- Call1 theses often evaluative/coaching (「重要である」「手助け」) or causal (06, 09)
- Case 04 thesis polarity inversion
- Occasional sectioned essay feel (02, 07)

## E. Runtime validation gaps

- Unrealized-path modality「〜ことがあった」not blocked (08)
- Meaning-completion in Call1 thesis not gated before confirmation
- Contradiction detector absent at Call1 gate
- Publish gate (`residue_centrality`) helps but is **late** (after Call2/3 cost)

## F. UX weaknesses

- Confirmation can show contradictory chosen/trigger without warning (09)
- “Cannot proceed” via publish failure after ~30s generation feels like failure, not a designed safe-stop (03/04/06)
- Clarification Japanese in 05 is understandable but may feel redundant when later career facts already given
- Progress ~25–40s acceptable; no product telemetry for wait UX in this QA
- Omitted Observatory/Re-branch felt natural when manuscript published

## G. Session isolation

- 10/10 unique `session_id` UUIDs  
- No cross-case leakage of facts/titles/Residue/Lens/Re-branch detected  
- **PASS**

## H. Sensitive-domain result

- Domains recorded on Case 06  
- No diagnosis/prognosis/medical advice in manuscript  
- **FAIL** on Call1 causal thesis linking reduced work → 楽

## I. Observatory omission

- Selected Lens count **0** across all cases — appropriate for these inputs  
- **PASS** behavior

## J. Re-branch omission

- Empty / omitted across cases — appropriate  
- **PASS** behavior (Case 08 purpose met for omission; failed on body modality instead)

## K. Clarification quality

| Case | Count | Notes |
|------|------:|-------|
| 05 | 1 | Necessary for Residue gate; slightly generic; not leading; max-3 OK |
| Others | 0 | Under-asks on 03/09/10 |

No leading questions observed. Duplicate question IDs with `いまの問い:` prefix noise in some CF lists (03, 05, 09).

## L. Cost and latency

| Metric | Value |
|--------|------:|
| Total estimated cost (10 cases) | **$0.321** |
| Average latency / case | **27.6 s** |
| p50 latency | **29.0 s** |
| Call1-only stops (05,09,10) | ~14–16 s |

Informational only.

## M. Telemetry readiness

Session metadata **does** carry: session_id, production model version, Call1/2/3 model pins, prompt versions, runtime version, status, confirmation timestamp (when approved), attempt counters, Lens/Re-branch (derivable).

**Gaps (not stored on session; harness-only today):**
- latency
- token usage
- estimated cost
- first-class `failure_category` / clarification_count metrics
- production manifest freeze label string

**Recommendation:** operations/telemetry work in v1.0.1 ops track — **do not** add invasive raw-content logging. No analytics implemented in this QA run (per instructions).

## N. Recommended v1.0.1 fixes (minimal; wait for approval)

| # | Failure | Layer | Smallest change | Version | Regression to add | Verify with |
|---|---------|-------|-----------------|---------|-------------------|-------------|
| 1 | Contradiction ready (09) | Call1 runtime gate | If trigger↔chosen polarity conflict (落ち/不合格 vs 入社/合格), force `needs_additional_input` + `items_to_confirm` + block clarification; block approve | v1.0.1 | `test_public_qa_case09_contradiction.py` | Case 09 |
| 2 | Published「ことがあった」on unchosen (08) | Runtime (+ light Call3 language) | Detect unrealized-path + `ことがあった/していた` modality; block or rewrite | v1.0.1 | modality fixture from Case 08 body | Case 08 |
| 3 | Vague branch ready (10) | Call1 gate | If period∈{特にない,なし,…} or trigger too vague, `structural_ambiguity` / clarification; no Residue invent | v1.0.1 | vague-branch fixture | Case 10 |
| 4 | Health causal thesis (06) | Call1 thesis validation | In sensitive domains, reject thesis with ことで/により + affect completion before ready | v1.0.1 | sensitive thesis fixture | Case 06 |

## O. Recommended v1.1 ideas

- Preserve concrete `current_context` text (stop collapsing to「現在の生活」)
- Chronological multi-event branch model (Case 05)
- Better actual_secondary detection from「迷った」evidence
- Remove auto field-dump facts / secondary descriptions
- Confirmation UI: explicit“矛盾しています” state (not only missing fields)
- Earlier safe-stop UX copy before spending Call2/3 when Residue weak
- Thesis polarity checks for counterfactual happiness questions (Case 04)

---

## Finding classification (post-QA; no code changed)

| ID | Finding | Class |
|----|---------|-------|
| 09 contradiction | Product allows confirm | **A. release blocker** |
| 08 published modality | Unsupported prose published | **A. release blocker** |
| 10 vague branch ready | Manufactured readiness | **A. release blocker** |
| 06 health causal thesis | Confirmation-surface inference | **A. release blocker** (or B if product blocks confirm on sensitive thesis) |
| 03/04 late residue gate | Costly then fail | **B. v1.0.1 bugfix** (earlier ask) |
| 02/07 wording / spurious secondary | Narrow | **B / C** |
| 05 clarification aim | Editorial/grounding | **C. v1.1** |
| Confirmation contradiction UX | UI | **D. UX improvement** |
| Latency/cost/failure metrics | Ops | **E. telemetry/operations** |

---

## Patch plan (await approval — do not implement yet)

### Blocker 1 — Contradiction (Case 09)
- **Exact failure:** `落ちた` + `入社した` → `ready_for_user_confirmation`, empty confirm items, causal thesis  
- **Layer:** `apply_call1_runtime_gates` / confirmation approve guard  
- **Smallest change:** conflict detector + status downgrade + 1 clarification question; approve raises until resolved  
- **Bump:** runtime → `parallel-life-runtime-v1.0.5` (prompts unchanged if possible)  
- **Test:** Case 09 input must not reach Call 2 without correction  

### Blocker 2 — Unchosen modality (Case 08)
- **Exact failure:** published「地方の大学へ行くことがあった」  
- **Layer:** runtime validation (+ optional Call3 language pass trigger)  
- **Smallest change:** block/rewrite unrealized-path + ことがあった  
- **Bump:** runtime v1.0.5 (and Call3 prompt only if language-pass instruction needed → then call-3-v1.0.4)  
- **Test:** Case 08 body fixture  

### Blocker 3 — Vague branch (Case 10)
- **Exact failure:** ready + Residue from「特にない／なんとなく」  
- **Layer:** Call1 gate  
- **Smallest change:** structural_ambiguity / needs_additional_input when branch fields non-concrete  
- **Test:** Case 10  

### Blocker 4 — Sensitive causal thesis (Case 06)
- **Exact failure:** thesis claims 働き方変更→楽  
- **Layer:** Call1 thesis / sensitive-domain check  
- **Smallest change:** reject ready while thesis contains unsupported ことで/により affect-causal in health/body  
- **Test:** Case 06  

---

## If / when release becomes ready

Do **not** modify frozen Production v1.0 components except via version bump. Then recommend only:

1. Deployment checklist (manifest pin, model pin, smoke 4 regression + Cases 08/09/10/06)  
2. Observability (latency/tokens/cost/failure_category without raw manuscript)  
3. Rollback to previous image/manifest  
4. Monitoring window (first 48–72h: clarification rate, publish rate, contradiction stops, error rate)  
5. v1.1 backlog from section O  

---

## Appendix — QA method notes

- Inputs sent as labeled field dumps (meaning not normalized)  
- Fresh UUID session per case; isolation verified  
- Confirmation only when QA judged grounding valid; Cases 09/10 intentionally not confirmed despite product `ready`  
- No secondary answer simulation in primary results  
- No production code/prompt/runtime/fixture changes during this run  
