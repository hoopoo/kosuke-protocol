# Deep Reading v1.1.1 — Selection + Meaning Compression NTT A/B

Generated: `2026-08-08T04:05:00+00:00`  
Staging API: `https://parallel-life-api-staging.shiroandco-office.workers.dev`  
Production: **untouched** (Context Pack remains staging-only)

## Verdict

```
SELECTION+COMPRESSION PROMISING — NEEDS REVISION
```

B (v1.1.1) improves **title / reading stance** vs A (v1.1.0 résumé framing), and pins Selection+Compression runtime correctly. It does **not** yet hit targets for `resume_density ≤ 3` or `Context Value Add ≥ 8` on the live NTT run; Call1 thesis/residue still slip into causal framing.

---

## 1. Staging configuration

| Item | Value |
|------|--------|
| Contextual Call1 | `parallel-life-call-1-v1.1.1` |
| Contextual runtime | `parallel-life-runtime-v1.1.1-exp` |
| Strict / Prod | `parallel-life-call-1-v1.0.3` / `parallel-life-runtime-v1.0.6` |
| Flag | `DEEP_READING_CONTEXT_PACK_ENABLED=true` on staging only |
| Manifest | `PRODUCTION_MANIFEST_v1.1.1-exp.json` |
| Same pack as prior A/B | yes (5 approved items; no new facts) |

---

## 2. Arms

| Arm | Source |
|-----|--------|
| **A** Contextual v1.1.0 | Prior live artifact `live_ab/A_ntt/contextual_*` |
| **B** Selection+Compression v1.1.1 | Fresh staging session after container rollout |
| **C** Book/ChatGPT qualitative | Structure benchmark only (not scored for app-unavailable facts) |

---

## 3. Scorecard

| Metric | A v1.1.0 | B v1.1.1 | Target |
|--------|----------|----------|--------|
| Factual fidelity | 10 | 10 | 10 |
| resume_density (↓ better) | 6.0 | 7.0 | ≤3 |
| Thesis strength | 4 | 8 | high |
| Temporal depth | 7 | 7 | — |
| Structural depth | 5 | 5–9* | ≥9 |
| Residue | 8 | 7 | structural pattern |
| Observatory | 3 (0 lenses) | 3 (0 lenses) | 0–2 strong |
| Re-branch | 3 | 4 | thesis-derived |
| Title | 4 | 8 | non-résumé |
| Context Value Add | 8† | 7 | ≥8 |
| Life read vs summarized | mixed | summarized‡ | reading |

\* Heuristic structural_depth on B body is mixed: prose *attempts* structural reading (“社名の連なりとして見るのではなく…”) but still enumerates employers/projects → density penalty.  
† A’s CVA heuristic is inflated by pack ID presence; qualitatively A is résumé-like.  
‡ Body longer and still name-heavy despite better title.

**Targets met:** fidelity only. `resume_density≤3`, `depth≥9`, `CVA≥8` **not** met on this live B.

---

## 4. Titles

- **A:** NTTを離れた後の経歴と、残る問い / 外資系半導体企業への転職、複数業界・企業での経験、現在の会社経営  
- **B:** 残った問い、いまの会社 / NTTを離れた転職から、自己経営の現在まで  

B title is clearly less résumé-list; closer to question+present structure.

---

## 5. Qualitative excerpts

### A body (résumé cadence)

> NTT東日本で勤務した後、NTTを離れ、外資系半導体企業へ転職した。…その後、複数の業界と企業を経験した。現在は自分の会社を経営し、複数の観測、Protocol、文章制作を行っている。

### B body (better stance, still name-dense)

> 職歴を単なる社名の連なりとして見るのではなく、28歳で外へ移った時点から、その後の複数の場を経る時間として置くことができる。…残っていた場合にどのような仕事や立場になっていたかを示す材料はない。

### B Call1 thesis (still causal — soft-gate gap on this run)

> 組織内役職から自己経営へと移行した選択が、今もなお影響を与えている。

### B Residue (causal bridge)

> 選択の結果が現在の自己経営に繋がっている。

---

## 6. Selection / compression behavior (B)

- Prompt/runtime pins confirmed: **v1.1.1 / v1.1.1-exp**
- Pack facts retained: all 5 approved items (cap=5 → no demotion pressure on this pack size)
- Re-branch used `pack_current_work_004` (company) — still somewhat promotional/causal vs “scale of accumulation”
- Observatory: 0 selected (conservative gate held)
- `meaning_compression` / `manuscript_logic_ids` present in Call1 path (schema additive)

---

## 7. Book qualitative comparison (C)

| Dimension | A | B | C (book) |
|-----------|---|---|----------|
| Temporal arc | listed | listed + some framing | long institutional |
| Structural tension | weak | emerging | strong (制度内 vs 持ち運び) |
| Residue | bio/question | causal link | pattern of re-definition |
| Title | résumé | question/present | metaphor |
| Life read vs summarized | summarized | mixed→summarized | reading |

**Does B close the gap to C?** Partially on title and anti-résumé *intent*; not yet on compression strength, residue pattern, or density.

---

## 8. Safety / production

| Check | Result |
|-------|--------|
| Prod redeployed? | No |
| Title publication blockers loosened? | No |
| Lens gate loosened? | No |
| Unapproved pack used? | No |
| Call3 publishable (B) | Yes (blockers=[]) |

---

## 9. Recommendation

Keep staging on v1.1.1-exp. Do **not** enable production.

Next revision focus (implementation follow-ups):

1. Stronger Call2 anti-enumeration (hard cap on distinct org mentions in body)  
2. Thesis/Residue causal soft-repair must fire when `影響`/`繋が` appear (gate added post-run; redeploy for next staging smoke)  
3. Prefer demoting employer-fine lines even when total pack size ≤5 if category duplicates career_history  
4. Re-branch must derive from tension, not “自己経営の影響”

Artifacts:

- `selection_compression_ab/SUMMARY.json`
- `selection_compression_ab/B_manuscript.json`
- `selection_compression_ab/B_trace.json`
- Baseline A: `live_ab/A_ntt/contextual_*.json`
