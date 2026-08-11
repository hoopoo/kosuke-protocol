# Observatory Architecture Audit — Parallel Life Deep Reading v1.1

**Date:** 2026-08-08  
**Scope:** Read-only architecture audit. **No code changes. No production changes.**  
**Staging artifacts referenced:** NTT Selection+Compression v1.1.1 (`selection_compression_ab/B_session_final.json`)  
**Question:** Are SHIRO & Co. observatories used as genuine editorial lenses **before** central-thesis formation, or mainly added **after** manuscript meaning is already determined?

---

## Verdict

```
OBSERVATORY CURRENTLY DECORATIVE
```

User suspicion is **confirmed for Deep Reading**.

Observatory lenses are selected **after** `meaning_compression` and `central_thesis`. Runtime gates filter selected lenses for the Observatory *section*; they do **not** feed back into structural relations, compression, thesis, Lost, Protected, Residue, or Re-branch. On the current NTT Contextual run, **0 lenses** were selected — meaning was fully formed without any Observatory evidence.

---

## 1. Current pipeline

### Deep Reading Contextual v1.1.1 (implemented `generation_order`)

```
branch input
  + approved Context Pack (flagged Contextual only)
→ grounded_input
→ relevant_context_selection
→ meaning_compression
→ central_thesis
→ lost_structure
→ protected_structure
→ residue_candidates
→ selected_observatory_lenses          ← Observatory enters HERE
→ rebranch_design
→ editorial_outline
→ user_confirmation_view
→ Call2 / Call3 manuscript
```

Source: `parallel_life_deep_reading/prompts.py` → `call1_user_prompt_v11` `generation_order`.

### Strict / Production (v1.0.2 path)

Same conceptual late placement: Observatory is evidence-gated after Residue; 0 selected is normal; Call2/3 omit Observatory when empty. Context Pack is off in production.

### Classic Parallel Life (non–Deep Reading)

`select_observatory_lenses` (keyword heuristic in `observatory_lenses.py`) + `cross_lens_synthesis` prose exist in classic editorial/engine paths. That is a **separate product path**. Deep Reading does **not** import `select_observatory_lenses` and does **not** use classic `cross_lens_synthesis` as a pre-thesis structure.

---

## 2. Current Observatory insertion point

| Stage | Observatory evidence present? |
|-------|-------------------------------|
| Context Pack approval | No (user biography / projects only) |
| Relevant context selection | No |
| Meaning compression | No |
| Central thesis | No |
| Lost / Protected / Residue | No (Residue may later *gate* a lens, but is not shaped by Observatory data) |
| **selected_observatory_lenses** | **Yes — first insertion** |
| Re-branch | Only indirectly if LLM echoes lens names; design is thesis-derived, not Observatory-evidence-derived |
| Call2 Observatory / Cross-Lens sections | Yes, **only if** selected lenses non-empty |
| Call3 | Same; empty → sections stripped |

### What the runtime actually does

1. LLM proposes `evaluated` / `selected` lenses late in Call1.  
2. `recalculate_lens_evidence_gate` requires **all** of:
   - non-empty `explicit_evidence_ids` (branch ∪ pack IDs)
   - non-empty `residue_evidence_ids`
   - non-empty `new_meaning_added`
3. `filter_selected_lenses` keeps only gate-passed IDs.  
4. Call2 sets `observatory_omitted=true` when selected count is 0.  
5. Publication gate can block `observatory_takeover` (too much Observatory prose) — defensive against decoration becoming the manuscript.

**There is no Observatory → thesis rewrite loop.**

---

## 3. Does Observatory influence thesis today?

| Artifact | Influenced by Observatory evidence today? |
|----------|-------------------------------------------|
| Structural relations (implicit in compression/thesis) | **No** |
| Meaning compression | **No** |
| Central thesis | **No** |
| Lost | **No** |
| Protected | **No** |
| Residue | **No** (Residue is an *input gate* for allowing a lens, not an output of lenses) |
| Re-branch | **No** (prompt: thesis-derived; pack projects discouraged) |
| Observatory manuscript section | **Yes** (only place) |
| Cross-lens synthesis section (Deep Reading) | Only as optional late prose when lenses selected; **not** a typed pre-thesis relation object |

