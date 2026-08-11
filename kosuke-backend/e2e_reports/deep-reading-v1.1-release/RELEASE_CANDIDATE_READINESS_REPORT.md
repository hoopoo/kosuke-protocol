# Parallel Life Deep Reading v1.1.11-exp — Release Candidate Readiness Audit

Generated: `2026-08-08T19:05:00+00:00` (audit from frozen staging QA artifacts)  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **not deployed / unchanged**  
Audit mode: **read-only** (no code changes, no v1.1.12, no prompt tune, no gate loosen)

## Final decision

```
V1.1 RELEASE CANDIDATE READY WITH KNOWN LIMITATIONS
```

Safety and Track A/B success criteria for a Contextual staging RC are met.
Do **not** chase 10/10 publishable. Remaining non-publishable cases are mostly
legitimate sparse stops or intermittent section-realization defects that belong
in a bounded v1.2 backlog — not blockers that invalidate the RC freeze proposal.

---

## Staging pins (verified)

| Surface | Pin |
|---------|-----|
| Runtime (Contextual) | `parallel-life-runtime-v1.1.11-exp` |
| Call 1 (Contextual) | `parallel-life-call-1-v1.1.9-exp` |
| Call 2 / 3 (Contextual) | `parallel-life-call-2/3-v1.1.11-exp` (from freeze proposal; QA runtime schema = v1.1.11-exp) |
| Staging Strict Call 1 | `parallel-life-call-1-v1.0.3` |
| Production Call 1 | `parallel-life-call-1-v1.0.3` |
| Production Context Pack | **OFF** (`production_context_pack_off=true`) |

Source QA: `e2e_reports/deep-reading-v1.1-public-qa/PUBLIC_QA_V1111_RAW.json`  
Manuscripts: `e2e_reports/deep-reading-v1.1-public-qa/v1111/*/manuscript.md`

---

## 1. 10-case final classification

Exactly one class per case.

| Case | Pub | Class | Rationale |
|------|-----|-------|-----------|
| case01_career | yes | **A — publishable expected** | Career fork + structural shift + Residue/Re-branch coherent; safety clean |
| case02_family | yes | **A — publishable expected** | Family/fertility domain preserved; soft note: present pack “会社経営” appears as present anchor |
| case03_education | yes | **A — publishable expected** | Education semantics + reconsider Re-branch realized |
| case04_romance | yes | **A — publishable expected** | Clear relational Branch Point; Lost/Residue coherent |
| case05_health | yes | **A — publishable expected** | No unsupported causality; Lost = unverifiability; safety clean |
| case06_entrepreneurship | no | **C — product defect** | Draft reached; gate `required_section_unrealized:residue` — Residue prose is present but under-realized vs validator lexicon; not an intentional safe-stop; retryable |
| case07_creative | yes | **A — publishable expected** | Creative domain OK; **quality flag** below (thin Chosen Path) |
| case08_vague | no | **D — insufficient input** | Sparse / unrecalled branch; title + thesis fail correctly; user must enrich original input |
| case09_zero_lens | no | **C — product defect** | Place-domain Chosen Path / Lost underrealized (`chosen_path`, `lost`, thesis closure); Observatory lens=0 itself is correct |
| case10_sensitive | no | **C — product defect** | Branch Point underrealized (missing 分岐/境界 lexicon); **not** a hard-safety failure; editorial variance remaining after Track B health fix on a different fixture |

**Counts:** A=6 · B=0 · C=3 · D=1  
(If forced to map vague as “legitimate safe-stop,” it is still user-actionable insufficient input — class **D** is more precise.)

---

## 2. Publishable manuscript quality (6 cases)

Safety scan across all 6 publishable bodies: no schema leakage tokens, no coaching rhetoric, no career-template leakage hits, no unsupported-causality regex hits in frozen manuscripts.

| Case | Title | Fidelity / causality | Naturalness / depth / life_read | Lost·Protected·Residue·Re-branch | Observatory | Release-quality? |
|------|-------|----------------------|----------------------------------|-----------------------------------|-------------|------------------|
| career | 残らなかった場所の物差し | High; NTT/外資 facts; no intention claims | Strong structural reading | Coherent; Re-branch present | lens=0 omit OK | **Yes** |
| family | 身体の時間として残る分かれ目 | High on fertility fork; present “会社経営” is pack-present bleed (not career template rewrite) | Good; slightly pack-anchored present | Coherent; leave_unresolved Re-branch | candidates existed; not selected — omit OK | **Yes** (soft present-bleed note) |
| education | 合格のあとに残った、もう一つの大学 | High; no career mobility inject | Good depth | Re-branch reconsider realized | candidate education-employment; not selected — omit OK | **Yes** |
| romance | 「あのまま」を残して暮らす | High; clear fork | Natural; light “のだと思う” hedge | Lost/Residue strong; Protected weaker but present | no candidates — omit OK | **Yes** |
| health | 休養を優先したあとに残る問い | High; temporal coexistence wording; no illness→outcome assert | Good restraint | Lost unverifiability OK; Re-branch preserve | body candidate; not selected — omit OK | **Yes** |
| creative | 夜と週末に続ける創作 | Facts OK | **Thin Chosen Path** (choice + present chronology; weak structural shift prose) | Lost/Protected/Residue/Re-branch OK | candidates; not selected — omit OK | **Borderline yes** — publishable but shallow Chosen Path |

