# Deep Reading v1.1.2-exp — Observatory-Core Live NTT (STAGING)

Generated: `2026-08-08T04:40:00+00:00` (approx; see `observatory_core_live_ntt/SUMMARY.json`)  
Staging: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Session: see `observatory_core_live_ntt/session_final.json`  
Elapsed: **37.48s** · Publishable: **true**

## Verdict

```
OBSERVATORY CORE PROMISING — NEEDS REVISION
```

**First live run only — no prompt/runtime/schema/evidence/lens-rule changes after this result.**

Blocking causality / lens-name / promo failures: **none**  
Missed targets: `resume_density` (8.0 > 3), `depth` (7 < 9), `naturalness` (5 < 8); Re-branch empty; Lost/Protected empty; subtitle résumé-like.

---

## 1. Staging deployment result

| Check | Result |
|-------|--------|
| Staging deploy | `npx wrangler deploy --env staging` OK (image `62284aab…`) |
| Container refresh | `FORCE_CONTAINER_RESTART` one-shot then **deleted** |
| Staging Contextual Call1 | `parallel-life-call-1-v1.1.2-exp` |
| Staging Contextual runtime | `parallel-life-runtime-v1.1.2-exp` |
| Staging pack flag | **true** |
| Staging Strict Call1 | `parallel-life-call-1-v1.0.3` |
| Staging Strict runtime | `parallel-life-runtime-v1.0.6` |
| Production Call1 | `parallel-life-call-1-v1.0.3` |
| Production pack flag | **false / unset** |
| Production deploy | **not performed** |
| Session leakage staging↔prod | No shared session IDs; separate Workers / DO bindings |

---

## 2. Call1 structure

| Field | Live value |
|-------|------------|
| Prompt | `parallel-life-call-1-v1.1.2-exp` |
| Runtime | `parallel-life-runtime-v1.1.2-exp` |
| Central thesis | 「一企業の内部で役割を積み上げる道を離れたという個人の分岐を、日本型の長期雇用・一社内での役割蓄積モデルと、企業間移動を前提とするキャリアモデルが併存してきたと並べて読むことができる。」 |
| Causality framing | non-causal parallel (並べて読む) |
| Observatory section lenses | `selected: []` (omitted; relations already pre-thesis) |

Meaning compression / selection: see `observatory_core_live_ntt/call1.json`.

---

## 3. Selected lenses (pre-thesis candidates)

Expected: `education-employment`, `clean-society`, `after-success`  
**Live:** same three (order: education-employment, after-success, clean-society).

| lens_id | structural_reason |
|---------|-------------------|
| education-employment | 一社内蓄積キャリアと企業間移動キャリアの境界として読める |
| after-success | 達成後にも閉じない問いが残る構造 |
| clean-society | 標準化された進路規範との緊張として読める |

Anti-promo: Protocol / 観測所 project names did **not** select `protocol-publishing`.

Evidence IDs: `obs_ee_001`, `obs_cs_001`, `obs_as_001`, `obs_ee_002` (≤6).

---

## 4. CrossLensRelations

Three relations, all `causality_status: non_causal_parallel`:

1. **clr_ee_regime_001** (`institutional_context`)  
   personal: 一企業の内部で役割を積み上げる道を離れた  
   social: 日本型の長期雇用・一社内での役割蓄積モデルと、企業間移動を前提とするキャリアモデルが併存してきた  
   interpretation: 個人の会社選択であると同時に、一社内蓄積 vs 企業間持ち運びキャリアの境界として読むことができる

2. **clr_cs_norm_001** (`cultural_context`)  
   『残る』側が標準進路として置かれていた ↔ 「普通はこうするものだ」規範（強制したとは断言しない）

3. **clr_as_001** (`tension`)  
   何かを形にしたあとも閉じない問い ↔ 達成後に残る問いの形の違い

---

## 5. Call2 result

- Title candidates (3):  
  1. 残ることと移ることのあいだ  
  2. あのとき残っていたら  
  3. 一社の時間の外側で  
- Draft published into edit-validate without schema failure.
- Observatory section omitted (no decorative lens dump).

---

## 6. Call3 result

| Item | Value |
|------|--------|
| final_title | 残ることと移ることのあいだ |
| final_subtitle | NTT東日本での勤務、企業間の移動、そして現在の経営を並べて読む |
| publishable | **true** |
| blocking_reasons | `[]` |
| Title validation | **unchanged / not loosened** |

---

## 7. Final manuscript