**Answer:** Observatory influences **only the Observatory section** (when any lens survives the gate). It does **not** currently act as a pre-thesis editorial lens.

NTT live evidence: `selected_observatory_lenses.evaluated = []`, `selected = []`, while thesis/compression were already complete.

---

## 4. Available lens registry (repository truth)

**Canonical catalog:** `kosuke-backend/app/observatory_lenses.py` — **16 IDs**.  
Deep Reading Call1 does **not** constrain `lens_id` to this enum at schema level, but product metadata and classic selection do.

**Not found in repository (do not invent):** “Generated Things / Folklore”, “Body Meaning” as a separate ID (Body exists as `body`).

### Registry table

| lens_id | Purpose (from defs) | Available evidence/data in repo | Machine-readable? | Integrated in Deep Reading? | Usable for Deep Reading today? |
|---------|---------------------|--------------------------------|-------------------|-----------------------------|--------------------------------|
| `education-employment` | Education/employment systems shaped available choices | Metadata + keywords; classic heuristic selection | Metadata/keywords only | Name-level only (LLM may pick; no evidence store) | Conceptually yes; **no structured observatory corpus** |
| `market-signals` | Housing/income/work/region as conditions of a livable life | Same | Same | Same | Same |
| `book` | Literary form latent in the branch | Same | Same | Same | Same |
| `protocol-publishing` | One branch beside anonymous records as social pattern | Same; also appears as **user Context Pack project fact** (biography), not as lens corpus | Same | Same; risk of self-promo via pack | Same; gate tries to block promo |
| `work` | Org life; staying/leaving/changing roles | Same | Same | Same | Same |
| `city` | Place, migration, belonging | Same | Same | Same | Same |
| `intimacy` | Closeness vs autonomy | Same | Same | Same | Same |
| `body` | Illness, fatigue, care as lived branch | Same | Same | Same | Same |
| `clean-society` | Normalization / quiet exclusion | Same | Same | Same | Same |
| `after-success` | What remains after achievement | Same | Same | Same | Same |
| `old-web` | Early net / non-returnable digital places | Same | Same | Same | Same |
| `contact-data` | Exposure, personal data, unwanted visibility | Same | Same | Same | Same |
| `meaning-layer` | Language/symbols; meaning over time | Same | Same | Same | Same |
| `sound` | Memory held in sound | Same | Same | Same | Same |
| `image` | Photos / unphotographed scenes | Same | Same | Same | Same |
| `style` | Clothing/appearance as life record | Same | Same | Same | Same |

**Core preferred (classic selection bias):** `education-employment`, `market-signals`, `book`, `protocol-publishing`.

### Adjacent systems (not wired into Deep Reading lenses)

| System | Role | Deep Reading coupling |
|--------|------|------------------------|
| `observatory_engine.py` + FragmentStore/Chroma | Meaning Observatory research dashboard | **Not connected** to Parallel Life Deep Reading Call1 |
| `lenses.py` | Experience lenses (`open`, etc.) | Different product surface |
| `parallel_life_seed.py` | Classic heuristic seed text | Not Deep Reading ObservatoryEvidence |
| Context Pack items mentioning “観測所” / “Protocol Publishing” | **User biography**, not SHIRO observatory corpus | Can falsely look like lens integration |

**Gap:** There is a **lens taxonomy**, but **no machine-readable ObservatoryEvidence retrieval layer** for Deep Reading. Selection in Deep Reading is LLM+gate, not catalog-backed evidence fetch.

---

## 5. Proposed pre-thesis lens architecture

Target model (product intent):

```
Branch Facts
+ Approved Context Pack
+ Selected Observatory Evidence
        ↓
CrossLensRelations
        ↓
Meaning Compression
        ↓
Central Thesis
        ↓
Lost / Protected / Residue / Re-branch
        ↓
Manuscript (Observatory section optional; thesis already lens-informed)
```

### Pre-thesis Lens Selection stage

**Input**

- Branch facts (`grounded_input` / fact IDs)
- Approved Context Pack items (IDs + categories + texts)
- Observatory registry metadata (purpose/descriptors only — not full dumps)

**Output**

- `candidate_lenses`: **0–4** (prefer **2–4** when structural relevance exists; **0 is valid**)
- Each candidate: `lens_id`, `structural_relevance_reason`, `confidence`, `rejected_alternatives` (optional)

