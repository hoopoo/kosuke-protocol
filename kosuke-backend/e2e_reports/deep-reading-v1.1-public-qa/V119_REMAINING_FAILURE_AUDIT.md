# Parallel Life Deep Reading v1.1.9-exp — Remaining Public QA Failure Audit

Generated: `2026-08-08` (post v1.1.9 live Public QA)  
Sources: `PUBLIC_QA_V119_RAW.json`, `v119/*/`, `live_ab/*/public_qa_v118_session_final.json`  
Scope: **analysis only** — no prompts / runtime / schemas / BranchSemantics / Observatory thresholds / title validation / publication gates modified.

## Verdict (audit)

Semantic leakage and clarification loops are **not** the remaining blockers.

Remaining non-publishable cases split into three tracks:

| Track | Nature | Cases primarily affected |
|-------|--------|---------------------------|
| **A** Deterministic/runtime | Observatory keyword false-negative; Call3 heading destruction; Call3 label rename; pre-draft soft-gate bounce after clarification exit | family, entrepreneurship, health, education (labels), romance/creative/zero_lens (pre-draft) |
| **B** Editorial realization | Call3 under-realization / weak claim echo; title–closing mismatch | education, sensitive, (partial) vague |
| **C** Observatory coverage | mostly correct zero-lens / omit-by-CrossLens; creative candidates unused only because pipeline never reached draft | zero_lens, creative (deferred) |

**Recommended next step: E — MULTIPLE TRACKS, WITH ORDER → start with A.**

---

## 1. 10-case failure matrix

| Case | Domain | Pub | Class | First true failure point | Gate vs Quality | Primary type |
|------|--------|-----|-------|--------------------------|-----------------|--------------|
| case01_career | career | **True** | PASS | — (full pipeline OK) | — | — |
| case02_family | family | False | GATE_BLOCKED | Call3 validators: `required_section_unrealized:observatory` despite present section | **GATE** (quality high: nat9/depth9) | **H** validator_false_negative |
| case03_education | education | False | GATE_BLOCKED | Call3 renames labels + compresses early sections; then title_closing_mismatch | GATE + QUALITY | **G** + **F** + **E** |
| case04_romance | romance | False | PASS_SAFE_STOP | Pre-draft: `thesis_gate:unsupported_causal_framing` → clarification exit → stuck `ready_for_user_confirmation` (no Call2) | neither manuscript gate nor quality yet | **I** / soft-gate bounce |
| case05_health | health | False | GATE_BLOCKED | Call3 destroys `##` line structure (inline headings) → all labels “missing” | **GATE** (Call2 was good) | **F** Call3_deletion / markdown |
| case06_entrepreneurship | career | False | GATE_BLOCKED | Same observatory keyword FN as family | **GATE** (nat9/depth9) | **H** validator_false_negative |
| case07_creative | creative | False | PASS_SAFE_STOP | Same pre-draft soft-gate bounce as romance | no manuscript | **I** / soft-gate bounce |
| case08_vague | unknown | False | GATE_BLOCKED | Empty/weak central thesis + no SectionContracts; prose without labels | GATE (expected sparse) | **I** + thesis/title gate |
| case09_zero_lens | place | False | PASS_SAFE_STOP | Same pre-draft soft-gate bounce; Observatory candidates empty (correct) | no manuscript | **I** + correct zero lens |
| case10_sensitive | health | False | GATE_BLOCKED | Call3 under-realizes Lost/Protected vs claim markers; Observatory keyword FN | GATE + QUALITY | **E** + **H** |

---

## 2. First failure point per case (pipeline order)

Trace order used: BranchSemantics → MeaningCompression → Thesis → SectionContracts → Claims → Call2 → Call3 → Validators → Publishable.

### case01_career — PASS
All stages succeed. Observatory lenses `selected=[]` by design (`omitted_pre_thesis_relations`) but CrossLens meaning is realized under `## 社会との接続`. Publishable.

### case02_family — first fail at **Call3 validators (Observatory realization)**
- BranchSemantics `family` OK; contracts/claims OK; Call2+Call3 keep all 8 labels.
- Observatory body exists and is on-claim (body/care vs institutional reduction).
- Validator `_section_claim_realized("observatory")` requires `(?:社会|雇用|企業間|並[べび]|長期|似た条件|人々)` — family/body prose matches **none** → false unrealized.
- **Not** selector failure: candidates `body`, `after-success` exist; section omitted from *lens list* via CrossLens omit path, but section text is present.

