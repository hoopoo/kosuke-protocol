# Parallel Life Deep Reading v1.1.10-exp — Deterministic Realization Report

Generated: `2026-08-08T09:41:13.323929+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**  

## Verdict

```
V1.1.10 DETERMINISTIC TARGETS MET — editorial failures remain (Track B not started)
```

## 1. Observatory FN root cause / fix

- **Root cause (v1.1.9):** Observatory realization used employment-oriented keyword expectations;
  family / entrepreneurship prose that realized social-parallel meaning still failed.
- **Fix:** evidence/claim/variant-aware `_observatory_realized`; contract stores
  `supporting_observatory_evidence_ids` + `acceptable_semantic_variants`;
  `must_be_present` only when selected lenses > 0 (lens=0 → omit, no FN).
- Live Observatory FN count: **0**

## 2. Locked-label fix

- Public labels are immutable structural contracts.
- Alias map restores literary renames (e.g. 残されたもの → 守られたもの).
- Live locked-label mutations: **0**

## 3. Call3 heading preservation

- Call3 literary naturalness LLM skipped on v1.1.10 runtime.
- After each Call3 rewrite / language pass: `restore_locked_section_manuscript`
  (Call2 markdown = fallback SoT for required meanings).

## 4. Parser behavior

- Valid: line-start `## <locked label>`.
- Normalize: inline `##`, missing space, trailing `。`, alias labels.
- Pipeline prefers parse → restore → `render_locked_sections`.
- Live heading parser misses (inline/period forms remaining): **0**

## 5. Education compression fix

- Required-section meaning preservation: if Call3 prose loses interpretive core,
  restore that section body from Call2 fallback.
- No education semantic rewrite.

## 6. Clarification exit state machine

```
needs_additional_input → clarification_answered → reevaluate_grounding
→ ready_for_user_confirmation → confirmed → ready_for_draft → draft_generation
```

- Soft thesis bounce after max rounds + structurally sufficient → `ready_for_draft`
  (`clarification_exit=sufficient_for_deep_reading`).
- Structurally insufficient → `insufficient_for_deep_reading` (HTTP 200).
- No confirm dead-end without draft route.
- Live clarification dead-ends: **0**

## 7. Targeted 7-case rerun

| Case | Pub | ObsFN | LabelMut | Parser | DeadEnd | Draft | Status | Class |
|------|-----|-------|----------|--------|---------|-------|--------|-------|
| case02_family | True | False | False | False | False | True | ready_for_draft | PASS |
| case03_education | False | False | False | False | False | True | ready_for_draft | GATE_BLOCKED |
| case04_romance | False | False | False | False | False | True | ready_for_draft | GATE_BLOCKED |
| case05_health | False | False | False | False | False | True | ready_for_draft | HARD_FAIL |
| case06_entrepreneurship | True | False | False | False | False | True | ready_for_draft | PASS |
| case07_creative | True | False | False | False | False | True | ready_for_draft | PASS |
| case09_zero_lens | True | False | False | False | False | True | ready_for_draft | PASS |

## 8. Sensitive deterministic-only result

```json
{
  "case_id": "case10_sensitive",
  "publishable": true,
  "deterministic": {
    "observatory_required": false,
    "observatory_omission_reason": "zero_selected_observatory_lenses",
    "observatory_unrealized_block": false,
    "observatory_false_negative": false,
    "locked_label_mutation": false,
    "alias_headings_raw": [],
    "parsed_locked_labels": [
      "分岐点",
      "選んだ道",
      "選ばなかった人生",
      "失ったもの",
      "守られたもの",
      "今に残った構造",
      "これからの再分岐"
    ],
    "heading_parser_inline_miss": false,
    "heading_parser_period_form": false,
    "clarification_dead_end": false,
    "draft_reached": true,
    "final_status": "ready_for_draft",
    "clarification_exit": null
  },
  "blocking": [],
  "note": "Editorial Lost/Protected left for Track B"
}
```

- Editorial Lost/Protected underrealization left for Track B (not tuned here).

## 9. Full 10-case rerun (v1.1.9 → v1.1.10)

| Case | v119 Pub | v1110 Pub | ObsFN | LabelMut | DeadEnd | Class |
|------|----------|-----------|-------|----------|---------|-------|
| case01_career | True | False | False | False | False | GATE_BLOCKED |
| case02_family | False | True | False | False | False | PASS |
| case03_education | False | False | False | False | False | GATE_BLOCKED |
| case04_romance | False | False | False | False | False | GATE_BLOCKED |
| case05_health | False | False | False | False | False | HARD_FAIL |
| case06_entrepreneurship | False | True | False | False | False | PASS |
| case07_creative | False | True | False | False | False | PASS |
| case08_vague | False | True | False | False | False | PASS_WITH_NOTES |
| case09_zero_lens | False | True | False | False | False | PASS |
| case10_sensitive | False | True | False | False | False | PASS |

## 10. Publishable count

**6 / 10**

## 11. Remaining genuine editorial failures

```json
[
  {
    "case_id": "case01_career",
    "classification": "GATE_BLOCKED",
    "blocking": [
      "required_section_unrealized:chosen_path",
      "thesis_closure_missing:chosen_path_structural_shift"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": false,
      "residue": true,
      "observatory": false,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "call1_status": "ready_for_draft"
  },
  {
    "case_id": "case03_education",
    "classification": "GATE_BLOCKED",
    "blocking": [
      "required_section_unrealized:re_branch",
      "thesis_closure_missing:re_branch_present_choice",
      "re_branch_missing_released_alternative"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": true,
      "residue": true,
      "observatory": false,
      "re_branch": false,
      "re_branch_omitted_valid": false
    },
    "call1_status": "ready_for_draft"
  },
  {
    "case_id": "case04_romance",
    "classification": "GATE_BLOCKED",
    "blocking": [
      "required_section_unrealized:branch_point"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": true,
      "residue": true,
      "observatory": false,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "call1_status": "ready_for_draft"
  },
  {
    "case_id": "case05_health",
    "classification": "HARD_FAIL",
    "blocking": [
      "unsupported_causality",
      "required_section_unrealized:lost"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": true,
      "residue": true,
      "observatory": false,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "call1_status": "ready_for_draft"
  }
]
```

## 12. Production untouched confirmation

- Production Call1: `parallel-life-call-1-v1.0.3`
- Production schema: `parallel-life-call-1-schema-v1.0.2`
- Production pack: `None` (must be false/null)
- production_context_pack_off: `True`
- Staging Call1 (keep v1.1.9-exp): `parallel-life-call-1-v1.1.9-exp`
- Staging runtime: `parallel-life-runtime-v1.1.10-exp`

## 13. Recommendation

Deterministic Track A targets met. Do **not** auto-start Track B; review remaining editorial failure matrix first.

## Summary metrics

```json
{
  "cases": 10,
  "publishable": 6,
  "gate_blocked": 3,
  "hard_fails": 1,
  "semantic_domain_leak": 0,
  "observatory_false_negatives": 0,
  "locked_label_mutations": 0,
  "heading_parser_misses": 0,
  "clarification_dead_ends": 0
}
```
