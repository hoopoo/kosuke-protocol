# Deep Reading v1.1.2-exp — Observatory-Core A/B/C

Generated: `2026-08-08T04:29:13.788141+00:00`  
Production: **unchanged** (Strict v1.0.2 / Context Pack flag off in prod)

## Verdict

```
OBSERVATORY CORE PROMISING — NEEDS REVISION
```

Structural pre-thesis targets met offline; live staging manuscript redeploy still required before Public QA.

Stop signals: `none`

---

## 1. Architecture implemented

Contextual experimental pipeline:

```
Branch Facts + Approved Context Pack
→ Candidate Lens Selection (structural, 0–4)
→ Observatory Evidence Retrieval (≤6 curated)
→ CrossLensRelations (non_causal_parallel default)
→ Relevant Context Selection
→ Meaning Compression (personal/social/present/unresolved)
→ Central Thesis
→ Lost / Protected / Residue / Re-branch
→ Manuscript (Observatory section omitted when relations already carry meaning)
```

Pins:
- Call1: `parallel-life-call-1-v1.1.2-exp`
- Runtime: `parallel-life-runtime-v1.1.2-exp`
- Manifest: `PRODUCTION_MANIFEST_v1.1.2-exp.json`
- Strict / Production: unchanged

---

## 2. Curated evidence store

| id | lens_id | structural_pattern (short) | source |
|----|---------|----------------------------|--------|
| `obs_ee_001` | `education-employment` | 日本型の長期雇用・一社内での役割蓄積モデルと、企業間移動を前提とするキャリアモデルが併存してきた… | `kosuke-backend/app/observatory_lenses.py:education-employment` |
| `obs_ee_002` | `education-employment` | 教育から就労への移行や配属・転勤の制度が、仕事だけでなく住む場所や独立のタイミングまで同時に条件づけることがある… | `kosuke-backend/app/observatory_lenses.py:education-employment` |
| `obs_ms_001` | `market-signals` | 住まい・収入・地域の労働市場・世帯形成の条件が、個人の意思だけでは決めきれない生活の可否を形づくる… | `kosuke-backend/app/observatory_lenses.py:market-signals` |
| `obs_ms_002` | `market-signals` | 転職・転居に伴う収入リスクと移動コストが、『残る／移る』の分岐の重さを経済条件として左右しうる… | `kosuke-backend/app/observatory_lenses.py:market-signals` |
| `obs_cs_001` | `clean-society` | 『普通はこうするものだ』という規範が、一社に留まり役割を積む道を標準として選択の幅を静かに狭めることがある… | `kosuke-backend/app/observatory_lenses.py:clean-society` |
| `obs_body_001` | `body` | 分岐は思考上の選択だけでなく、疲れ・回復・ケアなど身体で経験された時間でもある… | `kosuke-backend/app/observatory_lenses.py:body` |
| `obs_as_001` | `after-success` | 達成や評価のあとに残る問いは、達成前の問いとは形が違い、承認だけでは閉じない生活の問いが残ることがある… | `kosuke-backend/app/observatory_lenses.py:after-success` |
| `obs_pp_001` | `protocol-publishing` | 一つの分岐を、似た年齢・就労形態・時代条件の匿名記録と並べると、個人選択の背後に社会的パターンが見えることがある（実名なし・比較軸のみ）… | `kosuke-backend/app/observatory_lenses.py:protocol-publishing` |


Total items: **8** (repository-grounded; no invented observations)

---

## 3. NTT lens selection (C)

Structures: `['employment_regime_boundary', 'normative_standard_path', 'post_achievement_question']`  
Candidates: `['education-employment', 'after-success', 'clean-society']`  
Evidence: `['obs_ee_001', 'obs_cs_001', 'obs_as_001', 'obs_ee_002']`  

Anti-promo check: `protocol-publishing` **not** selected despite pack mentioning Observatory / Protocol Publishing.

---

## 4. CrossLensRelations (C)

### `clr_ee_regime_001` (institutional_context, non_causal_parallel)

- personal: 一企業の内部で役割を積み上げる道を離れた
- social: 日本型の長期雇用・一社内での役割蓄積モデルと、企業間移動を前提とするキャリアモデルが併存してきた
- interpretation: 個人の会社選択であると同時に、一社内で地位を蓄積するキャリアと、企業間を移動しながら専門性を持ち運ぶキャリアの境界として読むことができる