### case03_education — first fail at **Call3 label rename / compression**
- Call2 has correct locked labels including `守られたもの` / `今に残った構造`.
- Call3 renames to `残されたもの` / `今に残る問い` → `required_public_label_missing`.
- Call3 also collapses Branch Point / Chosen Path / Lost to fact-only lines → `required_section_unrealized` + thesis_closure failures.
- Title fails separately: `title_closing_mismatch` (subtitle present; closing mismatch).
- BranchSemantics/contracts themselves are education-correct (no career leak).

### case04_romance — first fail **before Call2**
- Contracts/claims exist and look domain-correct.
- Approve path soft-fails on `selection:thesis_gate:unsupported_causal_framing`.
- Clarification exit `proceed_structurally_sufficient` returns `ready_for_user_confirmation` but never reaches `ready_for_draft`.
- Harness correctly stops (no manuscript). This is a **pre-draft product/runtime soft-stop**, not section prose failure.

### case05_health — first fail at **Call3 markdown destruction**
- Call2: complete labeled manuscript, claims largely realized.
- Call3: merges sections into a single prose blob with **inline** `## 選ばなかった人生。` / `## 守られたもの。` (not line-start headings). Parser only accepts `^##\s+` → 7/8 labels “missing”; only trailing proper `## これからの再分岐` survives.
- Meaning is largely still in the blob — mechanical label/parser failure, not absence of content.

### case06_entrepreneurship — first fail at **Call3 validators (Observatory)**
- Same pattern as family: full labeled manuscript; Observatory prose is after-success parallel (“達成…問いが残る”) without employment keywords → unrealized FN.
- Quality otherwise strong (nat9/depth9).

### case07_creative — first fail **before Call2** (same as romance)
- BranchSemantics `creative` OK; contracts OK; candidates `education-employment`/`after-success` present; relations=0.
- Soft-gate thesis causal framing + clarification exit bounce → no draft.
- Observatory selector issue is **deferred** until draft is reachable.

### case08_vague — first fail at **Thesis / contract absence**
- `branch_semantics` null; SectionContracts empty (`must_be_present` none).
- Call2/Call3: short unlabeled essay.
- Gates: `central_thesis_not_maintained`, `title_validation_failed` (`title_not_linked_to_central_thesis`).
- Appropriate sparse behavior for vague input; not a label bug.

### case09_zero_lens — first fail **before Call2** (soft-gate bounce)
- BranchSemantics `place` OK; Observatory candidates/evidence empty → **correct zero lens**.
- Same thesis causal soft-gate + clarification exit bounce as romance/creative.

### case10_sensitive — first fail at **Call3 claim realization (Lost/Protected) + Observatory FN**
- Labels preserved (unlike health/education rename).
- Lost body uses “確かめることはできない” but marker regex wants `確かめられ|辿れな|検証できな|…` → underrealization.
- Protected body narrates caregiving help (“置いておける”) without `余白|余地|保た|…` markers → underrealization.
- Observatory body is body-lens parallel without employment keywords → FN (H).

---

## 3. Section realization matrix

Legend: Y/N for each cell. Types use A–J from §3 of the brief.

### Summary matrix (final Call3 / or pre-draft N/A)

| Case | BP | Chosen | Unchosen | Lost | Prot | Residue | Obs | Re-branch |
|------|----|--------|----------|------|------|---------|-----|-----------|
| career | pass | pass | pass | pass | pass | pass | pass | pass |
| family | pass | pass | pass | pass | pass | pass | **H FN** | pass |
| education | **E** | **E** | pass | **E** | **G** | **G** | pass | **E** |
| romance | n/a pre-draft | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| health | **F/G** | **F/G** | **F/G** | **F/G** | **F/G** | **F/G** | **F/G** | pass* |
| entrepreneurship | pass | pass | pass | pass | pass | pass | **H FN** | pass |
| creative | n/a pre-draft | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| vague | no contract | no contract | no contract | no contract | no contract | no contract | no contract | no contract |
| zero_lens | n/a pre-draft | n/a | n/a | n/a | n/a | n/a | n/a (correct 0) | n/a |
| sensitive | pass | pass | pass | **E** | **E** | pass | **H FN** | pass |

