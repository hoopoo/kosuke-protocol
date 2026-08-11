# Phase 1 — Residue zero diagnosis (live fixtures)

Date: 2026-08-07  
Source: `e2e_reports/deep-reading-v1.0.1-full-live-run/case*/call1.json`

## Per-case table

| Case | current_context supplied | grounded current-life facts | raw residue items | normalized | runtime-filtered | removal reasons | final primary residue |
|---|---|---|---|---|---|---|---|
| 1 | 三人家族・会社経営 | fact4 現在の家族/経営; fact5 息子・友人来訪 | `[]` | `[]` (no coerce) | n/a | none — never generated | none |
| 2 | **misfiled** later decision text | fact_4 現在の家族/経営; fact_5 感情的現在 | `[]` | `[]` | n/a | none — never generated | none |
| 3 | 文章・プロトコル | fact3 現在の仕事文脈 | `[]` | `[]` | n/a | none — never generated | none |
| 4 | 企業経験＋観測/文章/プロトコル | fact3 現在制作文脈 | `[]` | `[]` | n/a | none — never generated | none |

Notes:
- `parse_diagnostics.normalization_applied` was `[]` in all four → strict schema accept, no residue coerce path.
- No runtime residue filter existed that could zero a non-empty list.
- Call 1 system prompt (`parallel-life-call-1-v1.0.1`) **never mentions Residue**.

## Cause classification

| Code | Applies? | Evidence |
|---|---|---|
| A prompt generation failure | **YES (primary)** | Prompt has zero Residue instructions; model returns empty `items` |
| B structured schema omission/default | **YES (enabling)** | `ResidueCandidates.items` defaults to `[]`; schema does not require past/present anchors |
| C normalization loss | No | empty before normalize |
| D support ID mismatch | No | no candidates to validate |
| E inference-distance rejection | No | no filter applied |
| F sensitive-domain filter | No | no residue filter |
| G runtime over-filtering | No | no residue filter in gates |
| H field-name mismatch | No | wrapper `{items:[]}` already canonical |
| I other | Partial | Case2 `current_context` polluted by later-decision line (hurts present anchors) |

## Conclusion

Residue zero is an **implementation/prompt defect in Call 1 residue extraction**, not over-filtering.  
Call 1 must receive a focused v1.0.2 residue contract (prompt + schema fields for past/present anchors).  
Do **not** treat `user_question` as Residue.
