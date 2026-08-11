# Deep Reading v1.1 Context Pack — Live A/B Report (Staging Only)

**Date:** 2026-08-08  
**Scope:** Staging enablement + live Strict vs Contextual A/B  
**Constraint honored:** No prompt / runtime / evidence-gate / schema / production v1.0.2 edits during this run  
**Artifacts:** `e2e_reports/deep-reading-v1.1-context-pack/live_ab/`

---

## Verdict

```
CONTEXT PACK V1.1 PROMISING — NEEDS REVISION
```

Plumbing, mode separation, approval gates, and factual fidelity work on staging. Contextual can deepen present-life specificity without inventing biography. It does **not** yet reliably approach book-quality *reading* (often drifts toward résumé / longer inventory), Observatory almost never fires, and NTT Context Value Add misses the ≥8 target on the dedicated case run.

---

## 1. Staging configuration

| Item | Staging | Production |
|------|---------|------------|
| API | `https://parallel-life-api-staging.shiroandco-office.workers.dev` | `https://parallel-life-api.shiroandco-office.workers.dev` |
| `DEEP_READING_ENABLED` | true | true |
| `DEEP_READING_CONTEXT_PACK_ENABLED` | **true** (wrangler `env.staging` vars + container env forward) | **false / unset** (prod response has no `context_pack_enabled`; FE treats as off) |
| Enabled probe | `{"enabled":true,"context_pack_enabled":true}` | `{"enabled":true}` |
| Context Pack seed endpoint | 200 | 404 `context_pack_disabled` (or code path absent) |
| Product pin | v1.0.2 Strict path when mode=strict | v1.0.2 unchanged |
| Contextual pins | Call1 `parallel-life-call-1-v1.1.0` / runtime `parallel-life-runtime-v1.1.0-exp` | n/a |

Config sources touched for staging-only enablement (not production deploy):

- `cloudflare/api-container/wrangler.toml` — staging `true`, production explicit `false`
- `cloudflare/api-container/src/index.ts` — forward `DEEP_READING_CONTEXT_PACK_ENABLED` (default `"false"`)
- Staging worker redeployed; **production worker was not redeployed**

Manifest reference: `PRODUCTION_MANIFEST_v1.1.0-exp.json`

---

## 2. Mode separation result

Fresh sessions. Strict arm was intentionally sent an approved pack and **ignored** it.

| Check | Strict | Contextual |
|-------|--------|------------|
| `deep_reading_mode` | `strict` | `contextual` |
| Call1 prompt | `parallel-life-call-1-v1.0.3` | `parallel-life-call-1-v1.1.0` |
| Runtime schema | `parallel-life-runtime-v1.0.6` | `parallel-life-runtime-v1.1.0-exp` |
| Pack facts in grounded | 0 | 5 (NTT pack) |
| Leak of pack-only phrases into Strict session | **none** | n/a |
| Publishable manuscript | yes | yes (mode_sep) |

**Result: PASS** — switching modes does not leak Context Pack into Strict.

---

## 3. Context Pack approval UX

API-level checks (staging seed + local edit semantics matching FE contract):

| Capability | Result |
|------------|--------|
| See every seeded item | PASS |
| Items start `approved=false` | PASS |
| Pack starts `approved_by_user=false` | PASS |
| Edit content | PASS (client-side before ground) |
| Delete item | PASS (`rejected_or_deleted_ids`) |
| Add item | PASS |
| Approve pack for Contextual ground | PASS |
| Choose Strict instead | PASS (mode ask / secondary CTA; Strict ground omits pack) |
| Hidden profile/history | PASS — seed is same-session / paste text only |
| Raw internal IDs in item content | PASS — none |
| Production seed blocked | PASS (404) |

FE behind flag (`ModeAsk` + `ContextPackEditor`) is present in repo; staging Pages redeploy of FE was not required for this API A/B.

---

## 4–5. NTT Strict vs Contextual

### Strict (dedicated case)

- Title: 「残っていたら」という現在形  
- Chars: 410  
- Prompt/runtime: v1.0.3 / v1.0.6  
- Pack facts: 0  
- Observatory: 0  
- Tone: restrained reading; juxtaposition without causality  

### Contextual (dedicated case; first draft attempt failed, retry succeeded)

- Title: NTTを離れた後の経歴と、残る問い  
- Subtitle: 外資系半導体企業への転職、複数業界・企業での経験、現在の会社経営  
- Chars: 342  
- Prompt/runtime: v1.1.0 / v1.1.0-exp  
- Pack IDs used: `pack_career_history_001..003`, `pack_current_work_004`, `pack_current_projects_005`  
- Residue present anchors from pack: `pack_current_work_004`, `pack_current_projects_005`  
- Observatory: 0  

### Additional NTT Contextual sample (mode_sep run)

Higher literary quality appeared on a separate Contextual session:

- Title: 二十八歳の分かれ目と、現在の机の上  
- Chars: 554  
- Same approved pack; stronger present return (“机の上”) without dropping the branch question  

Variance shows Contextual *can* read rather than summarize — but not reliably yet.

---

## 6. NTT book-quality comparison

| Dimension | A Strict app | B Contextual app (retry) | C Book/ChatGPT qualitative target |
|-----------|--------------|---------------------------|-------------------------------------|
| Temporal depth | Thin (branch → now) | Longer career arc via pack | Long institutional arc |
| Institutional reading | Light | Present (NTT東日本 / 半導体 / 複数業界) | Strong |
| Current-life connection | Company only | Company + 観測/Protocol/文章 | Projects, domains, social observation |
| Residue | Structural juxtaposition | Pack present anchors; statement often question-like | Dense past↔present |
| Observatory | 0 | 0 | Active when evidence supports |
| Re-branch | Empty | Empty | Grounded in current projects |
| Title | Strong (question as present tense) | Weaker / résumé-leaning | Thesis + closing |
| “Life read vs summarized” | Reading (thin) | Closer to career summary on retry; better on mode_sep sample | Reading |

**Does Contextual materially close the gap to the book?**  
**Partially on evidence surface area; not yet on manuscript depth/voice.** Pack expands what *may* be said; prose often inventories the pack instead of composing one thesis across time. Do not score C for factual safety (it may use unavailable info).

---

## 7. Family A/B

| | Strict | Contextual |
|---|--------|------------|
| Title | 三人で暮らす現在と、二人目をめぐる問い | 三人で暮らす現在と、仕事のある日々 |
| Chars | 347 | 477 |
| Pack | — | family / company / creative |
| Medical causality invented? | No | No |
| Branch question retained? | Yes (二人目) | Yes |

Contextual adds work/creative present without inventing family psychology. Mild risk: thesis tilts toward “家族と仕事の両立” and softens fertility-counterfactual primacy — still acceptable, not a hard failure.

---

## 8. Education A/B

| | Strict | Contextual |
|---|--------|------------|
| Title | 十九歳の合格と、いま残る問い | 別の大学を考える現在 |
| Chars | 341 | 339 |
| University→career causality? | Explicitly refused | Explicitly refused |
| Pack | — | company / 文章・プロトコル / 観測 |

**PASS** for non-inference. Context Value Add modest (present specificity), not transformative.

---

## 9. Creative-work A/B

| | Strict | Contextual |
|---|--------|------------|
| Title | 現在の制作と、創作中心の人生という問い | 経営と文章制作の現在、その傍らにある創作 |
| Chars | 394 | 503 |
| “Late recovery of creativity”? | Avoided | Avoided |
| Pack | — | company / writing / observation / Protocol |

**PASS** on failure-condition avoidance. Contextual lists present projects more densely; still juxtapositional rather than redemptive narrative.

---

## 10. Evidence trace (Contextual, internal)

| Case | Pack IDs | Residue pack anchors | Thesis pack-linked | Observatory pack evidence | Re-branch pack supports |
|------|----------|----------------------|--------------------|---------------------------|-------------------------|
| A_ntt | 5 career/work/project | present: work+projects | weak (generic career influence wording) | none | none |
| B_family | 3 | none recorded on residue IDs | soft (work/family coexistence) | none | none |
| C_education | 3 | none on residue IDs (present facts duplicated) | none direct | none | none |
| D_creative | 4 | none on residue IDs | none direct | none | none |

Public manuscripts do **not** show internal IDs.

---

## 11. Observatory behavior

Across all Contextual live manuscripts in this run: **zero lenses selected**.

Interpretation:

- Expanded allowlist did **not** force Market Signals / Protocol Publishing / Education–Employment from project-name string match — **good**.  
- Zero Lens remains valid — **good**.  
- Desired “material deepening when pack + Residue support” did **not** appear — Observatory quality still low; pack evidence is underused for lens selection.

---

## 12–15. Scoring

Scale /10. Targets for Contextual: fidelity=10, naturalness≥8, continuity≥8, depth≥9, Context Value Add≥8.

### Case A — NTT

| Metric | Strict | Contextual (retry) |
|--------|--------|--------------------|
| Factual fidelity | 10 | 10 |
| Naturalness | 8 | 5 |
| Continuity | 8 | 6 |
| Depth | 5 | 6 |
| Specificity | 5 | 8 |
| Residue quality | 7 | 5 |
| Observatory quality | 3 | 3 |
| Re-branch quality | 2 | 2 |
| Title quality | 8 | 4 |
| **Context Value Add** | — | **5** |

### Case B — Family

| Metric | Strict | Contextual |
|--------|--------|------------|
| Factual fidelity | 10 | 10 |
| Naturalness | 8 | 7 |
| Continuity | 8 | 7 |
| Depth | 6 | 7 |
| Specificity | 6 | 8 |
| Residue quality | 7 | 6 |
| Observatory quality | 3 | 3 |
| Re-branch quality | 2 | 2 |
| Title quality | 8 | 6 |
| **Context Value Add** | — | **6** |