\*health: Re-branch has a proper line-start `##` heading; other sections’ content exists but headings are inline/broken.

### Detailed per-section (blocked cases)

#### case02_family — Observatory only

| Field | Observatory |
|-------|-------------|
| contract exists / required | Y / Y |
| interpretive claim | Y — `個人史は身体経験として続き、制度説明に還元しない` |
| evidence | CrossLens `clr_body_001` + `obs_body_001` (supporting_evidence_ids on contract may be empty; meaning from relations) |
| Call2 realized (label+prose) | Y |
| Call3 preserved | Y |
| public label | Y `社会との接続` |
| validator | **FAIL** unrealized |
| exact reason | Keyword set employment-biased; excerpt has 家族/身体/ケア/制度 but not 社会\|雇用\|企業間\|並べ\|… |
| type | **H** |

#### case03_education

| Section | Contract | Claim | Call2 | Call3 label | Call3 realize | Type |
|---------|----------|-------|-------|-------------|---------------|------|
| Branch Point | Y | Y | Y | Y | N (fact-only 40ch) | E |
| Chosen Path | Y | Y | Y | Y | N (“第一志望の大学へ進学した。”) | E |
| Unchosen | Y | Y | Y | Y | Y | — |
| Lost | Y | Y | Y | Y | N (weak markers) | E |
| Protected | Y | Y | Y | **N** (`残されたもの`) | n/a | **G** (+ meaning moved) |
| Residue | Y | Y | Y | **N** (`今に残る問い`) | n/a | **G** |
| Observatory | Y | Y | Y | Y | Y | — |
| Re-branch | Y | Y | Y | Y | N (release/choice markers incomplete vs gate) | E |

#### case05_health

| Section | Call2 | Call3 | Type |
|---------|-------|-------|------|
| All except Re-branch | Proper `##` + realized prose | Content merged; headings become inline `## ラベル。` → parser miss | **F** (structure) then reported as **G** missing labels |
| Re-branch | Y | Proper `## これからの再分岐` preserved | — |

Excerpt (Call3 destruction):

```text
…治療と仕事が同じ現在の生活のなかにある。## 選ばなかった人生。選ばなかった道は…
…置いておくほうが近い。## 守られたもの。仕事量を抑え…
```

#### case06_entrepreneurship — Observatory

| Field | Value |
|-------|-------|
| claim | `達成の事実と、なお残る問いを並置して読める` |
| Call3 excerpt | `何かを形にし、仕事が続いているという事実と、その後にも問いが残ることは矛盾しない…` |
| validator | FAIL (no 社会/雇用/企業間/並べ/…) |
| type | **H** (after-success parallel is present) |

#### case10_sensitive

| Section | Call3 excerpt (abbrev) | Validator | Type |
|---------|------------------------|-----------|------|
| Lost | `…いま確かめることはできない。失われたものは、そうした別の経過を知る確かさでもある。` | unrealized | **E** (marker miss; meaning partial) |
| Protected | `家族が看病を手伝ってくれた…置いておける` | unrealized | **E** (care narrative ≠ protected-possibility markers) |
| Observatory | body/care time parallel | unrealized | **H** |

#### Pre-draft cases (04/07/09)

All eight contracts generally exist with claims; **no Call2/Call3**. Classification per section: **I** (pipeline stopped) — not A–H manuscript failures.

---

## 4. Public label audit

| Case | Symptom | Cause | Meaning present? | Classification |
|------|---------|-------|------------------|----------------|
| education | `守られたもの`→`残されたもの`; `今に残った構造`→`今に残る問い` | **Call3 rename** | Yes (under new names) | **G** — label-only diverge + secondary underrealization |
| health | Labels reported missing | **Call3** collapsed newlines; `##` not at line start; parser `^##\s+` fails | Yes (inline) | **F** then surfaced as **G**; **not** semantic failure |
| family / entrepreneurship / sensitive / career | Labels exact | OK | — | — |
| romance / creative / zero_lens | N/A | no manuscript | — | — |
| vague | no locked labels | no contracts | prose only | expected sparse |

**Do not loosen validation yet.** Smallest mechanical fixes (Track A): Call3 must preserve locked labels as line-start `##` headings; optionally treat known synonym renames as diagnostics-only later — out of scope for this audit.

---

## 5. Manuscript omission audit