```markdown
### 残ることと移ることのあいだ

28歳のとき、NTT東日本に残るか、外資へ移るかという分かれ目があった。NTT東日本で勤務したのち、外資系半導体企業へ転職し、その後は複数の業界と企業を経験している。一つの企業の内部で役割を積み上げ続ける時間は、ここでは続かなかった。その経過は、日本で長期雇用と一社内での役割蓄積が一つのモデルとしてあり、企業間の移動を前提とするキャリアのモデルもまた併存してきたことと並べて見ることができる。個人の経歴を制度の結果として語る材料はないが、二つの道が同じ時代の仕事の風景に置かれている。

「普通はこうするものだ」という規範が、一社にとどまり役割を積む道を標準として置き、選択の幅を静かに狭めることがあるとも言われる。ただし、その規範がこの去就を決めたとは確認できない。ここで確かに置けるのは、残るという道と移るという道があり、後者へ進んだという順序だけである。外資系半導体企業からさらに複数業界・企業へと続く経過は、一社の内部だけで役割を重ねる時間とは異なる並びを持つ。

### 現在に残る問い

現在は自分の会社を経営し、複数の観測、Protocol、文章制作を行っている。この現在の生活と、かつてNTT東日本で勤務していた時間を並べると、その間には経歴の説明だけでは閉じない距離がある。そこに「あのとき残っていたらどうなっていたか」という問いが残る。残っていた場合の会社、役割、生活を示す材料はなく、その先を具体的な伝記にすることはできない。

問いが残ることと、会社を経営しながら観測・Protocol・文章制作を進めていることは、同じ現在の中にある。どちらかがもう一方を説明し尽くすわけではない。それでも、かつての勤務先を振り返る問いと、現在、自分の会社を経営しているという事実は並べて読むことができる。答えのない「残っていたら」の側を空白のまま保ちながら、現在の仕事は進行している。
```

Full artifact: `observatory_core_live_ntt/manuscript.md`

---

## 8. Causality result

**PASS (no blocking failure)**

Explicit non-causal language present:

- 「個人の経歴を制度の結果として語る材料はない」
- 「その規範がこの去就を決めたとは確認できない」
- Thesis uses 「並べて読む」 not 「引き起こした / 追いやった」

No transform into “employment-structure change caused leaving NTT.”

---

## 9. Lens-name exposure

**PASS**

Public body contains **no** `Clean Society` / `After Success` / `Education–Employment` / `ObservatoryEvidence` / `CrossLensRelation`.  
Insight appears; infrastructure names stay hidden.

Note: body still names user projects (`観測`, `Protocol`) as **present-life facts from Context Pack** — not lens labels. Editorial risk remains (résumé/project density), but not lens-name advertising.

---

## 10. resume_density

| Metric | Value | Target |
|--------|-------|--------|
| resume_density | **8.0** | ≤3 |
| flags | org_enumeration, industry_enumeration, project_enumeration | — |

**FAIL vs target.**  
Body still stacks: NTT東日本 → 外資系半導体 → 複数業界・企業 → 観測/Protocol/文章制作.  
Institutional reading is present, but résumé cadence is not compressed enough.

---

## 11. CVA

| Metric | Value | Target |
|--------|-------|--------|
| Context Value Add | **9** | ≥8 |

**PASS.** Pack + CrossLens clearly deepen beyond branch-only reading.

---

## 12. Personal focus

| Metric | Value | Target |
|--------|-------|--------|
| personal_focus | **9** | ≥8 |

**PASS.** Branch (残る/移る), 「あのとき残っていたら」, present self-company remain primary. Not a sociology essay.

---

## 13. Social depth

| Metric | Value | Target |
|--------|-------|--------|
| social_depth | **9** | ≥8 |

**PASS.** One-company accumulation vs portable cross-company career is explicit; clean-society “普通” appears as juxtaposition with denial of causal force.

---

## 14. Residue

Live Residue:

> 「NTT東日本で勤務した」を振り返る問いは、「現在は自分の会社を経営している」という現在の生活と並べて読むことができる

| Aspect | Assessment |
|--------|------------|
| Past ↔ present connection | Yes |
| Non-causal | Yes (並べて読む) |
| Social parallel woven in Residue statement itself | Weak (social parallel is stronger in body thesis than in Residue item) |
| Quality score | **9** (structural; slightly employer-named) |

Stronger than v1.1.1 causal “繋がっている” residue; still not the single strongest section versus book-quality pattern language.

---

## 15. Re-branch

| Aspect | Result |
|--------|--------|
| directions | **`[]` empty** |
| Score | **3** |
| Promo auto-recommend (SHIRO / Protocol grow / apps) | **none** (vacuously) |

