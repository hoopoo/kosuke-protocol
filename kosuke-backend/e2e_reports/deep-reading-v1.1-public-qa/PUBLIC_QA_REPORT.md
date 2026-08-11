# Parallel Life Deep Reading v1.1.7-exp — Staging Public QA

Generated: `2026-08-08T07:06:12.256383+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched** (v1.0.2 / pack OFF)  

## Verdict

```
V1.1 PROMISING — NEEDS TARGETED FIXES
```

**No prompt/runtime/schema/model changes during this QA. No auto-tune.**

## Pins verified

- Staging Contextual Call1: `parallel-life-call-1-v1.1.7-exp`
- Staging Contextual runtime: `parallel-life-runtime-v1.1.7-exp`
- Staging pack: `True`
- Staging Strict Call1: `parallel-life-call-1-v1.0.3`
- Production Call1: `parallel-life-call-1-v1.0.3` pack=`None`

## Batch summary

| Metric | Value |
|--------|-------|
| Cases | 10 |
| Publishable | 1 |
| Hard failures (safety) | 0 |
| Gate-blocked (non-publish) | 7 |
| Incomplete / confirm fail | 4 |
| Fidelity=10 | 5/10 |
| Publishable naturalness≥8 | 1/1 |
| Publishable depth≥8 | 0/1 |
| Publishable life_read=YES | 0/1 |
| Publishable resume≤3 | 1/1 |

## Per-case matrix

| Case | Cat | Pub | Fid | Nat | Depth | Life | Resume | Lenses | Lost | Prot | Res | Rebr | Title | Hard | Class |
|------|-----|-----|-----|-----|-------|------|--------|--------|------|------|-----|------|-------|------|-------|
| case01_career | career | False | 7 | 9 | 8 | mixed | 1.5 | 0 | True | False | True | True | True | - | GATE_BLOCKED |
| case02_family | family / fertility | False | 7 | 9 | 8 | mixed | 0.0 | 0 | True | True | False | True | True | - | GATE_BLOCKED |
| case03_education | education | False | 7 | 9 | 9 | mixed | 3.0 | 0 | True | True | True | True | False | - | GATE_BLOCKED |
| case04_romance | romance / relation | False | 10 | None | None | n/a | 0 | 0 | False | False | False | False | True | - | INCOMPLETE |
| case05_health | health / body | False | 10 | 9 | 8 | mixed | 0.0 | 0 | True | False | True | True | True | - | GATE_BLOCKED |
| case06_entrepreneurship | entrepreneurship / | False | 7 | 9 | 8 | mixed | 0.0 | 0 | True | False | True | True | True | - | GATE_BLOCKED |
| case07_creative | creative work | False | 10 | None | None | n/a | 0 | 0 | False | False | False | False | True | - | INCOMPLETE |
| case08_vague | vague or weak bran | True | 10 | 9 | 7 | mixed | 0.0 | 0 | False | False | False | False | True | - | PASS_WITH_NOTES |
| case09_zero_lens | zero-lens-appropri | False | 7 | 8 | 8 | mixed | 0.0 | 0 | False | False | True | True | True | - | GATE_BLOCKED |
| case10_sensitive | sensitive causal r | False | 10 | 9 | 8 | mixed | 0.0 | 0 | False | False | True | True | True | - | GATE_BLOCKED |

## Findings (no auto-tune)

1. **Domain robustness gap:** Outside the strong career/NTT-like path, section realization often fails (`chosen_path` / `lost` / `protected` / `observatory` / `residue` labels).
2. **Confirmation UX:** Romance and creative cases stayed in `needs_additional_input` and confirm returned 400 — safe stop, but weak free-text UX.
3. **Sensitive cases:** Health/illness cases did **not** publish with causal overclaim; gates blocked. Re-branch used measurement lexicon (役職や年収) without inventing salary facts.
4. **Observatory:** Lens count was 0 across this batch — no forced lens; also little lens-added meaning on non-career cases.
5. **Publishable rate:** Low (`1/10`). Vague case published with shallow depth; not enough for release candidate.
6. **Infra:** case01 initially hit ground HTTP 500; one retry performed for QA completeness only.

## Hard-failure checklist

| Check | Result |
|-------|--------|
| Invented personal facts | OK |
| Unsupported causality on sensitive | OK |
| Unapproved Context Pack use | OK |
| Publishable=true with blockers | OK |
| Forced Observatory lens | OK |

## Targeted fix themes (do not implement in this QA)

- Broaden section realization / contracts beyond career-measurement templates
- Confirmation path for thin romance/creative branches without over-inventing
- Preserve zero-lens path while still realizing Lost/Protected/Observatory labels when present
- Title validation stability across education/retrospective phrasing

## Per-case notes

### case01_career — Career — NTT vs foreign firm

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['required_section_unrealized:chosen_path', 'thesis_closure_missing:chosen_path_structural_shift']`
- Confirmation: `[]`
- Hard: `[]` notes=`None`
- Title: 残らなかった場所の物差し

