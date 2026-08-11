# Parallel Life v1.1 Public QA — Failure Taxonomy & Architecture Decision

Generated: 2026-08-08  
Scope: Staging Public QA v1.1.7-exp artifacts + code audit  
**No prompts/runtime/schemas/models modified. No v1.1.8. Production untouched.**

## Verdict (architecture)

```
B. ADD GENERAL BRANCH SEMANTICS LAYER
```

Secondary: clarify UX/state for `needs_additional_input` (item 8) as a separate non-editorial fix.  
Observatory evidence expansion (C) is useful later but **not** the primary blocker — career templates already overwrite non-career domains before lenses matter.

---

## 1. Failure matrix

| Case | Domain | Primary failure | Secondary failure | BranchSemantics needed | Observatory coverage | Clarification issue | Section issue | Safe-stop correctness |
|------|--------|-----------------|-------------------|------------------------|----------------------|---------------------|---------------|------------------------|
| case01_career | career | section realization | thesis closure (chosen_path structural_shift) | belonging / mobility / evaluation / continuity | store has EE/MS; selected=0 this run | no | chosen_path unrealized despite career-shaped claims | gate-block OK (no unsafe publish) |
| case02_family | family/fertility | **branch semantics** (career template on fertility) | section contract / residue label | family configuration / bodily limit / unrealized child | body evidence exists; selected=0 | no | residue missing; observatory unrealized; re_branch still salary-metric | gate-block OK; content semantically wrong upstream |
| case03_education | education | **branch semantics** + title | section realization (branch_point) | opportunity / selection / self-concept / institutional path | EE education evidence exists; selected=0 | no | title_validation_failed; career-shaped chosen_path claim | gate-block OK |
| case04_romance | romance | **clarification UX** | grounding sufficiency | intimacy / separation / relational continuity | thin; 0 lens plausible | **yes** — approve→400 | never reached manuscript | safe stop intent OK; **HTTP 400 wrong signal** |
| case05_health | health | **branch semantics** / protected template | residue_centrality + observatory | bodily constraint / uncertainty / adaptation / causal limits | body candidate evaluated=1, selected=0 | no | protected career-余白; re_branch salary metric | gate-block OK (sensitive restraint held) |
| case06_entrepreneurship | entrepreneurship | section realization | **branch semantics** (chosen_path inverted toward「定義し直す」) | ownership / stability / risk exposure | after-success/MS possible; selected=0 | no | chosen/lost/protected/observatory unrealized | gate-block OK |
| case07_creative | creative | **clarification UX** | grounding sufficiency | expression / time / livelihood / unfinished craft | thin; 0 lens plausible | **yes** — approve→400 | never reached manuscript | safe stop intent OK; **HTTP 400 wrong signal** |
| case08_vague | vague | thesis formation (weak) | depth / life_read | (minimal) leave unresolved | 0 lens correct | no | published shallow; contracts sparse | **publishable=true** — correct non-invention, weak reading |
| case09_zero_lens | local stay | **branch semantics** (inverted career shift) | section realization + observatory label | place / belonging / everyday continuity | 0 lens may be correct | no | chosen/lost/protected wrong claims; 社会との接続 missing | gate-block OK |
| case10_sensitive | illness/work | **branch semantics** + section realization | observatory | bodily constraint / care / work interruption / causal limits | body evidence exists; selected=0 | no | multi-section unrealized; re_branch still salary metric | gate-block OK (no causal publish) |

### Pipeline trace pattern (gate-blocked majority)

```
raw branch (often domain-clear)
→ grounded facts (usually OK)
→ Context Pack (approved, often current_work)
→ branch interpretation / CrossLens (employment-flavored when 残る/移る matches)
→ MeaningCompression (mixed quality; sometimes causal soft language)
→ thesis (domain-variable)
→ SectionContracts ★ FAILURE NODE
     Lost/Protected/Chosen/Re-branch synthesized with career measurement lexicon
→ interpretive claims (career-shaped even for fertility/education/health)
→ manuscript (partially resists nonsense → realization fails)
→ validation (publishable=false)
```

Romance/creative stop earlier:

```
ground → needs_additional_input
→ confirm approve (or answer then approve while still incomplete)
→ DeepReadingGenerationError → HTTP 400
```