**Selection rules (must not be keyword/project-name matching)**

1. Prefer **structural isomorphism**: personal branch structure ↔ lens’s social/institutional pattern.  
2. Ban selection solely because pack mentions “Observatory”, “Protocol Publishing”, project titles, or company brands.  
3. Prefer at most one “identity/media” lens (`book` / `sound` / `image` / `style`) unless branch evidence is visual/aural-primary.  
4. For career-exit / employment-regime branches: `education-employment`, `work`, `market-signals`, `clean-society` are structural candidates; `protocol-publishing` only if the *reading mode* (anonymous social record) is needed — not because the user works on that project.  
5. Zero lenses if no lens adds a relation the branch+pack cannot already state.

**Implementation note:** Classic `select_observatory_lenses` is **keyword-driven** and often forces 2–3 lenses — **unsuitable** as-is for the target model. Deep Reading needs a new structural selector (rules + optional LLM with hard caps), then evidence retrieval.

---

## 6. ObservatoryEvidence (compact)

For each selected lens, retrieve **only** relevant observations/structures — never dump an observatory.

```yaml
ObservatoryEvidence:
  lens_id: string                 # registry ID
  observation_id: string          # stable ID from observatory store
  structural_pattern: string      # short pattern statement (not essay)
  relevance_to_branch: string     # why this branch can be placed beside it
  source: string                  # corpus / fragment / curated note
  confidence: float               # 0–1
  # optional boundaries
  time_span: string | null
  geography: string | null
  interpretation_boundary: string # what this evidence must NOT claim
```

**Aggressive limits (proposed)**

| Cap | Value |
|-----|-------|
| Lenses | 0–4 (Deep Reading manuscript still may surface ≤2) |
| Evidence items total | ≤6 |
| Per lens | ≤2 |
| `structural_pattern` chars | ≤180 |
| Tokens into Call1 | hard budget; drop lowest confidence first |

**Current state:** This object **does not exist**. Gate fields today are LLM-authored `explicit_evidence_ids` / Residue IDs / `new_meaning_added` — not retrieved observatory observations.

---

## 7. CrossLensRelation schema

```yaml
CrossLensRelation:
  relation_id: string
  relation: string
    # juxtaposition / parallel structure / contrast / boundary —
    # NOT unsupported causation
  branch_evidence_ids: [string]
  context_pack_ids: [string]
  observatory_evidence_ids: [string]
  interpretation_boundary: string
  confidence: float
  relation_type: enum
    # personal_social_parallel | institutional_condition |
    # temporal_coincidence | contrast | open_question
```

### Example (NTT-shaped; non-causal)

- **personal:** 「大企業を離れた」  
- **social (lens):** 「日本型雇用から職種・専門性ベースの移動型キャリアへの変化」  
- **relation:** 「個人の転職は、同時期の雇用構造変化と並べて読むことができる」  
- **boundary:** Do **not** assert 「社会変化が転職を引き起こした」 unless supported.

**Current state:** No typed `CrossLensRelation` in Deep Reading. Classic `cross_lens_synthesis` is post-hoc prose after layers exist.

---

## 8. Thesis influence (design test)

CrossLensRelations should enable a thesis that connects:

1. individual branch  
2. current life (approved pack only)  
3. larger social structure (observatory evidence)

**without** becoming sociology commentary. Individual life remains primary.

| Quality | Compression/thesis-only | + CrossLensRelations |
|---------|-------------------------|----------------------|
| Personal primacy | Strong | Must remain strong (relation is juxtaposition) |
| Social depth | Weak / absent | Possible without causal takeover |
| Resume drift | High risk | Lower if social pattern replaces employer lists |
| Promo risk | Pack project names | Must exclude project-name lenses |

---

## 9. NTT structural comparison (no final prose)

Case facts (branch + approved pack):

**Branch**

- Age 28 fork: stay at NTT vs move to foreign firm  
- Chosen: leave NTT → foreign firm  
- Unchosen: accumulate roles inside one firm  
- Present: runs own company; still asks “what if I had stayed”

**Pack (approved, 5 items in live fixture family)**

- Worked at NTT  
- Worked at foreign firm  
- Now runs own company  
- Working on Observatory project  
- Involved in Protocol Publishing  
- (and related education–employment work items in fuller pack variants)

