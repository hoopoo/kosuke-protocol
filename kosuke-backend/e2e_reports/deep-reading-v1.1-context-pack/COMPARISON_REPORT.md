# Deep Reading v1.1 Context Pack — NTT Strict vs Contextual A/B

Generated: `2026-08-08T02:21:22.674265+00:00`  
Mode: offline structural (Call1 runtime gates; no live LLM)

## Fixture

Same branch + current_context (NTT career branch). Arm B adds an approved Context Pack
(NTT → foreign firms → own company; Observatory / Protocol Publishing / education–employment).

## Scorecard

| Metric | A Strict | B Contextual |
|--------|----------|--------------|
| Facts | 3 | 9 |
| Pack facts | 0 | 6 |
| Corpus chars | 94 | 281 |
| Pack present anchors | 0 | 3 |
| Selected lenses | 1 | 2 |
| Lenses with pack evidence | 0 | 2 |
| Project tokens in corpus | False | True |

## Verdict

- **Passed structural success criterion:** `True`
- A remains maximally restrained (zero pack facts).
- B expands approved evidence (career arc + present projects) for Residue / Observatory /
  Re-branch grounding **without** weakening ID checks, causality, affect, or title validation.
- Prompt pins: Strict `parallel-life-call-1-v1.0.3` / Contextual `parallel-life-call-1-v1.1.0`
- Runtime pins: Strict `parallel-life-runtime-v1.0.6` / Contextual `parallel-life-runtime-v1.1.0-exp`

## Human scorecard (for live LLM runs)

Use the same fixture against a live API with `DEEP_READING_CONTEXT_PACK_ENABLED=true`:

1. Depth — temporal arc, institutional reading, present return
2. Factual fidelity — zero unsupported bio/causality (Call3 blockers)
3. Naturalness — thesis unity, Lost/Protected asymmetry
4. Residue quality — past↔present with pack present anchors
5. Observatory — selected count + evidence provenance (branch vs pack)
6. Re-branch — grounded in approved projects
7. Title — thesis + closing under existing title validation

## Artifacts

- `fixtures/ntt_branch.txt`
- `fixtures/ntt_context_pack.json`
- `A_strict_call1.json`
- `B_contextual_call1.json`
- `COMPARISON_SUMMARY.json`