---

## 2. Career-overfitting audit

### Smoking-gun artifacts (non-career cases)

| Case | Contract claim (excerpt) | Why fatal |
|------|--------------------------|-----------|
| family | 「二人目を目指して治療を続けることから、**所属が変わるたびに自分の仕事を定義し直す道へ移った**」 | Fertility branch rewritten as job mobility |
| education | 「別の大学へ進学することから、**所属が変わるたびに自分の仕事を定義し直す**」 | University choice → employer redefinition |
| zero-lens | 「都会へ出るから、**所属が変わるたびに自分の仕事を定義し直す道へ移った**」 | Chose *local stay*; claim invents opposite mobility structure |
| all non-vague | Re-branch: 「**役職や年収だけを唯一の到達指標にしなくてよい**」 | Salary metric forced onto family/health/romance-capable arcs |
| nearly all | branch_point: 「**勤務先の一点ではなく**、内部で積み上げる道と外へ持ち運ぶ道」 | Employer-boundary template as universal branch geometry |

### Where NTT concepts became product logic

| Concept | Location (code / prompts) | Class |
|---------|---------------------------|-------|
| accumulation / 積み上げ / 蓄積 | `build_rebranch_decision`, Call2 prompts v115–v117, realization goals | **B** career-specific promoted to generic |
| measurement / 物差し / 測り方 | `ClaimAtoms.measurement_tension`, Lost/Residue synthesizers, thesis_closure arc check | **A/B hybrid** — legitimate as *one* residue form; currently mandatory |
| role/title / 役職や年収 | `build_rebranch_decision.what_is_no_longer_required` (hard default) | **B** |
| institution / 一制度 / 一社 | Lost synthesizer, `_has_employment_regime`, observatory default claim | **B** when default; **A** when EE evidence present |
| portable value / 持ち運ぶ | branch_point / protected templates, CrossLens draft personal_structure | **B** |
| self-defined metric / 定義し直す | `_chosen_path_closure_fields`, Protected synthesizer | **B** as universal chosen-path shift |
| long-term accumulation as Re-branch | Call1 v11 prompt §25, Call2 instructions, `ReBranchDecision` | **B** |

### Detector overbreadth

`_has_employment_regime` matches `残[るり]|移[るり]|転職|…`.  
Any branch that says 「残る／移る」 (local stay, relationship leave, illness leave-work) can inherit the NTT employment geometry even when the *changed dimension* is place, intimacy, or body.

### Legitimate generics (keep)

- past path vs unrealized path  
- present question / residue  
- non-causal social parallel when evidence exists  
- factual restraint / no invented biography  
- quiet present choice vs coaching  

### Illegitimate generics (demote)

- “Lost = lost ruler of institutional progress”  
- “Protected = redefine work across affiliations”  
- “Re-branch = choose what counts as accumulation / reject salary-only metric”  
- “Chosen Path structural shift = internal ladder → portable self-definition”

---

## 3. BranchSemantics proposal (pre-thesis, domain-neutral)

Insert **before** MeaningCompression / thesis / SectionContracts:

```
Observatory-Core (unchanged selection)
→ BranchSemantics          ★ new internal layer
→ MeaningCompression / Thesis
→ SectionContracts
→ Interpretive Claims
→ Section Realization
```

### Proposed fields (no career hardcoding)

| Field | Intent |
|-------|--------|
| `branch_domain` | open enum/string: career, family, romance, education, health, place, creative, mixed, unknown |
| `changed_dimension` | what kind of life structure changed (not “job title”) |
| `chosen_structure` | structural reading of chosen path |
| `unchosen_structure` | structural reading of unrealized path (no invention) |
| `central_tension` | domain-specific tension (not always measurement) |
| `lost_verifiability` | what became unavailable / unverifiable / discontinuous |
| `protected_possibility` | what remained possible / intact / unclosed |
| `present_residue` | what of the old branch is still active in the present question |
| `rebranch_dimension` | which dimension could change *now* (or `none`) |
| `rebranch_act` | choose / reconsider / preserve / ask / leave_unresolved / not_act |
| `sensitive_boundaries` | causality/body/family limits |
| `evidence_ids` | grounding + pack + observatory ids |

