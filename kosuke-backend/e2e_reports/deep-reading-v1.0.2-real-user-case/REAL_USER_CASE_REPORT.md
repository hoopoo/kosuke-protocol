# Deep Reading v1.0.2 — Real-user case report

**Date:** 2026-08-08  
**Case:** age-30 breakup / Japanese marriage / wife+son+cat present life

## Phase 1 — Root cause (pre-fix trace)

| Step | Finding |
|------|---------|
| FE payload | `source_text` included concrete present life; confirmation later showed collapse |
| Call 1 user prompt | Instruction literally said: `current_context には『現在の生活』だけを入れる` |
| LLM structured response | Emitted `current_context: ["現在の生活"]` |
| Runtime gates | Treated generic label as sufficient `current_context` coverage |
| Confirmation view | Rebuilt from grounded → user saw 「現在の生活」 |
| `items_to_confirm` | Coverage missing `present_question` appended raw + LLM already had `present_question` → duplicated |
| Approve error | Generic `入力の矛盾または不足` even with zero contradictions |
| Residue / title | Weak present anchors → downstream title flake risk |

**Exact collapse site:** Call 1 prompt instruction (not FE). Runtime failed to recover concrete lines from source.

## Fixes (v1.0.2)

1. Call 1 prompt → `parallel-life-call-1-v1.0.3` (preserve concrete current_context; do not invent present_question)
2. Runtime → `parallel-life-runtime-v1.0.6` (`preserve_concrete_current_context`, UI scrub, error separation)
3. UI labels: 分岐点 / 起きたこと / 選んだ道 / 選ばなかった道 / 今の生活 / 今も残る問い / 確認が必要な点
4. Title validation: **unchanged** (prior closing-alignment looseness reverted)
5. Call 2/3 prompts: **unchanged**

## Live rerun (local service, same case)

| Metric | Result |
|--------|--------|
| current_context after ground | `息子が一人と妻の三人で生活しています。また、猫がいます` |
| generic collapse | **No** |
| raw `present_question` in UI items | **No** |
| approve | OK → ready_for_draft |
| final status | **complete** |
| final title | `三十歳の別れと、いまの暮らし` |
| publishable | **true** |
| blocking | `[]` |
| elapsed | ~21.5s |

Artifacts: `REAL_USER_CASE_REPORT.json`, `call1_after_ground.json`, `call3.json`

## Unit tests

`253 passed` (full backend suite), including `tests/test_deep_reading_v102_current_context.py`.

## Recommendation

Deploy API container + Pages to production, force container restart on `production-api-r3`, then retest the same case on `parallel-life.shiroand.io`.
