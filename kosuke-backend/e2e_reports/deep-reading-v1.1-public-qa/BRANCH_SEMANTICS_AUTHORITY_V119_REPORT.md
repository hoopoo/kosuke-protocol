# Parallel Life Deep Reading v1.1.9-exp — Branch Semantics Authority Report

Generated: `2026-08-08T08:54:56.876220+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**  

## Verdict

```
V1.1.9 LEAK/LOOP FIXED — section realization still blocks many cases
```

## 1. Downstream career leak source (v1.1.8 root)

- `_has_employment_regime` / Chosen Path `structural_shift` treated Context Pack
  `career_history` / `current_work` as template authority.
- Education/creative BranchSemantics domain could be `mixed` while career
  mobility copy (`所属が変わるたびに自分の仕事を定義し直す`) was still injected.

## 2. Domain authority rule (v1.1.9)

- Primary semantic source: **BranchSemantics**
- `allows_career_product_logic(sem)` required for career templates
- Pack employment = `background_employment_context` only
- If `domain ∈ non-career` OR `changed_dimension` not employment-related →
  employment helpers must not inject redefine-work / salary / accumulation framing

## 3. Education before / after

```json
{
  "before_domain": "mixed",
  "after_domain": "education",
  "before_tension": "「その大学へ進学すること」と「別の大学へ進学すること」がいまも並んで残る緊張",
  "after_tension": "「その大学へ進学すること」側の進路上の自己と、「別の大学へ進学すること」側の別の形成のあいだ",
  "before_leaks": [
    "education_auto_career_mobility",
    "unexplained_career_template_leakage"
  ],
  "after_leaks": [],
  "before_class": "HARD_FAIL",
  "after_class": "GATE_BLOCKED",
  "after_chosen_shift": "その大学へ進学することという選択が、教育の機会／制度上の進路の次元で別の組み立てを開き始めた"
}
```

v1.1.8 leak copy (`所属が変わるたびに自分の仕事を定義し直す`) is **gone**. Remaining block is section-realization / title — not semantic leakage.

## 4. Creative before / after

```json
{
  "before_domain": "mixed",
  "after_domain": "creative",
  "before_tension": "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだ",
  "after_tension": "「会社員を続けながら創作を副業として続けること」側の生計と表現の配分と、「創作を本業にすること」側の未完の表現生活のあいだ",
  "before_leaks": [
    "unexplained_career_template_leakage"
  ],
  "after_leaks": [],
  "before_class": "HARD_FAIL",
  "after_class": "PASS_SAFE_STOP",
  "after_chosen_shift": "会社員を続けながら創作を副業として続けることという選択が、表現に割く時間／生計との配分の次元で別の組み立てを開き始めた"
}
```

Career mobility templates removed. Clarification no longer infinite-loops; session exits to `ready_for_user_confirmation` (structurally sufficient proceed) rather than stuck `needs_additional_input`.

## 5. semantic_domain_leak diagnostics

- Cases with leaked=true: **0**

- `case01_career` domain=`career` leaked=`False` hits=`[]`
- `case02_family` domain=`family` leaked=`False` hits=`[]`
- `case03_education` domain=`education` leaked=`False` hits=`[]`
- `case04_romance` domain=`romance` leaked=`False` hits=`[]`
- `case05_health` domain=`health` leaked=`False` hits=`[]`
- `case06_entrepreneurship` domain=`career` leaked=`False` hits=`[]`
- `case07_creative` domain=`creative` leaked=`False` hits=`[]`
- `case08_vague` domain=`None` leaked=`None` hits=`None`
- `case09_zero_lens` domain=`place` leaked=`False` hits=`[]`
- `case10_sensitive` domain=`health` leaked=`False` hits=`[]`

## 6. Clarification-loop root cause

- Creative (and similar) stayed in `needs_additional_input` because gates re-asked
  equivalent present-context questions after `answer`, with no round bound.
- Approve while clarifying returned HTTP 200 (v1.1.8) but could still loop.

## 7. Clarification exit behavior

- Max rounds: **2**
- Duplicate / already-satisfied questions suppressed
- After max: structurally sufficient → proceed; else `insufficient_for_deep_reading` (HTTP 200)
- Infinite-loop suspected cases: **0**
- HTTP 400 on needs_additional_input: **0**

## 8. 10-case rerun

| Case | Domain | Pub | Leak | Clar400 | Loop | Class | Realization |
|------|--------|-----|------|---------|------|-------|-------------|
| case01_career | career | True | - | False | False | PASS | - |
| case02_family | family | False | - | False | False | GATE_BLOCKED | validator_too_strict |
| case03_education | education | False | - | False | False | GATE_BLOCKED | manuscript_omission |
| case04_romance | romance | False | - | False | False | PASS_SAFE_STOP | claim_weak |
| case05_health | health | False | - | False | False | GATE_BLOCKED | claim_weak |
| case06_entrepreneurship | career | False | - | False | False | GATE_BLOCKED | validator_too_strict |
| case07_creative | creative | False | - | False | False | PASS_SAFE_STOP | claim_weak |
| case08_vague | None | False | - | False | False | GATE_BLOCKED | claim_weak |
| case09_zero_lens | place | False | - | False | False | PASS_SAFE_STOP | claim_weak |
| case10_sensitive | health | False | - | False | False | GATE_BLOCKED | manuscript_omission |

## 9. Publishable count

**1 / 10**

## 10. Remaining section-realization failures

```json
{
  "case02_family": {
    "applicable": true,
    "primary": "validator_too_strict",
    "all": [
      "validator_too_strict"
    ],
    "blocking_reasons": [
      "required_section_unrealized:observatory"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": true,
      "residue": true,
      "observatory": true,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "malformed_claims": [],
    "career_leaks": []
  },
  "case03_education": {
    "applicable": true,
    "primary": "manuscript_omission",
    "all": [
      "manuscript_omission",
      "validator_too_strict"
    ],
    "blocking_reasons": [
      "title_validation_failed",
      "required_section_unrealized:branch_point",
      "required_section_unrealized:chosen_path",
      "required_section_unrealized:lost",
      "required_public_label_missing:protected:守られたもの",
      "required_public_label_missing:residue:今に残った構造",
      "required_section_unrealized:re_branch",
      "thesis_closure_missing:chosen_path_structural_shift",
      "thesis_closure_missing:residue_unresolved_question",
      "thesis_closure_missing:re_branch_present_choice",
      "re_branch_missing_released_alternative"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": false,
      "residue": false,
      "observatory": true,
      "re_branch": false,
      "re_branch_omitted_valid": false
    },
    "malformed_claims": [],
    "career_leaks": []
  },
  "case05_health": {
    "applicable": true,
    "primary": "claim_weak",
    "all": [
      "claim_weak"
    ],
    "blocking_reasons": [
      "required_public_label_missing:branch_point:分岐点",
      "required_public_label_missing:chosen_path:選んだ道",
      "required_public_label_missing:unchosen_life:選ばなかった人生",
      "required_public_label_missing:lost:失ったもの",
      "required_public_label_missing:protected:守られたもの",
      "required_public_label_missing:residue:今に残った構造",
      "required_public_label_missing:observatory:社会との接続",
      "thesis_closure_missing:chosen_path_structural_shift",
      "thesis_closure_missing:residue_unresolved_question"
    ],
    "section_realization": {
      "branch_point": false,
      "chosen_path": false,
      "unchosen_life": false,
      "lost": false,
      "protected": false,
      "residue": false,
      "observatory": false,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "malformed_claims": [],
    "career_leaks": []
  },
  "case06_entrepreneurship": {
    "applicable": true,
    "primary": "validator_too_strict",
    "all": [
      "validator_too_strict"
    ],
    "blocking_reasons": [
      "required_section_unrealized:observatory"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": true,
      "residue": true,
      "observatory": true,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "malformed_claims": [],
    "career_leaks": []
  },
  "case08_vague": {
    "applicable": true,
    "primary": "claim_weak",
    "all": [
      "claim_weak",
      "validator_too_strict"
    ],
    "blocking_reasons": [
      "central_thesis_not_maintained",
      "title_validation_failed"
    ],
    "section_realization": {
      "branch_point": false,
      "chosen_path": false,
      "unchosen_life": false,
      "lost": false,
      "protected": false,
      "residue": false,
      "observatory": false,
      "re_branch": false,
      "re_branch_omitted_valid": false
    },
    "malformed_claims": [],
    "career_leaks": []
  },
  "case10_sensitive": {
    "applicable": true,
    "primary": "manuscript_omission",
    "all": [
      "manuscript_omission"
    ],
    "blocking_reasons": [
      "required_section_unrealized:lost",
      "required_section_unrealized:protected",
      "required_section_unrealized:observatory"
    ],
    "section_realization": {
      "branch_point": true,
      "chosen_path": true,
      "unchosen_life": true,
      "lost": true,
      "protected": false,
      "residue": true,
      "observatory": true,
      "re_branch": true,
      "re_branch_omitted_valid": false
    },
    "malformed_claims": [],
    "career_leaks": []
  }
}
```

## 11. Production untouched confirmation

- Production Call1: `parallel-life-call-1-v1.0.3`
- Production pack: `None` (must be false/null)
- production_context_pack_off: `True`
- Staging Contextual Call1: `parallel-life-call-1-v1.1.9-exp`
- Staging schema: `parallel-life-runtime-v1.1.9-exp`

## 12. Recommendation

**Primary success signals met:** career semantic leakage = 0, clarification infinite/loop = 0.

Stop auto-tune for leak/loop. Next work (separate track, no gate loosening):

1. Section realization quality for education / health / sensitive (manuscript omission + public labels)
2. Observatory realization false-negatives (`required_section_unrealized:observatory` while section present)
3. Creative/romance/zero-lens: clarification exit → confirm works; improve path from confirm → draft without re-entering soft blockers

Do **not** loosen title validation or publication gates.

## Summary metrics

```json
{
  "cases": 10,
  "publishable": 1,
  "gate_blocked": 6,
  "hard_fails": 0,
  "career_leak_cases": 0,
  "clarification_http_400": 0,
  "clarification_infinite_loops": 0,
  "semantic_domain_leak_cases": 0
}
```