SectionContracts would bind to these fields instead of NTT templates.

---

## 4. Domain semantic profiles (from QA evidence)

Derived from actual Public QA compressions + failure modes (not invented ideals):

| Domain | Dimensions seen in QA | What contracts wrongly forced |
|--------|----------------------|-------------------------------|
| career | belonging, mobility, evaluation, continuity | (templates match — still realization brittle) |
| family | family configuration, bodily/resource limits, unrealized second child | job redefinition + salary metric |
| education | opportunity, selection, institutional path, later work feeling | employer redefinition + EE career thesis bleed |
| romance | intimacy, separation, later-life divergence | stopped at clarification; would likely hit measurement residue |
| health | bodily constraint, work pace adaptation, uncertainty | protected=affiliation余白; re_branch=salary |
| entrepreneurship | ownership vs employee stability, risk/anxiety | chosen_path mobility template; lost=institutional ruler |
| creative | expression vs livelihood time split | clarification stop |
| vague | weak memory, low concreteness | correctly thin publish |
| zero-lens / place | local belonging vs urban counterfactual | inverted mobility claim |
| sensitive illness | care time, work interruption, causal limits | career Lost/Protected + salary Re-branch |

---

## 5. Lost generalization

**Current assumption:** Lost ≈ loss of an institutional progress-ruler.

**Target question:**  
“What became unavailable, unverifiable, or discontinuous because this path was not chosen?”

| Domain example | Lost should mean |
|----------------|------------------|
| career | continuous verification inside one regime (when evidenced) |
| family | unrealized family configuration / unverifiable second-child life |
| romance | continued shared life (without inventing happiness facts) |
| education | alternate formation path / unverifiable other campus life |
| health | capacity to continue prior pace (without causal medical invention) |
| creative | full-time craft continuity |

Do **not** require accumulation/measurement/institution unless BranchSemantics supports them.

---

## 6. Protected generalization

**Current assumption:** Protected ≈ “redefine work across affiliations.”

**Target question:**  
“What remained possible, intact, or unclosed because the chosen path was taken?”

| Domain example | Protected should mean |
|----------------|----------------------|
| career | definitional flexibility / non-closure in one firm identity |
| family | intact three-person life; open tenderness with son (if evidenced) |
| romance | capacity to live alone without invented closure narrative |
| health | continued livelihood in adapted form |
| creative | craft practice still alive beside employment |

---

## 7. Residue generalization

**Current assumption:** Residue ≈ alternate measurement system / 役職・年収想像.

**Target question:**  
“What part of the old branch is still active in the present question?”

May be: measurement, intimacy, family imagination, bodily uncertainty, identity, unfinished creative possibility, place counterfactual.

`ClaimAtoms.measurement_tension` should be renamed/generalized (e.g. `active_tension`) so non-measurement residues are first-class.

---

## 8. Re-branch generalization

**Current hard default:**

- what_is_no_longer_required = 役職や年収だけを唯一の到達指標にしなくてよい  
- what_can_now_be_chosen = 長期の積み重ねを自分で選び直す  

**Target:** derive from `rebranch_dimension` + `rebranch_act`.

Valid acts: choose / reconsider / preserve / ask / leave_unresolved / not_act.  
Zero Re-branch remains valid.

Examples (illustrative, not hardcoded copy):

| Domain | Possible present act |
|--------|----------------------|
| family | leave second-child question open without optimizing family size |
| health | preserve adapted pace; do not re-litigate past overwork as failure |
| romance | ask what continuity means now without reunion advice |
| creative | choose how much livelihood time craft may claim — not “pick a KPI” |
| vague | omit Re-branch |

---

## 9. Clarification → 400 root cause

### Observed

- Romance / creative: `ground` → `needs_additional_input` (valid).  
- `confirm` → HTTP **400** with generic: 「確認を完了できません。不足している情報を補ってから再度お進みください。」

### Code path

1. `DeepReadingService.confirm` on `action=approve` while `call1.status == needs_additional_input`  
2. raises `DeepReadingGenerationError(_approve_incomplete_message(...))`  
3. `main.py` maps that exception to **HTTP 400**

### Diagnosis

This is a **UX/state contract bug**, not editorial quality failure:

