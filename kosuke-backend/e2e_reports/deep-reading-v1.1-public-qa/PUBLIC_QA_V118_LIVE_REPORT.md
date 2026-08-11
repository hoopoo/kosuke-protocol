# Parallel Life Deep Reading v1.1.8-exp — Staging Public QA Live Report

Generated: `2026-08-08T07:47:17.136173+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**  

## 12. Final verdict

```
V1.1.8 NOT READY
```

BranchSemantics improved cross-domain generalization: **partially yes** (family/romance/place/health semantics), **not fully** (education/creative still inherit career Chosen-Path template when employment co-text exists).

**No prompt/runtime/schema/Observatory-threshold changes during this QA. No auto-tune.**

## 1. Staging deployment

- Contextual Call1: `parallel-life-call-1-v1.1.8-exp`
- Contextual runtime/schema: `parallel-life-runtime-v1.1.8-exp`
- Context Pack enabled: `True`
- BranchSemantics present on NTT ground: `True` (domain=`career`)
- Strict Call1: `parallel-life-call-1-v1.0.3`

Pipeline confirmed:

```
Grounded → BranchSemantics → Context Pack → Observatory → MeaningCompression
→ Thesis → SectionContracts → Interpretive Claims → Call2 → Call3
```

## 2. Production untouched confirmation

- Production Call1: `parallel-life-call-1-v1.0.3`
- Production pack: `None` (must be false/null)
- production_context_pack_off flag: `True`

## 3. 10-case matrix

| Case | Domain(sem) | Pub | Fid | Nat | Depth | Life | Resume | Leak | Clar400 | Class |
|------|-------------|-----|-----|-----|-------|------|--------|------|---------|-------|
| case01_career | career | True | 10 | 9 | 9 | YES | 2.5 | - | False | PASS |
| case02_family | family | False | 10 | 9 | 8 | mixed | 0.0 | - | False | GATE_BLOCKED |
| case03_education | mixed | False | 10 | 9 | 7 | mixed | 0.0 | education_auto_career_mobility;unexplained_career_template_leakage | False | HARD_FAIL |
| case04_romance | romance | False | 10 | 9 | 8 | mixed | 1.0 | - | False | GATE_BLOCKED |
| case05_health | health | False | 10 | 9 | 8 | mixed | 0.0 | - | False | GATE_BLOCKED |
| case06_entrepreneurship | career | False | 10 | 9 | 8 | mixed | 0.0 | - | False | GATE_BLOCKED |
| case07_creative | mixed | False | 10 | None | None | n/a | 0 | unexplained_career_template_leakage | False | HARD_FAIL |
| case08_vague | None | True | 10 | 9 | 7 | mixed | 1.0 | - | False | PASS_WITH_NOTES |
| case09_zero_lens | place | False | 10 | 9 | 9 | mixed | 0.0 | - | False | GATE_BLOCKED |
| case10_sensitive | health | False | 10 | 9 | 7 | mixed | 0.0 | - | False | GATE_BLOCKED |

## 4. BranchSemantics per case

### case01_career

- **domain**: `career`
- **changed_dimension**: `制度的な所属／移動の仕方`
- **chosen_structure**: `外資系企業へ移ること`
- **unchosen_structure**: `一企業の内部で役割を積み上げ続けること`
- **central_tension**: `一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだ`
- **lost_verifiability**: `「一企業の内部で役割を積み上げ続けること」を取らなかったことで、同じ制度の時間のなかで進度を確かめ続ける道が閉じたこと`
- **protected_possibility**: `一つの所属に人生の尺度を固定しきらず、仕事を別の言葉で置き直す余白`
- **present_residue**: `「あのとき残っていたらどうなっていたか」がいまも残るのは、一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだが消えていないからかもしれない`
- **possible_rebranch_modes**: `['observe', 'leave_unresolved', 'reconsider']`
- **sensitive_boundaries**: `[]`

### case02_family

- **domain**: `family`
- **changed_dimension**: `家族のかたち／身体と治療の選択`
- **chosen_structure**: `妻と息子と三人で暮らす人生を続けること`
- **unchosen_structure**: `二人目を目指して治療を続けること`
- **central_tension**: `「妻と息子と三人で暮らす人生を続けること」側の家族のかたちと、「二人目を目指して治療を続けること」側の未実現の家族想像のあいだ`
- **lost_verifiability**: `「二人目を目指して治療を続けること」側にあった家族のかたちを、いまから確かめる道が閉じたこと`
- **protected_possibility**: `「妻と息子と三人で暮らす人生を続けること」を取った側に残った、いまの家族のかたちを壊さずに置く余白（妻と息子との三人家族で暮らしている）`
- **present_residue**: `「二人目を持つことへの思いが、今後の選択にどのように影響を与えるか。」がいまも残るのは、選ばなかった家族のかたちが想像として開いているからかもしれない`
- **possible_rebranch_modes**: `['leave_unresolved', 'preserve', 'observe']`
- **sensitive_boundaries**: `['no_unsupported_causality', 'no_medical_invention', 'no_invented_affect', 'no_family_outcome_invention']`

### case03_education

- **domain**: `mixed`
- **changed_dimension**: `教育の機会／制度上の進路`
- **chosen_structure**: `その大学へ進学すること`
- **unchosen_structure**: `別の大学へ進学すること`
- **central_tension**: `「その大学へ進学すること」と「別の大学へ進学すること」がいまも並んで残る緊張`
- **lost_verifiability**: `「別の大学へ進学すること」を選ばなかったことで、そこで何が続いていたかを確かめ続ける道が閉じたこと`
- **protected_possibility**: `「その大学へ進学すること」を取った側に残った、まだ閉じきらない可能性`
- **present_residue**: `「別の大学へ行っていたら、いまの仕事の感じ方は違ったか」がいまも残るのは、「その大学へ進学すること」と「別の大学へ進学すること」がいまも並んで残る緊張が消えていないからかもしれない`
- **possible_rebranch_modes**: `['observe', 'leave_unresolved', 'reconsider']`
- **sensitive_boundaries**: `[]`

### case04_romance

- **domain**: `romance`
- **changed_dimension**: `関係の継続／別れ`
- **chosen_structure**: `別れること`
- **unchosen_structure**: `一緒にいること`
- **central_tension**: `「別れること」側の単独の連続と、「一緒にいること」側の関係の連続のあいだ`
- **lost_verifiability**: `「一緒にいること」として続いていた関係の生活を、いま知る手がかりが残らないこと`
- **protected_possibility**: `「別れること」を取った側に残った、一人の生活を閉じきらずに続ける余地`
- **present_residue**: `「あのままだったらどうなっていたか」がいまも残るのは、関係の続き方についての未解決の想像が残るからかもしれない`
- **possible_rebranch_modes**: `['observe', 'revisit', 'leave_unresolved', 'not_act']`
- **sensitive_boundaries**: `['no_invented_affect', 'no_reunion_advice']`

### case05_health

- **domain**: `health`
- **changed_dimension**: `家族のかたち／身体と治療の選択`
- **chosen_structure**: `仕事量を減らして治療と休養を優先する`
- **unchosen_structure**: `以前と同じペースで働き続ける`
- **central_tension**: `「仕事量を減らして治療と休養を優先する」側の適応した生活と、「以前と同じペースで働き続ける」側の別の身体条件の想像のあいだ`
- **lost_verifiability**: `「以前と同じペースで働き続ける」側で続いていた身体条件や働き方を、いま同じようには辿れないこと`
- **protected_possibility**: `「仕事量を減らして治療と休養を優先する」を取った側に残った、身体の制約のなかで生活を続ける余地`
- **present_residue**: `「無理をして働き続けていたらどうなっていたか」がいまも残るのは、身体と生活の不確かさが問いとして残るからかもしれない`
- **possible_rebranch_modes**: `['preserve', 'observe', 'not_act']`
- **sensitive_boundaries**: `['no_unsupported_causality', 'no_medical_invention', 'no_invented_affect']`

### case06_entrepreneurship

- **domain**: `career`
- **changed_dimension**: `所有と安定／リスクへの露出`
- **chosen_structure**: `会社を辞めて自分の会社を始めること`
- **unchosen_structure**: `会社員として残ること`
- **central_tension**: `一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだ`
- **lost_verifiability**: `「会社員として残ること」を取らなかったことで、同じ制度の時間のなかで進度を確かめ続ける道が閉じたこと`
- **protected_possibility**: `一つの所属に人生の尺度を固定しきらず、仕事を別の言葉で置き直す余白`
- **present_residue**: `「会社に残っていたらどうなっていたか」がいまも残るのは、一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだが消えていないからかもしれない`
- **possible_rebranch_modes**: `['observe', 'leave_unresolved', 'reconsider']`
- **sensitive_boundaries**: `[]`

### case07_creative

- **domain**: `mixed`
- **changed_dimension**: `表現に割く時間／生計との配分`
- **chosen_structure**: `会社員を続けながら創作を副業として続けること`
- **unchosen_structure**: `創作を本業にすること`
- **central_tension**: `一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだ`
- **lost_verifiability**: `「創作を本業にすること」を取らなかったことで、同じ制度の時間のなかで進度を確かめ続ける道が閉じたこと`
- **protected_possibility**: `「会社員を続けながら創作を副業として続けること」を取った側に残った、場を移しながら生活を組み立てる余白`
- **present_residue**: `「創作を本業にしていたらどうなっていたか」がいまも残るのは、一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだが消えていないからかもしれない`
- **possible_rebranch_modes**: `['observe', 'leave_unresolved', 'reconsider']`
- **sensitive_boundaries**: `[]`

### case08_vague

- **domain**: `None`
- **changed_dimension**: `None`
- **chosen_structure**: `None`
- **unchosen_structure**: `None`
- **central_tension**: `None`
- **lost_verifiability**: `None`
- **protected_possibility**: `None`
- **present_residue**: `None`
- **possible_rebranch_modes**: `None`
- **sensitive_boundaries**: `None`

### case09_zero_lens

- **domain**: `place`
- **changed_dimension**: `暮らす場所／日常の所属`
- **chosen_structure**: `地元に残る`
- **unchosen_structure**: `都会へ出る`
- **central_tension**: `「地元に残る」側の場所での日常と、「都会へ出る」側の別の暮らしの想像のあいだ`
- **lost_verifiability**: `「都会へ出る」側の暮らしの連続を、いま体験として辿れないこと`
- **protected_possibility**: `「地元に残る」を取った側に残った、いまの場所での日常を続ける余地`
- **present_residue**: `「都会へ出ていたら、いまの日常は違ったか。」がいまも残るのは、「地元に残る」側の場所での日常と、「都会へ出る」側の別の暮らしの想像のあいだが消えていないからかもしれない`
- **possible_rebranch_modes**: `['preserve', 'reconsider', 'leave_unresolved']`
- **sensitive_boundaries**: `[]`

### case10_sensitive

- **domain**: `health`
- **changed_dimension**: `家族のかたち／身体と治療の選択`
- **chosen_structure**: `治療のため仕事を一旦離れること`
- **unchosen_structure**: `治療しながら同じ仕事を続けること`
- **central_tension**: `「治療のため仕事を一旦離れること」側の適応した生活と、「治療しながら同じ仕事を続けること」側の別の身体条件の想像のあいだ`
- **lost_verifiability**: `「治療しながら同じ仕事を続けること」側で続いていた身体条件や働き方を、いま同じようには辿れないこと`
- **protected_possibility**: `「治療のため仕事を一旦離れること」を取った側に残った、身体の制約のなかで生活を続ける余地`
- **present_residue**: `「働き続けていたら、病状や生活はどうなっていたか。」がいまも残るのは、身体と生活の不確かさが問いとして残るからかもしれない`
- **possible_rebranch_modes**: `['preserve', 'observe', 'not_act']`
- **sensitive_boundaries**: `['no_unsupported_causality', 'no_medical_invention', 'no_invented_affect']`


## 5. Clarification flow

### case01_career

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case02_family

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case03_education

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case04_romance

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case05_health

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case06_entrepreneurship

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case07_creative

- HTTP 400 on needs_additional_input: `False`
- Rounds: `8`
- Questions: `['いまの生活の具体的な場面を教えてください', 'いまの生活の具体的な場面を教えてください', 'いまの生活の具体的な場面を教えてください', 'いまの生活の具体的な場面を教えてください']`
- Duplicates: `['いまの生活の具体的な場面を教えてください', 'いまの生活の具体的な場面を教えてください', 'いまの生活の具体的な場面を教えてください']`
- Continued: `True` · final=`needs_additional_input`
- Schema leakage: `True`

### case08_vague

- HTTP 400 on needs_additional_input: `False`
- Rounds: `2`
- Questions: `['今の生活の具体的な状況について教えてください。']`
- Duplicates: `[]`
- Continued: `True` · final=`ready_for_draft`
- Schema leakage: `True`

### case09_zero_lens

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

### case10_sensitive

- HTTP 400 on needs_additional_input: `False`
- Rounds: `1`
- Questions: `[]`
- Duplicates: `[]`
- Continued: `False` · final=`ready_for_draft`
- Schema leakage: `False`

## 6. Career leakage checks

| Check | Result |
|-------|--------|
| Total leak cases | 2 |
| family / romance / education / creative / health | FAIL: case03_education, case07_creative |

## 7. Section realization

| Case | BP | Chosen | Unchosen | Lost | Prot | Res | Obs | Rebr |
|------|----|--------|----------|------|------|-----|-----|------|
| case01_career | True | True | True | True | True | True | True | True |
| case02_family | True | True | True | True | False | True | True | True |
| case03_education | True | True | True | True | False | True | True | False |
| case04_romance | True | True | True | True | False | True | True | True |
| case05_health | True | True | True | True | False | True | True | True |
| case06_entrepreneurship | True | True | True | False | False | True | True | True |
| case07_creative | False | False | False | False | False | False | False | False |
| case08_vague | False | False | False | False | False | False | False | False |
| case09_zero_lens | True | True | True | True | True | True | True | True |
| case10_sensitive | True | True | True | False | False | False | True | True |

## 8. Observatory

- **case01_career**: candidates=`['education-employment', 'after-success', 'clean-society']` selected=`[]` evidence=`['obs_ee_001', 'obs_cs_001', 'obs_as_001', 'obs_ee_002']` structures=`['employment_regime_boundary', 'normative_standard_path', 'post_achievement_question']` added_meaning=`False` zero_ok=`True`
- **case02_family**: candidates=`['body', 'after-success']` selected=`[]` evidence=`['obs_body_001', 'obs_as_001']` structures=`['embodied_or_fertility', 'family_life', 'post_achievement_question']` added_meaning=`False` zero_ok=`True`
- **case03_education**: candidates=`['education-employment']` selected=`[]` evidence=`['obs_ee_002', 'obs_ee_001']` structures=`['education_transition']` added_meaning=`False` zero_ok=`True`
- **case04_romance**: candidates=`[]` selected=`[]` evidence=`[]` structures=`[]` added_meaning=`False` zero_ok=`True`
- **case05_health**: candidates=`['body']` selected=`[]` evidence=`['obs_body_001']` structures=`['embodied_or_fertility']` added_meaning=`False` zero_ok=`True`
- **case06_entrepreneurship**: candidates=`['after-success']` selected=`[]` evidence=`['obs_as_001']` structures=`['post_achievement_question']` added_meaning=`False` zero_ok=`True`
- **case07_creative**: candidates=`['education-employment', 'after-success']` selected=`[]` evidence=`['obs_ee_001', 'obs_ee_002', 'obs_as_001']` structures=`['creative_vs_corporate']` added_meaning=`False` zero_ok=`True`
- **case08_vague**: candidates=`[]` selected=`[]` evidence=`[]` structures=`None` added_meaning=`False` zero_ok=`True`
- **case09_zero_lens**: candidates=`[]` selected=`[]` evidence=`[]` structures=`[]` added_meaning=`False` zero_ok=`True`
- **case10_sensitive**: candidates=`['body']` selected=`[]` evidence=`['obs_body_001']` structures=`['embodied_or_fertility', 'family_life']` added_meaning=`False` zero_ok=`True`

## 9. Quality scores

| Case | Fid | Nat | Depth | Life | Resume | CVA | Personal | Social | Thesis | TitleQ |
|------|-----|-----|-------|------|--------|-----|----------|--------|--------|--------|
| case01_career | 10 | 9 | 9 | YES | 2.5 | 8.7 | 8 | 5 | 8 | 8 |
| case02_family | 10 | 9 | 8 | mixed | 0.0 | 8.3 | 8 | 5 | 8 | 8 |
| case03_education | 10 | 9 | 7 | mixed | 0.0 | 8.0 | 8 | 5 | 5 | 8 |
| case04_romance | 10 | 9 | 8 | mixed | 1.0 | 8.3 | 8 | 5 | 8 | 8 |
| case05_health | 10 | 9 | 8 | mixed | 0.0 | 8.3 | 8 | 5 | 8 | 8 |
| case06_entrepreneurship | 10 | 9 | 8 | mixed | 0.0 | 8.3 | 8 | 5 | 5 | 8 |
| case07_creative | 10 | None | None | n/a | 0 | None | None | None | None | None |
| case08_vague | 10 | 9 | 7 | mixed | 1.0 | 7.0 | 5 | 3 | 5 | 8 |
| case09_zero_lens | 10 | 9 | 9 | mixed | 0.0 | 8.7 | 8 | 5 | 8 | 8 |
| case10_sensitive | 10 | 9 | 7 | mixed | 0.0 | 8.0 | 8 | 5 | 5 | 8 |

## 10. v1.1.7 comparison

```json
{
  "available": true,
  "v117_verdict": "V1.1 PROMISING — NEEDS TARGETED FIXES",
  "publishable": {
    "v117": 1,
    "v118": 2
  },
  "gate_blocked": {
    "v117": 7,
    "v118": 6
  },
  "clarification_failures": {
    "v117_incomplete_or_confirm": 4,
    "v118_http_400": 0
  },
  "career_template_leakage": {
    "v117": "not_measured",
    "v118": 2
  },
  "naturalness_pub_ge8": {
    "v117": 1,
    "v118": 2
  },
  "depth_pub_ge8": {
    "v117": 0,
    "v118": 1
  },
  "life_read_yes": {
    "v117": 0,
    "v118": 1
  },
  "observatory_zero_all": {
    "v117": true,
    "v118": true
  }
}
```

## 11. Hard failures

- Hard-fail cases: `['case03_education', 'case07_creative']`
- Clarification HTTP 400: `-`
- Career leaks: `['case03_education', 'case07_creative']`
- Gate-blocked: `['case02_family', 'case04_romance', 'case05_health', 'case06_entrepreneurship', 'case09_zero_lens', 'case10_sensitive']`
- Safe-stops: `-`

## Recommendation

```
V1.1.8 NOT READY
```

### Why not READY / why still promising

| Axis | v1.1.7 | v1.1.8 | Notes |
|------|--------|--------|-------|
| Clarification HTTP 400 | romance/creative treated as error | **0** | Fixed as UX/state |
| family career-template | Lost/Protected/Chosen careerized | **0 leak** | BranchSemantics domain=`family` correct |
| romance career-template | stopped at confirm 400 | **0 leak**; manuscript gate-blocked | Semantics correct |
| place / health semantics | careerized | domain-correct Lost/Protected | Realization still gate-blocks |
| NTT career | strong | **publishable + life_read=YES** | Not degraded |
| education | career mobility claim | **still** Chosen Path 「仕事を定義し直す」 | `_has_employment_regime` true via pack `career_history`/`current_work` |
| creative | confirm 400 | Semantics mixed + Chosen Path career template; stayed `needs_additional_input` (HTTP 200) | Employment co-presence still overrides creative domain in contracts |
| publishable | 1/10 | **2/10** | career + vague |
| gate-blocked | 7 | 6 | Section realization still brittle |
| Observatory selected | 0 all | 0 all | Candidates improved (body/family); thresholds unchanged |

### Remaining hard blockers (do not patch in this run)

1. **Chosen Path closure** still falls back to employment “定義し直す” when pack/facts contain work language — even if BranchSemantics.domain is education/creative/mixed.
2. **Section realization / observatory label** still blocks many otherwise safer manuscripts.
3. Creative clarification loop can stall on repeated “いまの生活…” without progressing to draft (HTTP 200 correct; product UX still weak). Harness `schema_leakage=True` on clarification JSON is largely response-metadata false positive (`source_field`), not manuscript prose.

### Cross-domain generalization assessment

BranchSemantics **did** stop the worst v1.1.7 failure mode for family/romance/place (no more fertility→「役職や年収」 / local-stay→「仕事を定義し直す」 in semantics).  
It **did not yet** fully quarantine career product logic from SectionContract Chosen Path when employment evidence co-occurs. Therefore release candidate is **not** justified.

Artifacts: `e2e_reports/deep-reading-v1.1-public-qa/PUBLIC_QA_V118_LIVE_REPORT.md` · `PUBLIC_QA_V118_RAW.json` · `v118/<case>/`