| Case / section | Missing? | Why | Excerpt / note |
|----------------|----------|-----|----------------|
| health ×7 sections | Apparent omission | Call3 markdown merge, not content deletion | Inline `## 守られたもの。` etc. |
| education Protected/Residue | Label missing | Call3 rename | Call2 had correct labels + strong prose |
| education BP/Chosen/Lost | Underrealized | Call3 compression to chronology | Chosen Call3: `第一志望の大学へ進学した。` vs Call2 structural shift paragraph |
| family Observatory | Validator says unrealized | Content present | See §2 |
| entrepreneurship Observatory | Validator says unrealized | Content present | after-success prose |
| sensitive Lost/Protected | Weak vs markers | Call3 (and partly Call2) wrote adjacent but different meaning | Protected became caregiving anecdote |
| vague all | No section scaffold | Intentional sparse + no contracts | Unlabeled 3-paragraph essay |
| 04/07/09 | Total omission of manuscript | Never drafted | clarification exit / thesis soft-gate |

**Not observed:** evidence payload empty as primary cause for omitted required sections when draft ran. Contracts had claims; failures are post-contract (Call3 / validator).

---

## 6. Observatory false-negative audit

Do **not** increase lens selection thresholds (per brief).

| Case | BranchSemantics | Candidates | Evidence | Selected | Relations | Omit note | Zero-lens judgment |
|------|-----------------|------------|----------|----------|-----------|-----------|--------------------|
| career | career | ee, after-success, clean-society | obs_ee_*, obs_as_*, obs_cs_* | [] | 3 | omitted_pre_thesis_relations | **A** correct omit-from-lens-list; section still written via CrossLens — publishable |
| family | family | body, after-success | obs_body_001, obs_as_001 | [] | 2 | omitted_pre_thesis_relations | Lens omit OK; **section validator H** |
| education | education | education-employment | obs_ee_* | [] | (used in thesis/obs prose) | omitted_pre_thesis_relations | Section realized OK |
| romance | romance | [] | [] | [] | 0 | — | **A** plausible correct zero (no draft) |
| health | health | body | obs_body_001 | [] | present | omitted_pre_thesis_relations | Section content OK in Call2; Call3 structure break |
| entrepreneurship | career | after-success | obs_as_001 | [] | used | omitted_pre_thesis_relations | **H** on section keywords |
| creative | creative | ee, after-success | obs_ee_*, obs_as_* | [] | 0 | omitted_pre_thesis_relations | **C?** deferred — never drafted; candidates exist |
| vague | — | — | — | — | — | — | **A** |
| zero_lens | place | [] | [] | [] | 0 | — | **A correct zero lens** |
| sensitive | health | body | obs_body_001 | [] | used | omitted_pre_thesis_relations | **H** on section keywords |

Separation:

- **A. correct zero lens:** zero_lens, vague, romance (no social structure), career/family lens-list omit-by-CrossLens design.
- **B. missing evidence coverage:** not primary for these 10 (store hits exist when structures fire).
- **C. selector false-negative:** only *possible* for creative (candidates>0, relations=0, no draft). Do not expand store yet.

---

## 7. Quality vs gate split

| Case | Quality (nat/depth/life) | Gate blockers | Qualitatively good but mechanically blocked? |
|------|--------------------------|---------------|-----------------------------------------------|
| career | 9/9/YES | none | published |
| family | 9/9/mixed | observatory unrealized | **YES** |
| education | 9/7/mixed | labels + underrealization + title | Partially — Call2 stronger than Call3 |
| romance | n/a | pre-draft | N/A manuscript |
| health | 8/7/mixed | all labels missing (parser) | **YES** if Call2 evaluated; Call3 structure broken |
| entrepreneurship | 9/9/mixed | observatory unrealized | **YES** |
| creative | n/a | pre-draft | N/A |
| vague | 9/7/mixed | thesis + title | Weak thesis is real; unlabeled form expected |
| zero_lens | n/a | pre-draft | N/A |
| sensitive | 9/8/mixed | lost/protected/observatory | Mixed — obs is mechanical FN; lost/protected need stronger claim echo |

---

## 8. Tracks (do not mix in one patch)

