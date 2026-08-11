# Deep Reading v1.1.6-exp — Thesis Closure Live NTT (STAGING)

Generated: `2026-08-08T06:25:39.403911+00:00`  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched**

## Verdict

```
PROMISING — NEEDS REVISION
```

Pipeline ok: `False` · elapsed_s: `74.27`  
Publishable: `False`  
Stop rule hit: `True`  
**No auto-tune after first live result.**

---

## 1. Chosen Path before / after

### Before (v1.1.5)
選ばれたのは、別の企業へ移る道だった。その後、いくつかの場を経験している。ここにあるのは経歴の項目の連なりだけではなく、所属先が変わるなかで仕事を重ねてきたという事実である。

### After (v1.1.6)
NTTを離れ、外資系企業へ移った。その後は複数の業界・企業を経験し、現在は自分の会社を経営している。

この経歴を並べると、一社の内部で役割を積み上げ続ける道とは異なるかたちで、仕事を続けてきたことが見えてくる。

strong: `True`

---

## 2. Chosen Path thesis linkage

```json
{
  "interpretive_claim": "振り返ると、一企業の内部で役割を積み上げ続けるから、所属が変わるたびに自分の仕事を定義し直す道へ移った（当時の意図や優劣の断定ではない）",
  "required_public_label": "選んだ道",
  "factual_choice": "外資系企業へ移る",
  "structural_shift": "一企業の内部で役割を積み上げ続けるから、所属が変わるたびに自分の仕事を定義し直す道へ移った",
  "thesis_link": "いまも残る問いの起点として、この移り方が現在の生活につながっている",
  "unresolved_tension": "",
  "present_choice": "",
  "measurement_shift": "",
  "claim_atoms": {
    "present_anchor": "自分の会社を経営している",
    "past_anchor": "外資へ移る",
    "unresolved_question": "あのとき残っていたら",
    "measurement_tension": "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだ"
  }
}
```

Closure detail: `{"structural_shift_ok": true, "thesis_link_ok": true, "excerpt": "NTTを離れ、外資系企業へ移った。その後は複数の業界・企業を経験し、現在は自分の会社を経営している。\n\nこの経歴を並べると、一社の内部で役割を積み上げ続ける道とは異なるかたちで、仕事を続けてきたことが見えてくる。"}`

---

## 3. Residue linkage

```json
{
  "interpretive_claim": "「あのとき残っていたら」が自分の会社を経営しているという状況のなかで消えないのは、外資へ移るが別の物差しとして想像されるからかもしれない。感情の断定ではなく、一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだとして残る",
  "required_public_label": "今に残った構造",
  "factual_choice": "",
  "structural_shift": "",
  "thesis_link": "",
  "unresolved_tension": "",
  "present_choice": "",
  "measurement_shift": "",
  "claim_atoms": {
    "present_anchor": "自分の会社を経営している",
    "past_anchor": "外資へ移る",
    "unresolved_question": "あのとき残っていたら",
    "measurement_tension": "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだ"
  }
}
```

Excerpt:
現在は自分の会社を経営している。いまも「あのとき残っていたら」と考えることがある。

一社のなかで役割を重ねながら蓄積を測るあり方と、企業を移りながら仕事を捉え直すあり方。その二つを並べたところに、この問いは残っている。

strong: `True`

---

## 4. Re-branch before / after

### Before (v1.1.5)
過去の選択を正解か不正解かに閉じるよりも、現在の生活のなかで何を蓄積と呼び、何によってそれを確かめるかを考える余地がある。自分の会社を経営する現在においても、一つの場で続けた時間と、移りながら重ねた経験は、単純には交換できない。その交換できなさを残したまま、これからの尺度を置いていくことが、いまの問いになる。

### After (v1.1.6)
現在は会社を経営し、複数の観測、Protocol、文章制作を行っている。この現在で、何を長期の蓄積として数えるのかは、あらためて置かれる問いになる。

残らなかった人生の答えを確定する材料はない。その不確定さを残したまま、一社のなかで積み上げることと、場を移りながら積み上げることを、別々の尺度として見ていくことはできる。

strong: `False`

---

## 5. Thesis closure result

ok: `False`  
missing: `['thesis_closure_missing:re_branch_present_choice']`

```json
{
  "chosen_path": {
    "structural_shift_ok": true,
    "thesis_link_ok": true,
    "excerpt": "NTTを離れ、外資系企業へ移った。その後は複数の業界・企業を経験し、現在は自分の会社を経営している。\n\nこの経歴を並べると、一社の内部で役割を積み上げ続ける道とは異なるかたちで、仕事を続けてきたことが見えてくる。"
  },
  "residue": {
    "ok": true,
    "excerpt": "現在は自分の会社を経営している。いまも「あのとき残っていたら」と考えることがある。\n\n一社のなかで役割を重ねながら蓄積を測るあり方と、企業を移りながら仕事を捉え直すあり方。その二つを並べたところに、この問いは残っている。"
  },
  "re_branch": {
    "ok": false,
    "excerpt": "現在は会社を経営し、複数の観測、Protocol、文章制作を行っている。この現在で、何を長期の蓄積として数えるのかは、あらためて置かれる問いになる。\n\n残らなかった人生の答えを確定する材料はない。その不確定さを残したまま、一社のなかで積み上げることと、場を移りながら積み上げることを、別々の尺度として見ていくことはできる"
  },
  "ok": false
}
```

