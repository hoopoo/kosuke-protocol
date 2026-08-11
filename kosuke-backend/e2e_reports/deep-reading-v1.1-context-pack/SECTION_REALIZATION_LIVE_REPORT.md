# Deep Reading v1.1.5-exp — Section Realization Live NTT (STAGING)

Generated: `2026-08-08T06:05:04.776921+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**

## Verdict

```
SECTION REALIZATION PROMISING — NEEDS REVISION
```

Pipeline ok: `False` · elapsed_s: `73.96`  
Publishable: `False`  
Stop rule hit: `True`  
Blocking: `['required_section_unrealized:chosen_path', 'required_section_unrealized:re_branch']`  
**No auto-tune after first live result.**

---

## 1. Residue builder fix

```json
{
  "claim": "「あのとき残っていたら」が自分の会社を経営しているのなかで消えないのは、外資へ移るが別の物差しとして想像されるからかもしれない。感情の断定ではなく、一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだとして残る",
  "malformed": false,
  "atoms": {
    "present_anchor": "自分の会社を経営している",
    "past_anchor": "外資へ移る",
    "unresolved_question": "あのとき残っていたら",
    "measurement_tension": "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだ"
  }
}
```

- ClaimAtoms used (`present_anchor` / `past_anchor` / `unresolved_question` / `measurement_tension`)
- No `。の` / `影響を与えている。のなかで` malformation
- Remaining polish: 「経営しているのなかで」 particle join still slightly awkward (not auto-tuned)

---

## 2. Section labels

All stable labels present:

`['分岐点', '選んだ道', '選ばなかった人生', '失ったもの', '守られたもの', '今に残った構造', '社会との接続', 'これからの再分岐']`

Missing: `[]`

---

## 3. Lost realization — **strong**

この分岐を、一つの制度の内部で時間を積み、その蓄積を確かめていく連続性から離れることとして読むことはできる。役職や評価の内容を想定する材料はない。それでも、同じ場で過去から現在までをつなぎ、自分の位置を測るための尺度は、残る道の側にあったと考えられる。

Claim: 失われたのは安定の一覧ではなく、同じ制度の時間のなかで、自分がどこまで来たかを確かめ続ける物差し（一つの制度の内部で時間を積み上げ）だったとも読める

---

## 4. Protected realization — **strong**

外資系企業への転職と、その後のいくつかの場での経験を並べると、所属先が変わっても仕事を別の言葉で捉え直す余地があった、と見ることもできる。これは優劣や成功を示すものではない。現在、自分の会社を経営しているという事実と並べたとき、一つの所属だけでは尽くせない仕事のあり方が見えてくる。

Claim: 一つの所属に人生の尺度を固定しきらず、所属先が変わっても自分の仕事を別の言葉で定義し直す余白が残った（優劣や成功の証明ではない）

---

## 5. Residue realization — **present / medium-strong**

現在は自分の会社を経営している。その現在と、かつての勤め先で勤務した過去を並べるところに、「あのとき残っていたらどうなっていたか」という問いが置かれる。この問いに答えを与える材料はない。ただ、一つの場で時間を積む道と、場を移りながら仕事を重ねる道が、同じ現在のそばに残っている。

Gate: realized. Editorial: present + question + two measures, but role/salary alternate-measurement reading is only implicit.

---

## 6. Re-branch realization — **present in prose, gate failed**

過去の選択を正解か不正解かに閉じるよりも、現在の生活のなかで何を蓄積と呼び、何によってそれを確かめるかを考える余地がある。自分の会社を経営する現在においても、一つの場で続けた時間と、移りながら重ねた経験は、単純には交換できない。その交換できなさを残したまま、これからの尺度を置いていくことが、いまの問いになる。

Claim: これからの蓄積を何で測るかを自分で選ぶ、といういま向き合う問いが残る

Validator wanted clearer 「何で測るかを自分で選ぶ」 surface form.

---

## 7. Manuscript excerpts

**Title:** 残っていたら、という問いのそばで

## 分岐点
二十八歳のとき、NTTに残るか、外資系企業へ移るかという分岐があった。かつての勤め先で勤務した後、別の企業へ転職した。この分岐は勤務先の変更であると同時に、一つの組織の内部で役割を積む道と、組織を移りながら仕事を重ねる道を並べて考える起点になる。

## 選んだ道
選ばれたのは、別の企業へ移る道だった。その後、いくつかの場を経験している。ここにあるのは経歴の項目の連なりだけではなく、所属先が変わるなかで仕事を重ねてきたという事実である。

## 選ばなかった人生
もう一方には、NTTに残り、一企業の内部で役割を積み上げ続ける道があった。役職や暮らしの細部は分からないため、その先を具体化することはできない。ただ、一つの組織の時間のなかで仕事を続ける可能性は、実現しなかった道として残る。

## 失ったもの
この分岐を、一つの制度の内部で時間を積み、その蓄積を確かめていく連続性から離れることとして読むことはできる。役職や評価の内容を想定する材料はない。それでも、同じ場で過去から現在までをつなぎ、自分の位置を測るための尺度は、残る道の側にあったと考えられる。

## 守られたもの
外資系企業への転職と、その後のいくつかの場での経験を並べると、所属先が変わっても仕事を別の言葉で捉え直す余地があった、と見ることもできる。これは優劣や成功を示すものではない。現在、自分の会社を経営しているという事実と並べたとき、一つの所属だけでは尽くせない仕事のあり方が見えてくる。

## 今に残った構造
現在は自分の会社を経営している。その現在と、かつての勤め先で勤務した過去を並べるところに、「あのとき残っていたらどうなっていたか」という問いが置かれる。この問いに答えを与える材料はない。ただ、一つの場で時間を積む道と、場を移りながら仕事を重ねる道が、同じ現在のそばに残っている。

## 社会との接続
一社の内部で役割を積み上げるキャリアと、企業間を移りながら専門性を持ち運ぶキャリアは、異なる働き方のモデルとして併存してきた。この分岐も、その二つのモデルが接する場所として読むことができる。社会的な規範が個人の選択を決めたと断言することはできないが、「残る」道と「移る」道が同じ重さでは扱われない局面はあった。

## これからの再分岐
過去の選択を正解か不正解かに閉じるよりも、現在の生活のなかで何を蓄積と呼び、何によってそれを確かめるかを考える余地がある。自分の会社を経営する現在においても、一つの場で続けた時間と、移りながら重ねた経験は、単純には交換できない。その交換できなさを残したまま、これからの尺度を置いていくことが、いまの問いになる。


### Failure excerpts

```json
[
  "chosen_path_unrealized: 「選ばれたのは、別の企業へ移る道だった。その後、いくつかの場を経験している。」— 測り方の転換が薄い / resume-ish",
  "re_branch_gate_miss: 「何によってそれを確かめるか」「これからの尺度を置いていく」— claim『何で測るかを自分で選ぶ』に近いが validator 未達",
  "resume_density=4: employer/org enumeration remains (NTT/外資/別の企業/いくつかの場)",
  "residue_claim_grammar: 「経営しているのなかで」— atoms OK but particle join still slightly off"
]
```

---

## 8–11. Scores

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | 10 | 10 | True |
| CVA | 9 | ≥9 | True |
| resume_density | 4.0 | ≤3 | False |
| naturalness | 7 | ≥8 | False |
| depth | 7 | ≥9 | False |
| life_read | mixed | YES | False |
| Lost | strong | strong | True |
| Protected | strong | strong | True |
| Residue | medium-strong | strong | Partial |
| Re-branch | present / gate miss | present | Partial |

### vs v1.1.4

| Metric | v1.1.4 | v1.1.5 |
|--------|--------|--------|
| resume_density | 3.0 | 4.0 |
| naturalness | 7 | 7 |
| depth | 6 | 7 |
| life_read | mixed | mixed |
| labels | unstable/missing | **all 8 present** |
| Lost/Protected | underrealized | **strong** |
| Re-branch | omitted | **present (gate miss)** |

---

## 12. Production untouched

| Check | Result |
|-------|--------|
| Prod pack flag | `None` |
| Prod Call1 | `parallel-life-call-1-v1.0.3` |
| Title validation loosened? | **No** |
| Publication blockers loosened? | **No** |
| Observatory-Core modified? | **No** |

---

## 13. Recommendation

```
SECTION REALIZATION PROMISING — NEEDS REVISION
```

### Why not READY

1. `publishable=false` — `chosen_path` / `re_branch` failed required_section_realization.
2. resume_density 4 (>3).
3. naturalness/depth still short of targets.
4. Residue claim particle join polish remaining.

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/section_realization_live_ntt/`