### TRACK A — deterministic / runtime
1. **Observatory realization keywords** domain-neutral (body/care/達成/並置 etc.) — fixes family + entrepreneurship + sensitive obs FN without loosening publication policy intent.
2. **Call3 heading preservation** — forbid inline `##`; preserve locked labels as line-start headings (health).
3. **Call3 locked-label rename guard** — reject/repair `残されたもの` / `今に残る問い` back to locked labels (education).
4. **Clarification-exit → draft** — when `proceed_structurally_sufficient` and thesis only soft-fails causal framing, define whether approve may reach draft or terminal insufficient (romance/creative/zero_lens). Currently bounces at confirm forever without manuscript.

### TRACK B — editorial realization
1. Education: restore structural_shift / lost / re_branch density in Call3 (not chronology-only).
2. Sensitive: Protected must echo 余地/余白/制約のなかで…; Lost must echo 辿れない/確かめられ….
3. Title closing alignment for education (separate from semantics).

### TRACK C — Observatory coverage
1. Only after draft reachable for creative: decide if `creative_vs_corporate` should form CrossLens relations (not raw lens spam).
2. zero_lens: leave as correct empty.
3. Do **not** raise selection thresholds in the same patch as A/B.

---

## 9. Legitimate safe-stops

| Case | Legitimate? | Why |
|------|-------------|-----|
| vague | **Yes (mostly)** | Unclear branch; empty semantics/contracts; thesis/title gates appropriate |
| zero_lens Observatory emptiness | **Yes** | No candidates/evidence — correct zero lens |
| romance/creative/zero_lens pre-draft | **Partially** | Soft thesis gate may be legitimate caution; but clarification exit promising “proceed” without draft is a product inconsistency — not a successful deep-reading completion |

Do **not** assume all 9 non-publishable should publish.

---

## 10. Publishable-count explanation (why 1/10)

| Bucket | Count | Cases |
|--------|------:|-------|
| Already publishable | 1 | career |
| Blocked mainly by **deterministic bugs** (Track A) | **3–4** | family, entrepreneurship, health; (+ education labels as A) |
| Blocked by **editorial Call3 quality** (Track B) | **1–2** | education underrealization, sensitive lost/protected |
| **Pre-draft soft-stop / exit bounce** | **3** | romance, creative, zero_lens |
| **Legitimate sparse / vague** | **1** | vague |

Estimate if Track A only (no gate loosening, no prompt rewrite): publishable could move from **1 → ~4** (family, entrepreneurship, health) if Call3 heading fix + observatory keyword FN fix land and those manuscripts already score nat/depth ≥8.

Education/sensitive still need Track B. Pre-draft three need approve-path product decision before any manuscript metric applies.

---

## 11. Recommended next patch

**E. MULTIPLE TRACKS, WITH ORDER**

1. **First (smallest high-leverage): TRACK A**
   - Priority order inside A:
     1. Observatory realization keyword false-negative (family + entrepreneurship + sensitive obs)
     2. Call3 line-start heading preservation (health)
     3. Call3 locked public-label rename guard (education labels)
     4. Clarification-exit vs thesis soft-gate draft reachability (romance/creative/zero_lens)
2. **Then TRACK B** only for residual underrealization (education/sensitive).
3. **TRACK C last** and only if creative still has zero CrossLens after drafts exist.

**Do not** open publication gates or title validation in the same change.

Chosen single letter if forced to one: **A. FIX DETERMINISTIC SECTION / LABEL BUGS FIRST**.

---

## 12. Production untouched confirmation

| Check | Value |
|-------|-------|
| Production Call1 | `parallel-life-call-1-v1.0.3` |
| Production Context Pack | off / null |
| Staging Contextual Call1 | `parallel-life-call-1-v1.1.9-exp` |
| Staging runtime | `parallel-life-runtime-v1.1.9-exp` |
| This audit modified code? | **No** |

---

## Appendix — failure type counts (section-level, manuscript cases only)

| Type | Approx. count | Notes |
|------|---------------|-------|
| H validator_false_negative | 3+ | family/ent/sensitive observatory |
| G public_label_mismatch | 2+ | education renames; health reported as missing |
| F Call3_deletion/structure | 1 case × many sections | health |
| E Call2/Call3 underrealization | several | education early sections; sensitive lost/protected |
| I legitimate / pre-draft safe-stop | 4 | vague + 3 pre-draft |
| A/B/C contract/evidence gen | ~0 as primary for drafted non-career leaks | contracts existed when draft ran |

End of audit.