**Flagged as technically publishable but below ideal release craft:**  
`case07_creative` (Chosen Path under-interpreted). Acceptable for RC with known limitation; do not block freeze solely on this.

No manuscript was found with `publishable=true` while still carrying a hard safety blocker.

---

## 3. Non-publishable cases (4)

### case06_entrepreneurship — **C product defect**

| Question | Finding |
|----------|---------|
| Exact gate | `required_section_unrealized:residue` |
| Gate correct? | **Yes** as written — Residue names the question but lacks stronger “いまも / 問いが残 / 測り方” realization cues |
| User-resolvable? | Weakly — enriching present context/question may help; primarily a draft/edit realization miss |
| Intentional Deep Reading stop? | **No** — draft completed; publication gate blocked |
| UX explanation | **Weak** — `formatBlockingReasons` falls through to raw `required_section_unrealized:residue` |

**Do not** loosen Residue gate or auto-tune to raise publishable count. Backlog: section-realization reliability for entrepreneurship Residue.

### case08_vague — **D insufficient input**

| Question | Finding |
|----------|---------|
| Exact gate | `central_thesis_not_maintained`, `title_validation_failed` |
| Gate correct? | **Yes** |
| User-resolvable? | **Yes** — supply concrete triggering event / chosen / unchosen / present question |
| Intentional stop? | **Yes** — sparse “よく覚えていない” input should not yield a full Deep Reading essay |
| UX | Title/thesis messages are humanized; retry / return-to-input available |

Manuscript collapses to a single non-locked heading `## 覚えていない分岐` — correct sparse behavior, not a label-mutation regression (required locked outline never earned).

### case09_zero_lens — **C product defect** (Observatory zero is OK)

| Question | Finding |
|----------|---------|
| Exact gate | `required_section_unrealized:chosen_path`, `required_section_unrealized:lost`, `thesis_closure_missing:chosen_path_structural_shift` |
| Gate correct? | **Yes** — Chosen Path is factual only; Lost under-realized |
| Observatory lens=0 | **Correct** (`no_structural_lens_advantage`) |
| User-resolvable? | Partially via richer place/life detail; still an editorial realization gap for `place` domain |
| Intentional stop? | Not as “zero Observatory”; stop is section realization |

### case10_sensitive — **C product defect** (safety-clean)

| Question | Finding |
|----------|---------|
| Exact gate | `required_section_unrealized:branch_point` |
| Gate correct? | **Yes** — fork is narrated as juxtaposition without 分岐/境界/境目 tokens |
| Hard safety | **0** (no `sensitive_unsupported_causality`) |
| User-resolvable? | Limited; needs stronger Branch Point realization |
| Intentional stop? | Prefer stop over unsafe causal invention — gate behavior is conservative and correct |

---

## 4. Safety audit

| Check | Result |
|-------|--------|
| hard safety failures | **0** |
| blocker with publishable=true | **0** |
| semantic_domain_leak | **0** |
| clarification infinite loop | **0** |
| HTTP 400 on normal clarification | **0** (rounds HTTP 200) |
| Observatory false-positive / forced section | **0** (all cases `omission_reason=zero_selected_observatory_lenses` when contracts present) |
| unapproved Context Pack on production | **0** (pack null / flag off) |
| production untouched | **Confirmed** (Call1 v1.0.3, schema v1.0.2, pack off) |
| Track A regressions (labels/parser/dead-end/Obs FN) | **0** |

---

## 5. UX audit

Flow audited in frontend (`ParallelLifePage.tsx`, `ModeAsk`, `confirmationUx`, `ContextPackEditor`, `ManuscriptView`, diagnostics):

| Step | Status | Notes |
|------|--------|-------|
| Branch form → Deep Reading entry | OK | Standard result preserved |
| Mode choice | OK | Explicit Strict vs Contextual; cancel returns |
| Context Pack review | OK | Contextual only; approve-gated |
| Clarification | OK | Neutral notices; answer CTA; not rose-error for gate messages |
| Confirmation | OK | Proceed vs clarify modes; pending questions force answer path |
| Draft → edit-validate | OK | Progress labels human |
| Final manuscript / export | OK | Markdown download |
| Archive/export | OK | Client download path present |
| Safe-stop messaging | **Partial** | Mapped reasons OK for title/thesis/residue_centrality; **`required_section_unrealized:*` still raw** |
| Diagnostics | OK | `DiagnosticsPanel` **DEV-only** (`import.meta.env.DEV`) |
| Dead-end confirm | OK | Clarification exit → draft path exists server-side (v1.1.10+) |
| Schema names in user copy | Mostly OK | Confirmation filter strips schema-like list items; validation fallback can still show technical codes |

**UX known limitation (not a safety blocker):** humanize `required_section_unrealized:*` / `thesis_closure_missing:*` before production Pages cutover.