- Incomplete confirmation is a **normal product state**.  
- Treating it as HTTP 400 makes FE/QA harnesses look like hard errors.  
- Harness `approve_with_clarifications` may answer then approve while gates still leave `needs_additional_input` (e.g. residue/current_context/branch concreteness), so the second call legitimately refuses — but the status code is wrong for “still clarifying.”

### Proposed fix (do not mix with prompt work)

1. Prefer **HTTP 200** + session still `needs_additional_input` + structured `blocking_reason` / `missing_fields` when approve is premature.  
2. Reserve 400 for true malformed requests / contradictions / invalid actions.  
3. FE: never treat “still needs answers” as a toast error; keep clarification UI.  
4. Optionally make `answer` responses always include the next required question list explicitly.

---

## 10. Observatory zero-lens analysis

### Store reality

Curated `ObservatoryEvidence` ≈ **8** items, skewed to:

- education-employment (2)  
- market-signals (2)  
- clean-society (1)  
- body (1)  
- after-success (1)  
- protocol-publishing (1)  

Gaps: romance/intimacy, creative labor, place/migration beyond job mobility, family policy beyond body hint.

### Per-case read

| Case | Candidates / selected (session) | Likely reason 0 selected | A correct 0? or B sparse store? |
|------|----------------------------------|---------------------------|----------------------------------|
| career | sel=0 (cross_lens sometimes present) | conservative filter / structure miss this run | **B+conservative** — EE evidence exists |
| family | sel=0; body-relevant | embodied_or_fertility may not fire; contracts ignore body meaning anyway | **B** for family policy; body underused |
| education | sel=0 | education_transition under-detected vs career bleed | **B+selector** |
| romance | sel=0 | no intimacy evidence class | **A** (0 lens OK) + **B** store gap |
| health | evaluated=1, selected=0 | evidence_gate / new_meaning failed | **conservative** (body exists) |
| entrepreneurship | sel=0 | after-success/MS not selected | mixed |
| creative | sel=0 | no craft/livelihood lens evidence | **A/B** |
| vague | sel=0 | correct | **A** |
| zero-lens | sel=0 | intended | **A** |
| sensitive | sel=0 | body should compete; not selected | **conservative** |

### Conclusion

Do **not** loosen thresholds yet.  
Zero-lens was often *locally* correct, but the store is too employment-centric to help family/romance/creative — and even when body/EE evidence exists, SectionContracts still emit career measurement language. **Evidence expansion without BranchSemantics will not fix Wrong Lost/Protected/Re-branch.**

---

## 11. Architecture recommendation

### Choose **B. ADD GENERAL BRANCH SEMANTICS LAYER**

Why not A (targeted prompt fixes only)?  
Public QA shows the same career synthesizers firing across domains (`定義し直す`, `役職や年収`, employer branch_point). Prompt patches would be whack-a-mole against hardcoded Python templates in `section_contracts.py`.

Why not C first (expand Observatory)?  
Useful, but Observatory was 0 even when CrossLens/body hints existed; the blocking wrongness is SectionContract claim synthesis, not missing social prose alone.

Why not D (architecture cannot generalize)?  
The product *already* has the right abstract questions (Lost/Protected/Residue/Re-branch). They were implemented with an NTT-shaped answer key. A domain-neutral BranchSemantics layer is the missing adapter — not a full redesign of Observatory-Core or Strict production.

### Sequencing (proposal only — do not implement in this pass)

1. Spec BranchSemantics + migrate Lost/Protected/Residue/Re-branch synthesizers off NTT defaults.  
2. Fix clarification approve HTTP semantics (separate PR).  
3. Then expand ObservatoryEvidence for under-covered domains.  
4. Re-run the same 10 Public QA cases — no auto-tune mid-batch.

---

## 12. Return checklist

1. **Failure matrix** — §1  
2. **Career-overfitting audit** — §2  
3. **BranchSemantics proposal** — §3  
4. **Lost generalization** — §5  
5. **Protected generalization** — §6  
6. **Residue generalization** — §7  
7. **Re-branch generalization** — §8  
8. **Clarification 400 root cause** — §9  
9. **Observatory zero-lens analysis** — §10  
10. **Architecture recommendation** — **B**