### Case C — Education

| Metric | Strict | Contextual |
|--------|--------|------------|
| Factual fidelity | 10 | 10 |
| Naturalness | 8 | 7 |
| Continuity | 8 | 7 |
| Depth | 5 | 6 |
| Specificity | 5 | 7 |
| Residue quality | 6 | 6 |
| Observatory quality | 3 | 3 |
| Re-branch quality | 2 | 2 |
| Title quality | 7 | 7 |
| **Context Value Add** | — | **5** |

### Case D — Creative

| Metric | Strict | Contextual |
|--------|--------|------------|
| Factual fidelity | 10 | 10 |
| Naturalness | 8 | 7 |
| Continuity | 8 | 7 |
| Depth | 6 | 7 |
| Specificity | 6 | 8 |
| Residue quality | 7 | 6 |
| Observatory quality | 3 | 3 |
| Re-branch quality | 2 | 3 |
| Title quality | 7 | 6 |
| **Context Value Add** | — | **6** |

**Context Value Add question:** *Did the approved Context Pack create meaning that could not reasonably be produced from the branch form alone?*  
Answer today: **sometimes specificity, rarely new meaning.** Career/project nouns appear; a deeper institutional/observatory reading does not yet reliably follow.

---

## 16. Exact problematic excerpts

1. **NTT Contextual subtitle (résumé inventory)**  
   `外資系半導体企業への転職、複数業界・企業での経験、現在の会社経営`

2. **NTT Contextual body (summary cadence)**  
   `NTT東日本で勤務した後、NTTを離れ、外資系半導体企業へ転職した。…その後、複数の業界と企業を経験した。現在は自分の会社を経営し、複数の観測、Protocol、文章制作を行っている。`

3. **NTT Contextual thesis drift (generic causality temptation in Call1)**  
   `キャリアの選択が現在の自分にどのように影響を与えたか。`  
   (Manuscript mostly avoided hard causality; thesis framing is weaker than Strict.)

4. **Family Contextual thesis soft-shift**  
   `家族との生活と仕事の両立について考える`  
   (Risk of diluting 二人目 counterfactual as the organizing question.)

5. **Transient infra/LLM failure (not a fidelity bug)**  
   First A_ntt Contextual draft returned:  
   `Deep Reading の生成に失敗しました。確認済み構造は保持されています。再試行してください。`  
   Retry succeeded publishable with blockers=[].

---

## 17. Privacy / approval issues

| Issue | Status |
|-------|--------|
| Unapproved items entering pipeline | Not observed |
| Cross-session memory | Not observed |
| Prod flag bleed | Not observed |
| Internal IDs in public manuscript | Not observed |
| Pack content in Strict | Not observed |

---

## 18. Production v1.0.2 remained untouched

| Check | Result |
|-------|--------|
| Production worker redeployed? | **No** |
| Prod `context_pack_enabled` | absent → off |
| Prod Call1 / runtime pins | unchanged (v1.0.3 / v1.0.6 path) |
| Title validation / publication gates modified this run? | **No** |
| Prompts / schema / runtime code modified this run? | **No** (enablement = Cloudflare staging vars + env forward only) |

---

## 19. Recommendation

**CONTEXT PACK V1.1 PROMISING — NEEDS REVISION**

Keep staging flag on for further Public QA. Do **not** enable production yet.

### Why promising
- Strict / Contextual pin separation is correct and leak-free  
- Approval + kill switch work  
- Fidelity stays at 10; no invented biography / forced Observatory  
- Pack IDs correctly enter Residue present anchors when used  

### Why revision before Public QA graduation
1. Contextual prose frequently becomes **career inventory** rather than life reading (NTT retry)  
2. **Context Value Add** and **Depth** miss targets on primary NTT case  
3. Observatory / Re-branch rarely capitalize on pack evidence  
4. Call1 thesis sometimes drifts toward generic “influence” framing  
5. One draft-stage flake on first NTT Contextual attempt  

### Suggested next work (after this report; not done here)
- Call1 v1.1 prompt: prefer *reading* over chronology dump; forbid résumé subtitle patterns  
- Encourage Observatory only when pack ID + Residue + new meaning cohere (already gated; may need prompt examples)  
- Re-branch should cite pack project nouns when IDs present  
- Add Public QA checklist on staging Pages FE for mode ask / pack editor  

---

## Pipeline pass table

| Case | Strict | Contextual |
|------|--------|------------|
| Mode separation (NTT) | PASS | PASS |
| A NTT | PASS | PASS (retry) |
| B Family | PASS | PASS |
| C Education | PASS | PASS |
| D Creative | PASS | PASS |

Machine dump: `live_ab/LIVE_AB_SUMMARY.json`