### `clr_cs_norm_001` (cultural_context, non_causal_parallel)

- personal: 『残る』側が標準の進路として置かれていた
- social: 『普通はこうするものだ』という規範が、一社に留まり役割を積む道を標準として選択の幅を静かに狭めることがある
- interpretation: 個人の去就は、当時『普通』とされていた長期雇用パスと並べて読める（規範が強制したとは断言しない）

### `clr_as_001` (tension, non_causal_parallel)

- personal: 何かを形にしたあとも、閉じない問いが残っている
- social: 達成や評価のあとに残る問いは、達成前の問いとは形が違い、承認だけでは閉じない生活の問いが残ることがある
- interpretation: 達成の事実と、なお残る問いを並置して読める

---

## 5. NTT A/B/C scorecard

| Arm | Fidelity | Naturalness | resume_density | relation_density | CVA | Thesis | Social | Personal | Life read |
|-----|----------|-------------|----------------|------------------|-----|--------|--------|----------|-----------|
| A_v1.1.0_context_pack | 10 | 8 | 6.0 | 2.0 | 6 | 8 | 3 | 9 | mixed |
| B_v1.1.1_selection_compression | 10 | 8 | 7.0 | 0.0 | 6 | 8 | 3 | 9 | mixed |
| C_v1.1.2_observatory_core | 10 | 8 | 0.0 | 8.0 | 10 | 9 | 9 | 9 | reading |

C targets: fidelity=10, CVA≥8, resume≤4, relation≥7, social≥8, personal≥8  
C met structurally: **True**

Evaluation mode for C: `structural_offline_pre_thesis` (deterministic pre-thesis package + structural stance text; not a full live Call2/3 redeploy)

---

## 6. Thesis comparison

| Arm | Thesis |
|-----|--------|
| A | キャリアの選択が現在の自分にどのように影響を与えたか。 |
| B | 組織内役職から自己経営へと移行した選択が、今もなお影響を与えている。 |
| C | 一企業の内部で役割を積み上げる道を離れたという個人の分岐を、日本型の長期雇用・一社内での役割蓄積モデルと、企業間移動を前提とするキャリアモデルが併存してきたと並べて読むことができる。 |

C is materially stronger structurally: personal exit from internal-ladder career is **juxtaposed** with employment-regime coexistence, without claiming social change caused the resignation.

---

## 7–11. Metrics focus (C)

| Metric | C | Target |
|--------|---|--------|
| resume_density | 0.0 | ≤4 |
| relation_density | 8.0 | ≥7 |
| CVA | 10 | ≥8 |
| social_depth | 9 | ≥8 |
| personal_focus | 9 | ≥8 |

---

## 12. Other regression cases

| Case | Lenses | Relations | OK |
|------|--------|-----------|----|
| family_fertility | ['body'] | 1 | True |
| education | ['education-employment'] | 1 | True |
| creative_corporate | ['after-success', 'clean-society', 'education-employment'] | 2 | True |
| zero_lens_pen | [] | 0 | True |


Zero-lens case remains valid (blue pen). Fertility selects `body` without forcing employment lenses.

---

## 13. Privacy

- Observatory store contains only editorial/public structural patterns with source refs.
- No NTT / user biography stored in ObservatoryEvidence.
- Pack project lines do not select `protocol-publishing`.

---

## 14. Stale-evidence handling

- `market-signals` items marked `time_sensitive` with `as_of`.
- Freshness gate excludes items older than ~3 years when retrieving.
- Conceptual/historical lenses (`education-employment`, `clean-society`, …) are not freshness-blocked.

---

## 15. Production unchanged confirmation

| Check | Result |
|-------|--------|
| Prod Context Pack flag | remains false in `cloudflare/api-container/wrangler.toml` `[env.production]` |
| Strict Call1 | `parallel-life-call-1-v1.0.3` |
| Strict runtime | `parallel-life-runtime-v1.0.6` |
| Title publication blockers | unchanged |
| This experiment | Contextual + `DEEP_READING_CONTEXT_PACK_ENABLED` only |

---

## 16. Recommendation

```
OBSERVATORY CORE PROMISING — NEEDS REVISION
```

Next (not done in this pass): redeploy staging container with v1.1.2-exp and run live Call2/3 NTT manuscript before any Public QA claim.

Artifacts: `e2e_reports/deep-reading-v1.1-context-pack/observatory_core_ab/`
