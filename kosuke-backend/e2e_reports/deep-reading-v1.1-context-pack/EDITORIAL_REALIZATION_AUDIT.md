# Deep Reading v1.1.3 Design Audit — Editorial Realization

**Date:** 2026-08-08  
**Mode:** Trace + design only. **No code changes. No production changes.**  
**Frozen upstream (do not retune):** Observatory-Core lenses/evidence/CrossLens, Context Pack selection, MeaningCompression, central thesis from live v1.1.2 NTT.

Source artifact: `observatory_core_live_ntt/session_final.json`

---

## Verdict of the trace

Pre-thesis intelligence is strong and **survives into Call2 thesis language**.

The manuscript failure is **not** Call3 deletion of Lost/Protected/Re-branch.

**Lost / Protected / Re-branch were already empty in Call1.**  
Call2 therefore had nothing structural to realize for those sections, and filled the page with pack biography + CrossLens thesis prose instead.

---

## PHASE 1 — Exact NTT live trace

### Call1 (confirmed → ready_for_draft)

| Artifact | Live state |
|----------|------------|
| Prompt / runtime | `parallel-life-call-1-v1.1.2-exp` / `parallel-life-runtime-v1.1.2-exp` |
| RelevantContextSelection | All 5 pack IDs in `manuscript_logic_ids` (no withhold). Classifications are `runtime_backfill_unclassified` |
| Observatory candidates | `education-employment`, `after-success`, `clean-society` |
| ObservatoryEvidence | `obs_ee_001`, `obs_cs_001`, `obs_as_001`, `obs_ee_002` |
| CrossLensRelations | 3 relations, all `non_causal_parallel` (regime / norm / after-success) |
| MeaningCompression | Present; still contains causal-tinged continuity/transformation language, but CrossLens slots filled |
| Central thesis | Strong non-causal juxtaposition (一社内蓄積 vs 企業間移動) — `passed_weak_compression_link` |
| **Lost** | **`items: []`** |
| **Protected** | **`items: []`** |
| Residue | 1 item: NTT勤務振り返り問い ↔ 現在の会社経営（並べて読む） |
| **Re-branch** | **`directions: []`** |
| selected_observatory_lenses | empty (intentional omit after pre-thesis relations) |
| editorial_outline | Generic 3 sections: 「分岐の背景」「選択の影響」「今後の展望」 — **no Lost/Protected/Residue/Re-branch contracts** |

### Call2 input payload

`run_call2_draft` builds:

1. `confirmed_call1` = **full Call1 JSON dump** (after filtering grounded pack facts to selected IDs — here all 5)  
2. `ALLOWED_PERSONAL_EVIDENCE` = `build_evidence_ledger(call1)`

Ledger exposure (live reconstruction):

| Ledger field | Content |
|--------------|---------|
| `explicit_facts` | **All 5 pack lines** (NTT東日本 / 外資系半導体 / 複数業界・企業 / 自分の会社 / 観測・Protocol・文章制作) |
| `manuscript_logic_ids` | same 5 IDs |
| `central_thesis` | full thesis statement |
| `meaning_compression` | full object |
| `cross_lens_relations` | present in ledger |
| `branch_structure` | includes realized_outcomes with employer/industry strings |
| `validated_residue` | 1 structural residue |
| Lost / Protected / Re-branch plans | empty → nothing to enforce |

Additionally, `confirmed_call1` re-exposes the same pack biography, outline pack IDs, and branch outcomes — so Call2 sees pack résumé facts **twice**.

### Call2 manuscript

- Sections realized: only 2 literary headings — 「残ることと移ることのあいだ」「現在に残る問い」
- `observatory_omitted: true`
- `rebranch_omitted_reason`: 「確認済みの追加分岐を具体的な名詞と出来事で記述できる根拠がないため。」
- No Lost / Protected headings or structural blocks

### Call3 edit

- `body_markdown` **byte-identical** to Call2 (818 chars)
- Title validation passed; subtitle résumé-like
- `publishable: true`, `blocking_reasons: []`
- **Did not remove Lost/Protected/Re-branch** — they were never in the draft

