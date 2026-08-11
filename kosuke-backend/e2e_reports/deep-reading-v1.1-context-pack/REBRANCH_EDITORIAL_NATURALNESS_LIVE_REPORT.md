# Deep Reading v1.1.7-exp — Re-branch Decision + Editorial Naturalness Live NTT

Generated: `2026-08-08T06:45:17.116219+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**

## Verdict

```
REBRANCH EDITORIAL READY FOR PUBLIC QA
```

Pipeline ok: `True` · elapsed_s: `59.82`  
Publishable: `True`  
Stop rule hit: `False`  
**No auto-tune. Do not create v1.1.8 automatically.**

---

## 1. ReBranchDecision

```json
{
  "unresolved_tension": "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだ",
  "present_choice": "これから何を長期の積み重ねとして認めるかを、自分で選び直す",
  "what_is_no_longer_required": "役職や年収だけを唯一の到達指標にしなくてよい",
  "what_can_now_be_chosen": "これから何を長期の積み重ねとして認めるかを、自分で選び直す",
  "evidence_ids": [
    "pack_career_history_001",
    "pack_career_history_002"
  ],
  "non_genericity_score": 0.95,
  "interpretive_claim": "役職や年収だけを唯一の到達指標にしなくてよい。これから何を長期の積み重ねとして認めるかを、自分で選び直す余地がある（優劣や成功の断定ではない）"
}
```

---

## 2. Re-branch before / after

### Before (v1.1.6)
現在は会社を経営し、複数の観測、Protocol、文章制作を行っている。この現在で、何を長期の蓄積として数えるのかは、あらためて置かれる問いになる。

残らなかった人生の答えを確定する材料はない。その不確定さを残したまま、一社のなかで積み上げることと、場を移りながら積み上げることを、別々の尺度として見ていくことはできる。

### After (v1.1.7)
一社の時間のなかで自分の進み具合を確かめる感覚と、場を移って仕事を持ち運ぶ感覚を、どちらが正しかったかで裁かない。役職や年収だけを、唯一の到達指標にしなくてよい。自分の会社を経営する現在、長い時間をかけて何を積み重ねてきたと認めるかを、自分で選び直す。残らなかった道は否定せず、現在の仕事を見直す静かな背景として置いておく。

realized: `True`  
missing: `[]`

---

## 3. Thesis closure

ok: `True`  
missing: `[]`

```json
{
  "chosen_path": {
    "structural_shift_ok": true,
    "thesis_link_ok": true,
    "excerpt": "外資系企業へ移り、一つの企業の内部で役割を重ね続ける道から、所属が変わるたびに自分の仕事を言い直す道へ進んだ。優劣を決めるための移動ではない。けれど、いま自分の会社を経営する生活のなかにも、「あのとき残っていたら」という思いが残っている。"
  },
  "residue": {
    "ok": true,
    "excerpt": "その後、複数の業界や企業を経験し、現在は自分の会社を経営している。この現在と「あのとき残っていたら」を並べると、残る道は単なる過去の選択肢ではなく、一つの場で自分の進み具合を知る、別の目印として浮かぶ。場を移りながら仕事を持ち運んできた時間と、その目印との隔たりは、いまも残っている。"
  },
  "re_branch": {
    "excerpt": "一社の時間のなかで自分の進み具合を確かめる感覚と、場を移って仕事を持ち運ぶ感覚を、どちらが正しかったかで裁かない。役職や年収だけを、唯一の到達指標にしなくてよい。自分の会社を経営する現在、長い時間をかけて何を積み重ねてきたと認めるかを、自分で選び直す。残らなかった道は否定せず、現在の仕事を見直す静かな背景として置いておく。",
    "has_choice": true,
    "has_release": true,
    "has_residue_link": true,
    "question_only": false,
    "reflection_only": false,
    "coaching": false,
    "ok": true
  },
  "arc": "closed",
  "ok": true
}
```

---

## 4. Abstract vocabulary counts

```json
{
  "counts": {
    "蓄積": 0,
    "構造": 1,
    "尺度": 0,
    "制度": 0,
    "分岐": 2,
    "選択": 1
  },
  "soft_limits": {
    "蓄積": 3,
    "構造": 4,
    "尺度": 3,
    "制度": 3,
    "分岐": 4,
    "選択": 4
  },
  "excess": {},
  "excess_total": 0,
  "thinning_recommended": false
}
```

---

## 5. Remaining résumé text

resume_density: `0.0`  
markers: `['複数の業界']`

---

## 6. Call3 editorial changes

Call3 prompt_version: `parallel-life-call-3-v1.1.7-exp`  
Deterministic ensure_rebranch + compress_resume + thin_abstract + editorial naturalness pass enabled for v1.1.7 Contextual.

Server blocking_reasons: `[]`

---

## 7–9. Scores

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | 10 | 10 | True |
| CVA | 9 | ≥9 | True |
| resume_density | 0.0 | ≤3 | True |
| naturalness | 9 | ≥8 | True |
| depth | 9 | ≥8 | True |
| life_read | YES | YES | True |
| re_branch realized | True | true | True |
| thesis_closure | True | true | True |
| publishable | True | true | True |

### vs v1.1.6

| Metric | v1.1.6 | v1.1.7 |
|--------|--------|--------|
| resume_density | 3.0 | 0.0 |
| naturalness | 7 | 9 |
| depth | 7 | 9 |
| life_read | mixed | YES |
| publishable | False | True |

---

## 10. Publishable

`True`

---

## 11. Recommendation

```
REBRANCH EDITORIAL READY FOR PUBLIC QA
```

Next step (stop condition):

```
Proceed to Public QA on staging; do not create v1.1.8 automatically.
```

Production untouched: pack=`None` call1=`parallel-life-call-1-v1.0.3`  
Title / publication gates / Observatory-Core: **unchanged**

Full manuscript:

**Title:** 残らなかった会社の時間

## 分岐点
28歳のとき、かつての勤め先に残るか、外資系企業へ移るかという分かれ目があった。それは単に勤務先を替えるかどうかではなかった。同じ組織のなかで自分の進み具合を確かめていく道と、外へ出て仕事の意味を捉え直していく道が、そこにあった。

## 選んだ道
外資系企業へ移り、一つの企業の内部で役割を重ね続ける道から、所属が変わるたびに自分の仕事を言い直す道へ進んだ。優劣を決めるための移動ではない。けれど、いま自分の会社を経営する生活のなかにも、「あのとき残っていたら」という思いが残っている。

## 選ばなかった人生
残る側には、特定の役職や出来事を想像で補わなくてもよい、一つの企業のなかで役割を重ねていく時間があった。その可能性は実現しなかった。だから成功でも失敗でもなく、別の時間の流れとして、閉じきらずに残っている。

## 失ったもの
失ったのは、安定という一語では足りない。同じ組織で過ごす時間のなかで、自分がどこまで来たかを確かめ続ける目印だったのかもしれない。仕事の変化だけでなく、過去の自分との距離も、同じ場所で読み取れたはずである。

## 守られたもの
一方で、所属先が変わっても、自分の仕事を別の言葉で定義し直す余白は残った。移動の価値を証明する話ではない。一つの所属に人生全体の判断を預け切らないあり方も、外資系企業への転職後の時間にはあった。

## 今に残った構造
その後、複数の業界や企業を経験し、現在は自分の会社を経営している。この現在と「あのとき残っていたら」を並べると、残る道は単なる過去の選択肢ではなく、一つの場で自分の進み具合を知る、別の目印として浮かぶ。場を移りながら仕事を持ち運んできた時間と、その目印との隔たりは、いまも残っている。

## 社会との接続
この去就には、一社のなかで地位や役割を重ねていく働き方と、企業を移りながら専門性を持ち運ぶ働き方が並んでいる。「残る」ことが標準の進路として見えやすい時代や場面があったとしても、それだけで個人の決定を説明することはできない。ただ、会社を選ぶという個人の決定には、二つの働き方が張り合う場所が映っている。

## これからの再分岐
一社の時間のなかで自分の進み具合を確かめる感覚と、場を移って仕事を持ち運ぶ感覚を、どちらが正しかったかで裁かない。役職や年収だけを、唯一の到達指標にしなくてよい。自分の会社を経営する現在、長い時間をかけて何を積み重ねてきたと認めるかを、自分で選び直す。残らなかった道は否定せず、現在の仕事を見直す静かな背景として置いておく。


Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/rebranch_editorial_live_ntt/`