### Arm A — Context Pack + Selection/Compression only  
*(actual v1.1.1 NTT B Call1)*

| Field | Content |
|-------|---------|
| Selected facts (manuscript_logic_ids) | career NTT, foreign firm, current company, later career diversity, current projects |
| Selected lenses | **none** |
| Lens evidence | **none** |
| CrossLensRelations | **none** |
| Meaning compression | past: NTT→foreign move; alternative: stay in one firm; present: self-company + projects; tension/continuity/transformation framed as career-path difference; question: how the choice still affects self |
| Central thesis | 「組織内役職から自己経営へと移行した選択が、今もなお影響を与えている。」 |

**Diagnosis A:** Thesis is personal/career-transformational and still **causal-tinged** (`影響`). No education–employment regime, no market conditions, no clean-society “normal path” juxtaposition. Observatory projects in pack act as **biography**, not lenses — and still yielded **0** Observatory sections.

### Arm B — Pack + selected Observatory lenses + CrossLensRelations  
*(proposed structural sketch only — not generated manuscript)*

| Field | Proposed content |
|-------|------------------|
| Selected facts | Keep structural: fork at 28; leave vs stay-in-firm; present self-definition outside single-employer accumulation. **Demote** Observatory/Protocol project names from manuscript_logic unless they are the *present pattern* of redefinition (not product plugs). |
| Selected lenses (≤4, structural) | `education-employment` (school→firm→internal ladder as default regime); `work` (stay/leave identity); optionally `market-signals` or `clean-society` if pack/branch supports “normal large-firm path”; **exclude** `protocol-publishing` unless used as *reading mode*, not because user builds it |
| Lens evidence (examples) | `education-employment`: structural_pattern = 「一社内で役割を積み上げる進路が『普通』として提示される雇用様式」; relevance = unchosen path is that regime. `work`: structural_pattern = 「留まる／離れるが自己像を組み替える」; relevance = chosen exit. |
| CrossLensRelations | R1 personal_social_parallel: leave-NTT ↔ employment-regime shift (juxtaposition only). R2 contrast: unchosen internal accumulation ↔ present self-company scale of meaning. Boundaries: no “globalization caused the move”; no “Observatory project proves the reading.” |
| Meaning compression | past_structure: exit from single-firm accumulation path; alternative_structure: remain inside that regime; present_structure: self-defined work scale; tension: two measures of a life (internal role vs portable/self-authored); continuity: the unchosen regime still names the question; transformation: unit of evaluation moved; central_question: why the stay/leave fork still organizes meaning now |
| Central thesis (structural target) | Something in the class of: the branch remains because the life is still readable as a move from **role-inside-one-institution** to **self-authored measure** — placeable beside employment-structure change, **without** claiming that change caused the move. |

### Does B produce a materially stronger thesis?

**Yes, structurally — if and only if** ObservatoryEvidence is real and CrossLensRelations stay non-causal.

| Criterion | A (actual) | B (proposed) |
|-----------|------------|--------------|
| Personal primacy | Yes | Yes (if bounded) |
| Social structure without sociology takeover | No | Possible |
| Escape résumé/project inventory | Partial failure | Better lever (patterns replace names) |
| Uses SHIRO observatories as lenses | No | Yes by design |
| Risk of self-promotion | Pack projects unused for lenses but still in compression support | Must actively demote |

B is **not** available in current architecture; A is what ships on staging Contextual today.

---

## 10. Failure risks

| Risk | How it appears today / under target model | Mitigation |
|------|-------------------------------------------|------------|
| Forced lens matching | Classic keyword selector forces 2–3; Deep Reading opposite extreme (often 0) | Structural relevance; **0 valid**; no min-force |
| SHIRO & Co. self-promotion | Pack contains Observatory / Protocol Publishing as biography; thesis/rebranch can absorb project names | Ban lens selection from project-name hits; demote pack project IDs from manuscript_logic unless structural |
| Sociology overwhelming personal narrative | Target B risk if CrossLensRelations become the body | Cap evidence; individual primary; Observatory section optional |
| Unsupported causal claims | Already in A thesis/residue (`影響` / `繋が`) | Relation types + interpretation_boundary; keep soft/hard gates |
| Too much context | Pack + full observatory dumps | Cap manuscript_logic_ids; ≤6 ObservatoryEvidence |
| Token growth | Extra stages + evidence | Compact schemas; drop low confidence |
| Stale observatory data | No retrieval versioning today | `source` + as-of timestamps; freshness gate |
| Private/user context mixing | Pack is user-approved; observatory store must stay non-PII / non-cross-user | Hard partition: pack IDs vs observatory observation IDs |
| Circular reasoning | “User works on Observatory → select Observatory lenses → thesis about Observatory” | Explicit anti-circular rule in lens selection |

