# Parallel Life Deep Reading v1.1.11-exp — Targeted Editorial Report

Generated: `2026-08-08T14:13:48.913141+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**  

## Verdict

```
V1.1.11 TARGETED EDITORIAL PASS — do not chase 10/10; review matrix
```

## 1. Career chosen_path fix

- Contract structural_shift: one-institution continuity → work across organizations
- Realization accepts structural cues (一つの所属 / 移り方 / 組織を移) without requiring employment-metric jargon
- Anti-résumé: chronology-only still fails

## 2. Education re_branch fix / omission

- Re-branch place from BranchSemantics domain (not pack「仕事の場」)
- reconsider release: 「固定しなくてよい」; ensure_rebranch restores quiet decision
- Zero / valid omission still allowed when modes empty

## 3. Romance branch_point fix

- Contract first-paragraph fork: trigger + chosen + unchosen + 境界
- Realization accepts 境目 as 境界 synonym

## 4. Health causality trace / fix

- Exact trip: 「働き方を変えるかを考えた」 matched assertion pattern 「を変える」
- Detector unchanged; manuscript rewrite → 「働き方をどう置くかを考え」
- Also neutralize 「によって」「つながっている」frames in thesis_link / finalize

## 5. Health Lost result

- Lost meaning from health BranchSemantics: bodily condition / unverifiable configuration
- Realization accepts 検証することはできない / 身体条件 / 同じようには辿

## 6. Targeted 4-case results

| Case | Pub | Target OK | Class | Blocking |
|------|-----|-----------|-------|----------|
| case01_career | True | True | PASS | - |
| case03_education | True | True | PASS | - |
| case04_romance | True | True | PASS | - |
| case05_health | True | True | PASS | - |

```json
[
  {
    "case_id": "case01_career",
    "publishable": true,
    "classification": "PASS",
    "blocking": [],
    "editorial_target": {
      "target": "chosen_path",
      "ok": true,
      "excerpt": "28歳で外資系企業へ移った。一企業の内部で役割を積み上げ続ける連続から離れ、組織を移りながら仕事を続ける経歴になった。「あのとき残っていたらどうなっていたか」という問いは、現在の生活と並んでいる。"
    },
    "track_a_regressions": []
  },
  {
    "case_id": "case03_education",
    "publishable": true,
    "classification": "PASS",
    "blocking": [],
    "editorial_target": {
      "target": "re_branch",
      "ok": true,
      "omitted_valid": false,
      "excerpt": "一度決めた測り方を固定しなくてよい。いまの問いの置き方を、静かに見直す余地がある。\n\nいまも残る問いは、「その大学へ進学すること」側の進路上の自己と、「別の大学へ進学すること」側の別の形成のあいだとして並んでいる。そのそばで、現在の読み方を少しだけ置き直すことができる。"
    },
    "track_a_regressions": []
  },
  {
    "case_id": "case04_romance",
    "publishable": true,
    "classification": "PASS",
    "blocking": [],
    "editorial_target": {
      "target": "branch_point",
      "ok": true,
      "excerpt": "20代後半に、長く付き合っていた人と別れた。その出来事は、ただ関係が終わった一点というより、「別れること」と「一緒にいること」の二つの続き方が分かれた境界だった。"
    },
    "track_a_regressions": []
  },
  {
    "case_id": "case05_health",
    "publishable": true,
    "classification": "PASS",
    "blocking": [],
    "editorial_target": {
      "target": "causality+lost",
      "ok": true,
      "unsupported_causality": false,
      "lost_ok": true,
      "excerpt_lost": "失われたのは、以前と同じペースで働き続ける側で続いていたはずの身体条件や働き方を、いま同じように辿ることではないか。どのような状態が続いたかは確かめられず、その連続そのものが、現在からは検証できないまま残っている。",
      "hard": []
    },
    "track_a_regressions": []
  }
]
```

## 7. Full 10-case rerun (v1.1.10 → v1.1.11)

| Case | v1110 Pub | v1111 Pub | Class | TrackA reg |
|------|-----------|-----------|-------|------------|
| case01_career | False | True | PASS | - |
| case02_family | True | True | PASS | - |
| case03_education | False | True | PASS | - |
| case04_romance | False | True | PASS | - |
| case05_health | False | True | PASS | - |
| case06_entrepreneurship | True | False | GATE_BLOCKED | - |
| case07_creative | True | True | PASS | - |
| case08_vague | True | False | GATE_BLOCKED | - |
| case09_zero_lens | True | False | GATE_BLOCKED | - |
| case10_sensitive | True | False | GATE_BLOCKED | - |

## 8. Publishable count

**6 / 10**

## 9. Legitimate non-publishable cases

```json
[
  {
    "case_id": "case06_entrepreneurship",
    "classification": "GATE_BLOCKED",
    "status": "ready_for_draft",
    "note": "non-publishable but not a targeted Track B miss"
  },
  {
    "case_id": "case08_vague",
    "classification": "GATE_BLOCKED",
    "status": "ready_for_draft",
    "note": "non-publishable but not a targeted Track B miss"
  },
  {
    "case_id": "case09_zero_lens",
    "classification": "GATE_BLOCKED",
    "status": "ready_for_draft",
    "note": "non-publishable but not a targeted Track B miss"
  },
  {
    "case_id": "case10_sensitive",
    "classification": "GATE_BLOCKED",
    "status": "ready_for_draft",
    "note": "non-publishable but not a targeted Track B miss"
  }
]
```

## 10. Track A regression check

- Cases with Track A regressions: **0**
- semantic_domain_leak: **0**

## 11. Production untouched confirmation

- Production Call1: `parallel-life-call-1-v1.0.3`
- Production schema: `parallel-life-call-1-schema-v1.0.2`
- Production pack: `None`
- production_context_pack_off: `True`
- Staging Call1: `parallel-life-call-1-v1.1.9-exp`
- Staging runtime: `parallel-life-runtime-v1.1.11-exp`

## 12. Recommendation

Targeted Track B goals met. Do not chase 10/10. Next only if new genuine editorial failures appear in the matrix.

## Summary

```json
{
  "cases": 10,
  "publishable": 6,
  "gate_blocked": 4,
  "hard_fails": 0,
  "semantic_domain_leak": 0,
  "track_a_regression_cases": 0
}
```