---

## Answers to the five trace questions

### 1. Were Lost / Protected / Re-branch already empty in Call1?

**Yes.**

- `lost_structure.items = []`
- `protected_structure.items = []`
- `rebranch_design.directions = []`

This is the primary disappearance point.

### 2. If not empty, did Call2 omit them?

N/A for emptiness origin — but Call2 behavior confirms:

- No Lost/Protected section generation when Call1 items empty
- Re-branch explicitly omitted (`rebranch_candidates: []` + omission reason)
- Outline did not require those sections

### 3. Did Call3 remove them?

**No.** Call3 body == Call2 body. No section stripping occurred.

### 4. How much raw Context Pack biography was passed into Call2?

**Maximum selected pack surface (5/5 items), plus full Call1 dump.**

Concrete lines injected as `explicit_facts`:

1. NTT東日本で勤務した  
2. 外資系半導体企業へ転職した  
3. その後、複数業界・企業を経験した  
4. 現在は自分の会社を経営している  
5. 現在、複数の観測・Protocol・文章制作を行っている  

No per-section example budget. No demotion of employer/industry/project inventory for writing.

### 5. Which exact Call2 passages caused `resume_density = 8`?

Whole manuscript (title+subtitle+body) scores **8.0** with flags: `org_enumeration`, `industry_enumeration`, `project_enumeration`.

| Passage | Density drivers |
|---------|-----------------|
| **¶1** (highest local damage) | NTT東日本 ×2, 外資, 外資系半導体企業, 複数の業界と企業, 勤務した/その後 — org + industry + chronology stack in one paragraph |
| **¶2** | 外資系半導体企業, 複数業界・企業 — continues employer/industry chain |
| **¶3** | 観測 / Protocol / 文章制作 + NTT東日本 — project enumeration + org recall |
| **¶4** | 観測・Protocol・文章制作 repeated — project names again |
| **Subtitle** | 「NTT東日本での勤務、企業間の移動、そして現在の経営を並べて読む」 — administrative biography (low local density score alone, but reinforces résumé framing) |

Structural CrossLens sentences in ¶1–2 are good; they are **diluted by preceding résumé cadence**.

---

## PHASE 2 — Freeze pre-thesis intelligence

Treat as frozen inputs for v1.1.3 Editorial Realization:

- selected Observatory lenses (3)
- ObservatoryEvidence (4)
- CrossLensRelations (3)
- RelevantContextSelection / manuscript_logic_ids (as-is for fidelity validators; **writing access reduced separately**)
- MeaningCompression (as-is)
- central thesis (as-is)

**Do not retune Observatory-Core, Context Pack selection, or CrossLens logic.**

---

## 6. Proposed `SectionContract` schema

```yaml
SectionContract:
  section_id: string
    # branch_point | chosen_path | unchosen_life | lost | protected |
    # residue | observatory_meaning | rebranch
  structural_purpose: string
  required_meaning: string
    # one structural idea the section must realize
  supporting_evidence_ids: [string]
    # branch / pack / residue / cross_lens ids — capped
  prohibited_claims: [string]
  concrete_example_budget: int
    # default 1–2 biographical examples max
  must_be_present: bool
  omission_allowed: bool
  public_heading_mode: enum
    # literary | ui_label | omit_heading
  realization_status: enum
    # planned | realized | omitted_allowed | missing_required
```

### NTT target contracts (design)

| section_id | must_be_present | required_meaning (target) | example_budget | prohibited |
|------------|-----------------|---------------------------|----------------|------------|
| branch_point | true | 28歳の残る/移る分岐 | 1 | employer stack as section spine |
| chosen_path | true | 移る側へ進んだ事実 | 1–2 | industry tour list |
| unchosen_life | true | 一社内で役割蓄積を続ける道 | 1 | invented rank/salary |
| lost | true | 一制度内部で時間を積み、役職・評価として確認できる連続性 | ≤2 examples | salary/pension/colleagues/title inventory list |
| protected | true | 所属先が変わっても仕事を自分で定義し直す余白 | ≤2 | skill inventory; freedom/success moral |
| residue | true | 「残っていたら」は仮説数値要求ではなく、失われた測定系として読める | 1 past + 1 present | causal「影響した」 |
| observatory_meaning | false if already in thesis | CrossLens insight without lens names | 0–1 | Market Signals etc. labels |
| rebranch | true if residue/thesis support | 今後の蓄積を何で測るか | 0–1 action only if supported | SHIRO/Protocol/app growth |