---

## 6. Strict vs Contextual

| Mode | Behavior | Forced? |
|------|----------|---------|
| **Strict** | Call1 `v1.0.3`; epistemically conservative; no Context Pack | Default path “この入力だけで読む” |
| **Contextual** | Call1 `v1.1.9-exp` + runtime `v1.1.11-exp`; approved pack + BranchSemantics + Observatory-Core selection | Opt-in “背景情報も含めて読む” |

Users are **not** forced into Contextual. Staging flag enables Contextual; production keeps Context Pack **OFF**.

---

## 7. Observatory readiness

From frozen session dumps (9 cases with Call1 observatory fields):

| Metric | Value |
|--------|-------|
| Cases with ≥1 candidate lens | **7 / 9** |
| Cases with Observatory section required (`must_be_present`) | **0 / 9** |
| lens=0 / omit | **All** contracts omitted with `zero_selected_observatory_lenses` |
| Explicit zero reasons sampled | romance / zero_lens: `no_structural_lens_advantage` |
| Evidence retrieved | Often 1–4 items when candidates exist; **never promoted to selected public section** in this QA set |
| Manuscript `## 社会との接続` | **Absent** in all 10 frozen manuscripts |

**Launch assessment:** Observatory currently contributes **selection restraint + CrossLens/evidence plumbing**, not a frequent public “社会との接続” section. That is acceptable for v1.1 if marketed as optional social parallel when evidence clears thresholds — not as a guaranteed eighth section.

**v1.2 backlog:** evidence-store expansion and selection-calibration so selected lenses can appear when structurally advantageous — **without** loosening thresholds in this freeze.

---

## 8. Reliability / latency

| Metric | Observation |
|--------|-------------|
| Full 10-case wall time | **~571 s** ≈ **57 s / case** end-to-end (ground→confirm→draft→edit) |
| Targeted 4-case wall time | **~235 s** ≈ **59 s / case** |
| Clarification rounds | Typically **1**; vague **2**; no loops |
| Call1/2/3 hard failures | **None** in frozen pipelines (`error=null`, stages complete) |
| Title failures | Vague only (expected) |
| Session persistence | Staging DO-backed; FE reload recovery path present |
| Duplicate-submit | FE loading guards on approve/answer; no capacity incident recorded in this QA window |
| Staging capacity | No 503 / container_unavailable in this run |

No performance optimization recommended for RC.

---

## 9. Proposed frozen pins (do not rename until freeze approved)

**Proposal only — not applied in this audit.**

| Product | Proposed pin |
|---------|--------------|
| Product label | **Parallel Life Deep Reading v1.1.0** |
| Call 1 Contextual | `parallel-life-call-1-v1.1.9` (drop `-exp` on freeze) |
| Call 2 Contextual | `parallel-life-call-2-v1.1.11` |
| Call 3 Contextual | `parallel-life-call-3-v1.1.11` |
| Runtime Contextual | `parallel-life-runtime-v1.1.11` |
| Strict / Production path | remain `call-1-v1.0.3` + `runtime-v1.0.6` + Context Pack **OFF** |

Keep `-exp` until an explicit freeze/cutover checklist is executed.

---

## 10. Known v1.2 backlog (non-blocking for this RC decision)

1. Humanize publication-block UX for `required_section_unrealized:*` / thesis-closure codes  
2. Place-domain Chosen Path / Lost realization reliability (`zero_lens` fixture)  
3. Sensitive Branch Point realization reliability (safety-preserving)  
4. Entrepreneurship Residue realization reliability (no gate loosen)  
5. Creative Chosen Path depth (structural shift, not résumé chronology)  
6. Family/present pack bleed soft-editing (present anchors without derailing domain)  
7. Observatory evidence-store expansion + selection yield (thresholds unchanged until redesign)  
8. Optional: latency budget / progress UX for ~60s generations  

---

## 11. Product defects vs legitimate stops (summary)

| Type | Cases |
|------|-------|
| Legitimate / user-actionable stop | vague (**D**) |
| Product defect (realization variance; retry/backlog) | entrepreneurship, zero_lens, sensitive (**C**) |
| Publishable expected | career, family, education, romance, health, creative (**A**) |

**Do not** change model or loosen gates solely to convert C→A before freeze.

---

## 12. Final release decision

### V1.1 RELEASE CANDIDATE READY WITH KNOWN LIMITATIONS

**Why not “READY” (unqualified):**  
Intermittent section-realization defects remain (3 cases); UX still surfaces some technical blocker codes; Observatory public section almost never appears; creative Chosen Path is shallow.

**Why not “NOT READY”:**  
Hard safety = 0; semantic leak = 0; Track A regressions = 0; clarification loops = 0; production untouched; Strict/Contextual separation intact; targeted Track B 4/4 PASS; 6/10 publishable includes the previously failing career/education/romance/health set.

**Recommended next step (process only):**  
Execute freeze checklist → rename `-exp` pins → staging soak → production cutover with Context Pack remaining **OFF** until a separate Contextual production decision.