**FAIL vs product intent.** Thesis-derived structural re-branch about *how to measure future accumulation* did not appear. Empty is safer than promo, but not editorially sufficient.

---

## 16. Title candidates

| # | Title | Thesis link | Whole-ms relevance | Résumé-like? | Over-abstract? | Company-only? |
|---|-------|-------------|--------------------|--------------|----------------|---------------|
| 1 | 残ることと移ることのあいだ | Strong (stay/leave poles) | Strong | No | No | No |
| 2 | あのとき残っていたら | Strong (present question) | Strong | No | Mildly thin alone | No |
| 3 | 一社の時間の外側で | Strong (regime exit) | Good | No | Slightly poetic/abstract | No |

---

## 17. Final title

- **Title:** 残ることと移ることのあいだ — **good** (structure, not résumé list)
- **Subtitle:** NTT東日本での勤務、企業間の移動、そして現在の経営を並べて読む — **weak / résumé-tinged** (employer + chronology enumeration undercuts title)

Title validation: unchanged; publishable true.

---

## 18. Comparison with book benchmark

| Dimension | Live Observatory-Core | Book/ChatGPT (prior qualitative) | Gap |
|-----------|------------------------|----------------------------------|-----|
| Temporal depth | Present (28歳 → 現在) but compressed chronologically via employer stack | Long institutional arc | **Partially closed** |
| Institutional reading | Clear stay-ladder vs portable career | Strong | **Materially closer** |
| Current-life return | Present; question kept open | Strong | **Closer** |
| Lost / Protected | **Empty** | Structural continuity / possibility | **Still open** |
| Residue | Non-causal juxtaposition | Pattern of re-definition | **Closer, not equal** |
| Social structure | Present without causal takeover | Strong | **Closer** |
| Re-branch | **Missing** | Measurement of accumulation | **Open** |
| Title | Strong title / weak subtitle | Metaphor/question | **Partial** |
| Life read vs summarized | **mixed** (structure + résumé cadence) | reading | **Not fully closed** |

**Is the gap materially closed?**  
**Partially — institutional / non-causal social parallel yes; résumé compression, Lost/Protected, Re-branch, and pure “life being read” cadence no.**

---

## 19. Production untouched confirmation

| Item | Status |
|------|--------|
| Production deploy | **No** |
| Prod `DEEP_READING_CONTEXT_PACK_ENABLED` | **false** (wrangler `[env.production]`) |
| Prod Call1 | `parallel-life-call-1-v1.0.3` |
| Prompts / runtime / schema / evidence store / lens rules modified after live result? | **No** |
| Staging-only experiment | **Yes** |

---

## 20. Recommendation

```
OBSERVATORY CORE PROMISING — NEEDS REVISION
```

### Exact failures (stop rule — do not auto-tune here)

1. **resume_density = 8.0** (target ≤3) — employer / industry / project enumeration in body + résumé-like subtitle  
2. **depth = 7** (target ≥9) — structural thesis present but diluted by inventory cadence  
3. **naturalness = 5** (target ≥8) — same root cause  
4. **Re-branch empty** — no thesis-derived accumulation-measure re-branch  
5. **Lost / Protected empty** — no structural continuity lost / possibility preserved sections  
6. Life-read remains **mixed**, not fully “reading”

### What already works (do not regress)

- Pre-thesis lenses + CrossLens on staging  
- Non-causal institutional parallel in thesis/body  
- No lens-name advertising  
- No SHIRO promo re-branch  
- Personal primacy preserved  
- CVA ≥8, social_depth ≥8, personal_focus ≥8  
- Production untouched  

### Scorecard

| Metric | Score | Target | Met |
|--------|-------|--------|-----|
| fidelity | 10 | 10 | yes |
| naturalness | 5 | ≥8 | **no** |
| continuity | 8 | ≥8 | yes |
| depth | 7 | ≥9 | **no** |
| CVA | 9 | ≥8 | yes |
| resume_density | 8.0 | ≤3 | **no** |
| relation_density | 8.0 | ≥7 | yes |
| social_depth | 9 | ≥8 | yes |
| personal_focus | 9 | ≥8 | yes |
| residue | 9 | high | partial |
| re-branch | 3 | high | **no** |
| title | 4 (subtitle drag) | high | partial |
| life_read | mixed | reading | **no** |

Artifacts:

- `e2e_reports/deep-reading-v1.1-context-pack/observatory_core_live_ntt/`
- `e2e_reports/deep-reading-v1.1-context-pack/live_ab/ntt_v112/`