Generation rule: SectionContracts are built **server-side from frozen Call1** before Call2. Empty Lost/Protected/Re-branch in LLM Call1 must be **structurally backfilled from thesis + CrossLens + Residue** when evidence suffices — without inventing biography.

---

## 7. Proposed Call2 input reduction

### Current (broken for writing)

```
Call2 ← full confirmed_call1 JSON
      + ledger.explicit_facts = all manuscript_logic pack lines
```

### Proposed writing surface

```
Call2WritingPack:
  central_thesis
  meaning_compression (structural fields only)
  cross_lens_relations
  section_contracts[]
  branch_facts_minimal[]          # period / chosen / unchosen / present_question
  evidence_by_section:
    <section_id>: [≤ concrete_example_budget facts]
  residue_validated[]
  editorial_constraints:
    one_paragraph_one_idea: true
    max_org_names_in_body: 2
    max_project_names_in_body: 1
    forbid_chronology_stack_paragraphs: true
```

**Keep full pack available only to fidelity validators (Call3), not to the writing model.**

Default `concrete_example_budget = 2` per section; Lost/Protected prefer **0 named employers** if structural sentence already carries meaning.

NTT writing examples (not inventory):

- Allowed once: 「NTTを離れた」 or 「一社を離れた」  
- Demote from writing pack: 「外資系半導体」「複数業界・企業」「観測・Protocol・文章制作」 unless a specific section budget spends them

---

## PHASE 4–7 — Section meaning targets (NTT)

### Lost

Compress inventory into continuity-inside-one-institution:

> 「一つの制度の内部で時間を積み重ね、その蓄積を役職や評価として確認できる連続性」

Examples only as optional support, never the section spine.

### Protected

> 「所属先が変わっても、自分の仕事を自分で定義し直す余白」

No superiority / freedom / success claim unless explicit in approved evidence.

### Residue (strongest present return)

Not merely hypothetical rank/salary numbers.

Interpretation frame:

> 「『残っていたら』の問いは、一続きの制度の内部で人生の進度を知るための測定系を失ったこととして読むことができる」

Must use 「〜として読むことができる」 — not psychological fact.

### Re-branch

From Residue/thesis only:

> 「これから長期の蓄積を、何によって確認したいのか」

Forbidden defaults: SHIRO成長 / Protocol拡大 / 出版 / アプリ / 起業推奨.

---

## PHASE 9 — Writing rule

Call2:

**ONE PARAGRAPH = ONE STRUCTURAL IDEA**

Pattern: concrete fact → interpretation → return to branch meaning.

Ban résumé paragraphs: fact→employer→industry→project→chronology.

---

## 8. Proposed `required_section_realization` validator

Before `publishable=true`:

```yaml
RequiredSectionRealization:
  contracts: [SectionContract]
  checks:
    - every must_be_present=true section has realized prose OR allowed omission
    - Lost/Protected not inventory-shaped
    - Residue present and non-causal
    - Re-branch present if contract.must_be_present
    - resume_density <= threshold (soft diagnostic; hard block only if >5 for v1.1.3 gate experiment)
    - no lens-name advertising
```

Call3 may improve prose but **must not delete** `must_be_present` sections.

If Call2 omits a required section → `blocking_reasons += required_section_missing:<section_id>` → not publishable.

---

## 9. Subtitle recommendation

**Do not change public manuscript structure yet.**

Finding: literary title is strong; **public subtitle became administrative biography**.