---

## 11. Product principle evaluation

**Proposition:**  
Parallel Life is not “an AI that analyzes a life branch.”  
It is “a life branch interpreted through SHIRO & Co.’s accumulated observatories, using only user-approved personal context.”

| Requirement | Current Deep Reading support |
|-------------|------------------------------|
| User-approved personal context only | **Partial → Stronger in v1.1 Contextual** (Context Pack + approval). Production Strict remains branch-only. |
| Interpreted **through** accumulated observatories | **No** — taxonomy exists; evidence does not enter before meaning; NTT often has 0 lenses |
| Observatories as editorial lenses | **No** — decorative / optional late section |
| Individual life remains primary | **Yes** (and Observatory takeover is blocked) |

**Conclusion:** Current architecture supports the **privacy/approval** half of the proposition more than the **SHIRO observatory lens** half. The defining product claim is **not** architecturally true for Deep Reading today.

---

## 12. Implementation impact (if pursued later — not done now)

| Workstream | Impact | Notes |
|------------|--------|-------|
| ObservatoryEvidence store/API | High | Does not exist for Deep Reading; FragmentStore is unrelated dashboard |
| Pre-thesis lens selection | Medium | New stage before compression; replace/avoid keyword forcer |
| CrossLensRelation in Call1 schema | Medium | Additive models + prompts + soft gates |
| Thesis/compression prompts | Medium | Consume relations; keep non-causal |
| Call2/3 | Low–Medium | Observatory section becomes illustration of relations already used — or stays omitable |
| Classic Parallel Life | Separate | Do not silently couple; avoid dual semantics |
| Production v1.0.2 | **Must stay frozen** until explicit cutover | Flag/manifest discipline as with Context Pack |
| Eval | High | NTT + frozen4: thesis quality with/without lenses; promo/circular tests |

Estimated sequencing: Evidence corpus (even small curated set) → selector → CrossLensRelation → compression/thesis prompt pin → staging A/B → only then consider production.

---

## 13. Recommendation

```
OBSERVATORY CURRENTLY DECORATIVE
```

Not `OBSERVATORY ALREADY CORE` — insertion is post-thesis; no evidence feedback.  
Not `OBSERVATORY PARTIALLY INTEGRATED` — gate + optional section without thesis influence is decoration with safety rails, not partial core integration.

**Closest honest gloss:** Observatory is a **gated decorative manuscript section** backed by a **rich registry that Deep Reading does not yet use as a pre-thesis lens system**.

---

## Appendix A — File anchors

| Concern | Path |
|---------|------|
| Lens registry | `kosuke-backend/app/observatory_lenses.py` |
| FE lens config exposure | `kosuke-backend/app/parallel_life_lens.py` |
| Call1 order (v1.1.1) | `kosuke-backend/app/parallel_life_deep_reading/prompts.py` |
| Lens evidence gate | `kosuke-backend/app/parallel_life_deep_reading/runtime_validation.py` |
| Call2 omit Observatory | `kosuke-backend/app/parallel_life_deep_reading/draft.py` |
| Meaning Observatory dashboard (unwired) | `kosuke-backend/app/observatory_engine.py` |
| NTT B Call1 artifact | `e2e_reports/deep-reading-v1.1-context-pack/selection_compression_ab/B_session_final.json` |

## Appendix B — Influence matrix (summary)

| Pipeline stage | Observatory today |
|----------------|-------------------|
| Structural relations | — |
| Meaning compression | — |
| Central thesis | — |
| Lost / Protected / Residue | — (Residue gates lenses only) |
| Observatory selection | **entry point** |
| Re-branch | — |
| Manuscript Observatory section | **only consumer** |