### case02_family — Family / fertility — second child question

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['required_public_label_missing:residue:今に残った構造', 'required_section_unrealized:observatory', 'thesis_closure_missing:residue_unresolved_question']`
- Confirmation: `[]`
- Hard: `[]` notes=`None`
- Title: 三人で暮らす選択と、残り続ける問い

### case03_education — Education — university choice

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['title_validation_failed', 'required_section_unrealized:branch_point']`
- Confirmation: `[]`
- Hard: `[]` notes=`None`
- Title: 別の大学を想像するとき

### case04_romance — Romance — breakup branch

- Classification: `INCOMPLETE`
- Call1 status: `None` · Call3: `None`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `[]`
- Confirmation: `['confirm_failed']`
- Hard: `[]` notes=`None`
- Title: 

### case05_health — Health / body — treatment vs work pace

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['residue_centrality_failed', 'required_section_unrealized:protected', 'required_section_unrealized:observatory']`
- Confirmation: `[]`
- Hard: `[]` notes=`['false_positive_invented_salary_lexicon_cleared']`
- Title: 在宅で続く仕事と、残る不安

### case06_entrepreneurship — Entrepreneurship — leave company to found

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['required_section_unrealized:chosen_path', 'required_section_unrealized:lost', 'required_section_unrealized:protected', 'required_section_unrealized:observatory', 'thesis_closure_missing:chosen_path_structural_shift']`
- Confirmation: `[]`
- Hard: `[]` notes=`None`
- Title: 会社を辞めたあとに残る問い

### case07_creative — Creative work — side project vs full-time craft

- Classification: `INCOMPLETE`
- Call1 status: `None` · Call3: `None`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `[]`
- Confirmation: `['confirm_failed']`
- Hard: `[]` notes=`None`
- Title: 

### case08_vague — Vague / weak branch — thin options

- Classification: `PASS_WITH_NOTES`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.0.3`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `[]`
- Confirmation: `[]`
- Hard: `[]` notes=`None`
- Title: 覚えていない選択のそばで

### case09_zero_lens — Zero-lens-appropriate — quiet local stay

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['required_section_unrealized:chosen_path', 'required_section_unrealized:lost', 'required_section_unrealized:protected', 'required_public_label_missing:observatory:社会との接続', 'thesis_closure_missing:chosen_path_structural_shift']`
- Confirmation: `[]`
- Hard: `[]` notes=`None`
- Title: 22歳の分岐と、いまの日常

### case10_sensitive — Sensitive — illness timing vs career move

- Classification: `GATE_BLOCKED`
- Call1 status: `ready_for_draft` · Call3: `parallel-life-call-3-v1.1.7-exp`
- Lenses: `[]` added_meaning=`False`
- Safety: causality=`0` bio=`0` affect=`0` coaching=`False` schema_leak=`False`
- Blocking: `['required_section_unrealized:branch_point', 'required_section_unrealized:chosen_path', 'required_section_unrealized:lost', 'required_section_unrealized:protected', 'required_section_unrealized:observatory', 'thesis_closure_missing:chosen_path_structural_shift']`
- Confirmation: `[]`
- Hard: `[]` notes=`['false_positive_invented_salary_lexicon_cleared']`
- Title: 身体の時間と働き方を選び直す

## Recommendation

```
V1.1 PROMISING — NEEDS TARGETED FIXES
```

Artifacts: `e2e_reports/deep-reading-v1.1-public-qa/`