| Option | Recommendation |
|--------|----------------|
| A. Keep fixed UI labels (実際に選んだ道 / 失ったもの / 守られたもの) as chrome; omit literary subtitle | **Preferred for v1.1.3 experiment** when subtitle would enumerate employers/career stages |
| B. Allow literary subtitle only if it expresses tension (stay/leave, measure/空白) with ≤1 concrete noun | Secondary |
| C. Keep current dual title+subtitle always | Reject for NTT-class cases — subtitle regresses to résumé |

Report recommendation: **UI labels for section chrome; literary subtitle optional and tension-only; never employer chronology.**

Title generation remains thesis/tension-based; **do not optimize title until realization succeeds.** Keep 「残ることと移ることのあいだ」 as directional success.

---

## 10. Implementation plan (not executed)

Scope: **Editorial Realization only** — freeze Observatory-Core / Context Pack selection / CrossLens.

| Step | Work | Touches |
|------|------|---------|
| 0 | Keep this audit as freeze record | docs only |
| 1 | Add `SectionContract` models + server builder from Call1 (backfill Lost/Protected/Re-branch structurally when empty but evidence-rich) | new module; Call1 runtime post-gate **additive** |
| 2 | Build `Call2WritingPack` reducer (per-section evidence budgets) | `draft.py` ledger only |
| 3 | Call2 prompt: contracts + one-idea paragraphs; **do not** dump full pack résumé | `prompts.py` Call2 Contextual branch only |
| 4 | Call3 `required_section_realization` gate | `runtime_validation.py` / edit-validate |
| 5 | Subtitle policy: tension-only or omit (no public structure rename yet) | Call2/3 title selection |
| 6 | Staging-only pin: `parallel-life-call-2-v1.1.3-exp` / runtime note `v1.1.3-exp`; Strict+Prod unchanged | manifest/flag |
| 7 | Rerun same NTT branch+pack; compare to live v1.1.2 | report |
| 8 | **Stop** after first run if resume_density>5 or naturalness<8 or Lost/Protected empty | no auto-tune |

### Explicit non-goals

- Do not modify Observatory-Core selection/retrieval/relations  
- Do not modify Context Pack approval/selection algorithms  
- Do not loosen title validation  
- Do not enable production  

### Success targets (NTT B vs A)

| Metric | A live v1.1.2 | B target v1.1.3 |
|--------|---------------|-----------------|
| fidelity | 10 | 10 |
| CVA | 9 | ≥9 |
| social | 9 | ≥8 |
| personal | 9 | ≥9 |
| depth | 7 | ≥9 |
| naturalness | 5 | ≥8 |
| resume_density | 8 | ≤3 |
| Lost | empty | present+meaningful |
| Protected | empty | present+meaningful |
| Residue | ok | strong |
| Re-branch | empty | present if supported |
| life_read | mixed | YES |

---

## Root-cause summary

```
Strong pre-thesis (CrossLens + thesis)
        ↓
Call1 fails to materialize Lost / Protected / Re-branch plans (empty)
        ↓
editorial_outline is generic résumé/impact/outlook, not section contracts
        ↓
Call2 receives full pack biography ×2 (ledger + confirmed_call1)
        ↓
Call2 writes thesis-aware prose wrapped in employer/industry/project chronology
        ↓
Call3 preserves that prose (no section recovery)
        ↓
publishable=true with resume_density=8, life_read=mixed
```

**Editorial Realization = force section contracts + starve Call2 of résumé fuel + validate realization.**  
Not another Observatory retune.

---

## Artifacts referenced

- `e2e_reports/deep-reading-v1.1-context-pack/observatory_core_live_ntt/session_final.json`
- `e2e_reports/deep-reading-v1.1-context-pack/OBSERVATORY_CORE_LIVE_NTT_REPORT.md`
- `kosuke-backend/app/parallel_life_deep_reading/draft.py` (`build_evidence_ledger`, `run_call2_draft`)
- `kosuke-backend/app/parallel_life_deep_reading/prompts.py` (`call2_user_prompt`)

---

## Status

```
TRACE COMPLETE — READY TO IMPLEMENT ON REQUEST
```

No code was modified in this phase.