Server blocking_reasons: `['title_validation_failed', 'required_section_unrealized:re_branch', 'thesis_closure_missing:re_branch_present_choice']`

---

## 6. Remaining resume block

resume_density: `3.0`  
markers still present: `['複数の業界', 'Protocol', '文章制作', '観測']`

---

## 7. Grammar guard result

malformed claim sections: `[]`  
residue claim: `「あのとき残っていたら」が自分の会社を経営しているという状況のなかで消えないのは、外資へ移るが別の物差しとして想像されるからかもしれない。感情の断定ではなく、一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ蓄積のあいだとして残る`  
residue_malformed (pin ground): `False`

---

## 8–10. Naturalness / Depth / life_read

| Metric | Value | Target | Met |
|--------|-------|--------|-----|
| fidelity | 10 | 10 | True |
| CVA | 9 | ≥9 | True |
| resume_density | 3.0 | ≤3 | True |
| naturalness | 7 | ≥8 | False |
| depth | 7 | ≥9 | False |
| life_read | mixed | YES | False |
| Chosen Path strong | True | true | True |
| Lost strong | True | true | True |
| Protected strong | True | true | True |
| Residue strong | True | true | True |
| Re-branch strong | False | true | False |
| thesis_closure | False | true | False |

Marker repetition: `{'測る': 1, '尺度': 1, '蓄積': 6}`

### vs v1.1.5

| Metric | v1.1.5 | v1.1.6 |
|--------|--------|--------|
| resume_density | 4.0 | 3.0 |
| naturalness | 7 | 7 |
| depth | 7 | 7 |
| life_read | mixed | mixed |
| publishable | False | False |

---

## 11. Publishable

`False`

---

## 12. Production untouched

| Check | Result |
|-------|--------|
| Prod pack flag | `None` |
| Prod Call1 | `parallel-life-call-1-v1.0.3` |
| Title validation loosened? | **No** |
| Publication blockers loosened? | **No** (thesis_closure_check added as additional gate) |
| Observatory-Core modified? | **No** |
| Context Pack facts added? | **No** |

---

## 13. Recommendation

```
PROMISING — NEEDS REVISION
```

Full manuscript:

**Title:** 残らなかった道と、残る問い

## 分岐点

28歳のとき、NTTに残るか、外資へ移るかという分岐があった。そこには、一つの企業の内部で役割を積み上げていく道と、企業を移る道が並んでいた。

## 選んだ道

NTTを離れ、外資系企業へ移った。その後は複数の業界・企業を経験し、現在は自分の会社を経営している。

この経歴を並べると、一社の内部で役割を積み上げ続ける道とは異なるかたちで、仕事を続けてきたことが見えてくる。

## 選ばなかった人生

選ばなかったのは、一企業の内部で役割を積み上げ続ける道である。その先にどのような役割や出来事があったかを示す材料はない。

ただし、その道そのものは消えない。一つの組織の時間のなかで役割を重ねていく可能性として、開いたまま残っている。

## 失ったもの

手放したものとして置けるのは、一企業内で役割を積み上げ続ける道である。同じ組織のなかで仕事の蓄積を確かめていく連続性も、その道の側にあった。

## 守られたもの

企業を移る経歴には、所属先が変わっても、自分の仕事を別の言葉で捉え直す余白を読むことができる。それは選択の優劣や成功を示すものではない。一社内での蓄積とは異なるしかたで、仕事を見直す余地である。

## 今に残った構造

現在は自分の会社を経営している。いまも「あのとき残っていたら」と考えることがある。

一社のなかで役割を重ねながら蓄積を測るあり方と、企業を移りながら仕事を捉え直すあり方。その二つを並べたところに、この問いは残っている。

## 社会との接続

これは個人の会社選択であると同時に、一社内で役割を積み上げるキャリアと、企業間を移動するキャリアの境界としても読める。日本では、長期雇用や一社内での役割の蓄積を軸とする働き方と、企業間の移動を含む働き方が併存してきた。

どちらかを正解として置くのではなく、二つの道が異なる蓄積の形を持つことを見ておきたい。

## これからの再分岐

現在は会社を経営し、複数の観測、Protocol、文章制作を行っている。この現在で、何を長期の蓄積として数えるのかは、あらためて置かれる問いになる。

残らなかった人生の答えを確定する材料はない。その不確定さを残したまま、一社のなかで積み上げることと、場を移りながら積み上げることを、別々の尺度として見ていくことはできる。


Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/thesis_closure_live_ntt/`
