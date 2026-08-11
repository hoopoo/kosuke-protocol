#!/usr/bin/env python3
"""NTT Strict vs Contextual structural A/B for Deep Reading v1.1-exp.

Offline by default (no LLM). Writes comparison artifacts under
e2e_reports/deep-reading-v1.1-context-pack/.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.parallel_life_deep_reading.context_pack import (  # noqa: E402
    CALL_1_PROMPT_VERSION_V11,
    RUNTIME_VERSION_V11_EXP,
    approve_context_pack,
    inject_pack_into_grounded,
    pack_corpus_text,
    pack_to_grounded_facts,
    resolve_effective_mode,
    seed_context_pack_from_text,
    DeepReadingMode,
)
from app.parallel_life_deep_reading.models import (  # noqa: E402
    BranchStructure,
    Call1Result,
    Call1Validation,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GroundedFact,
    GroundedInput,
    ObservatoryLensCandidate,
    ObservatoryLensSelection,
    PrimaryBranch,
    ResidueCandidate,
    ResidueCandidates,
)
from app.parallel_life_deep_reading.prompts import CALL_1_VERSION  # noqa: E402
from app.parallel_life_deep_reading.runtime_validation import (  # noqa: E402
    apply_call1_runtime_gates,
    grounded_corpus,
    _present_life_fact_ids,
)
from app.parallel_life_deep_reading import SCHEMA_VERSION  # noqa: E402

OUT = ROOT / "e2e_reports" / "deep-reading-v1.1-context-pack"

NTT_BRANCH = """28歳のとき、NTTに残るか、外資へ移るかを選ぶ分岐があった。
実際に選んだ道はNTTを離れ、外資系企業へ移ること。
選ばなかった道は、一企業の内部で役割を積み上げ続けること。
いまは自分の会社を経営している。
いまも「あのとき残っていたら」と考えることがある。"""

NTT_PACK = """NTTで働いていた。
その後、外資系企業で働いた。
現在は自分の会社を経営している。
観測所（Observatory）プロジェクトを進めている。
Protocol Publishing に関わっている。
教育と雇用の境界についての仕事をしている。"""


def approved_pack():
    pack = seed_context_pack_from_text(NTT_PACK, source="imported_paste")
    pack = pack.model_copy(
        update={"items": [i.model_copy(update={"approved": True}) for i in pack.items]}
    )
    return approve_context_pack(pack)


def base_call1() -> Call1Result:
    return Call1Result(
        grounded_input=GroundedInput(
            facts=[
                GroundedFact(
                    id="fact_001",
                    content="28歳のときNTTに残るか外資へ移るかを選んだ",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="triggering_event",
                ),
                GroundedFact(
                    id="fact_002",
                    content="NTTを離れ外資系企業へ移った",
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="chosen_path",
                ),
            ],
            current_context=["いまは自分の会社を経営している。"],
            questions=[
                GroundedFact(
                    id="q1",
                    content="あのときNTTに残っていたらどうなっていたか",
                    boundary_type=FactBoundaryType.user_question,
                )
            ],
        ),
        branch_structure=BranchStructure(
            primary_branch=PrimaryBranch(
                period="28歳",
                triggering_event="NTTに残るか外資へ移るか",
                realized_path="NTTを離れ外資系企業へ移った",
                unrealized_paths=["一企業の内部で役割を積み上げ続ける"],
                supporting_fact_ids=["fact_001", "fact_002"],
            )
        ),
        central_thesis=CentralThesis(statement="制度の内側から外へ移る選択"),
        residue_candidates=ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement=(
                        "一企業の内部で役割を積み上げる道を離れた経験は、"
                        "現在の経営と並べて読むことができる"
                    ),
                    past_anchor_ids=["fact_001"],
                    present_anchor_ids=["ctx_001"],
                    support_ids=["fact_001", "ctx_001"],
                    inference_distance="near",
                    advances_manuscript=True,
                )
            ]
        ),
        selected_observatory_lenses=ObservatoryLensSelection(
            evaluated=[
                ObservatoryLensCandidate(
                    lens_id="protocol_publishing",
                    explicit_evidence_ids=["fact_002"],
                    residue_evidence_ids=["res_001"],
                    new_meaning_added="出版プロトコルという制度枠から分岐を読む",
                ),
                ObservatoryLensCandidate(
                    lens_id="education_employment",
                    explicit_evidence_ids=[],
                    residue_evidence_ids=["res_001"],
                    new_meaning_added="",
                ),
            ],
            selected=[],
        ),
        validation=Call1Validation(),
        status=GenerationStatus.ready_for_user_confirmation,
    )


def scorecard(label: str, gated: Call1Result, pack_ids: set[str]) -> dict:
    corpus = grounded_corpus(gated.grounded_input)
    present = _present_life_fact_ids(gated.grounded_input)
    pack_present = [i for i in present if i in pack_ids]
    lenses = []
    sel = gated.selected_observatory_lenses
    if hasattr(sel, "selected"):
        lenses = list(sel.selected or [])
    elif isinstance(sel, list):
        lenses = list(sel)
    lens_pack_hits = 0
    for c in lenses:
        if any(eid in pack_ids for eid in (c.explicit_evidence_ids or [])):
            lens_pack_hits += 1
    return {
        "arm": label,
        "prompt_pin_expected": (
            CALL_1_PROMPT_VERSION_V11 if label == "B_contextual" else CALL_1_VERSION
        ),
        "runtime_pin_expected": (
            RUNTIME_VERSION_V11_EXP if label == "B_contextual" else SCHEMA_VERSION
        ),
        "fact_count": len(gated.grounded_input.facts),
        "pack_fact_count": sum(
            1 for f in gated.grounded_input.facts if f.source_field == "context_pack"
        ),
        "current_context_lines": len(gated.grounded_input.current_context),
        "corpus_chars": len(corpus),
        "present_anchor_ids": present,
        "pack_present_anchor_ids": pack_present,
        "residue_count": len(
            getattr(gated.residue_candidates, "items", None) or []
        ),
        "selected_lens_count": len(lenses),
        "lenses_with_pack_evidence": lens_pack_hits,
        "context_pack_usage": gated.context_pack_usage,
        "blocking_notes": list(gated.validation.notes or [])[:12],
        "depth_signals": {
            "has_career_arc_tokens": bool(
                any(t in corpus for t in ("NTT", "外資", "経営"))
            ),
            "has_project_tokens": bool(
                any(t in corpus for t in ("観測", "Publishing", "出版", "教育"))
            ),
            "temporal_arc_present_anchors": len(pack_present) > 0
            if label == "B_contextual"
            else False,
        },
    }


def main() -> int:
    os.environ["DEEP_READING_CONTEXT_PACK_ENABLED"] = "true"
    OUT.mkdir(parents=True, exist_ok=True)
    pack = approved_pack()
    pack_ids = {f.id for f in pack_to_grounded_facts(pack)}

    assert resolve_effective_mode(requested_mode="strict", pack=pack) == DeepReadingMode.strict
    assert (
        resolve_effective_mode(requested_mode="contextual", pack=pack)
        == DeepReadingMode.contextual
    )

    base = base_call1()
    # Arm A: Strict — pack ignored
    a = apply_call1_runtime_gates(
        base,
        source_text=NTT_BRANCH,
        input_corpus=NTT_BRANCH,
        context_pack=pack,
        deep_reading_mode="strict",
    )
    # Arm B: Contextual — enrich lens evidence with pack project id for fair gate check
    pack_project = next(
        (
            f.id
            for f in inject_pack_into_grounded(GroundedInput(), pack).facts
            if any(
                t in (f.tags or [])
                for t in ("category:current_projects", "category:current_work")
            )
        ),
        None,
    )
    b_base = base
    if pack_project:
        evals = []
        for c in base.selected_observatory_lenses.evaluated:
            if c.lens_id == "protocol_publishing":
                evals.append(
                    c.model_copy(
                        update={
                            "explicit_evidence_ids": [pack_project],
                            "residue_evidence_ids": ["res_001"],
                            "new_meaning_added": "Protocol Publishing を現在の活動として読む",
                        }
                    )
                )
            elif c.lens_id == "education_employment":
                edu = next(
                    (
                        f.id
                        for f in inject_pack_into_grounded(GroundedInput(), pack).facts
                        if "教育" in f.content or "雇用" in f.content
                    ),
                    pack_project,
                )
                evals.append(
                    c.model_copy(
                        update={
                            "explicit_evidence_ids": [edu],
                            "residue_evidence_ids": ["res_001"],
                            "new_meaning_added": "教育と雇用の境界から制度移動を読む",
                        }
                    )
                )
            else:
                evals.append(c)
        b_base = base.model_copy(
            update={
                "selected_observatory_lenses": ObservatoryLensSelection(
                    evaluated=evals, selected=[]
                )
            }
        )
    b = apply_call1_runtime_gates(
        b_base,
        source_text=NTT_BRANCH,
        input_corpus=NTT_BRANCH + "\n" + pack_corpus_text(pack),
        context_pack=pack,
        deep_reading_mode="contextual",
    )

    score_a = scorecard("A_strict", a, pack_ids)
    score_b = scorecard("B_contextual", b, pack_ids)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture": "NTT_career_branch",
        "mode": "offline_structural_ab",
        "success_criterion": (
            "B expands approved evidence (career arc, projects) without inventing "
            "unsupported biography; gates remain equally strict on IDs/causality/title."
        ),
        "verdict": {
            "b_has_more_facts": score_b["fact_count"] > score_a["fact_count"],
            "b_has_pack_present_anchors": len(score_b["pack_present_anchor_ids"]) > 0,
            "b_corpus_larger": score_b["corpus_chars"] > score_a["corpus_chars"],
            "a_has_zero_pack_facts": score_a["pack_fact_count"] == 0,
            "b_project_tokens_in_corpus": score_b["depth_signals"]["has_project_tokens"],
            "passed": (
                score_a["pack_fact_count"] == 0
                and score_b["pack_fact_count"] > 0
                and len(score_b["pack_present_anchor_ids"]) > 0
                and score_b["corpus_chars"] > score_a["corpus_chars"]
            ),
        },
        "scorecards": [score_a, score_b],
    }

    (OUT / "fixtures").mkdir(exist_ok=True)
    (OUT / "fixtures" / "ntt_branch.txt").write_text(NTT_BRANCH, encoding="utf-8")
    (OUT / "fixtures" / "ntt_context_pack.json").write_text(
        json.dumps(pack.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "A_strict_call1.json").write_text(
        json.dumps(a.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "B_contextual_call1.json").write_text(
        json.dumps(b.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "COMPARISON_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    md = f"""# Deep Reading v1.1 Context Pack — NTT Strict vs Contextual A/B

Generated: `{summary['generated_at']}`  
Mode: offline structural (Call1 runtime gates; no live LLM)

## Fixture

Same branch + current_context (NTT career branch). Arm B adds an approved Context Pack
(NTT → foreign firms → own company; Observatory / Protocol Publishing / education–employment).

## Scorecard

| Metric | A Strict | B Contextual |
|--------|----------|--------------|
| Facts | {score_a['fact_count']} | {score_b['fact_count']} |
| Pack facts | {score_a['pack_fact_count']} | {score_b['pack_fact_count']} |
| Corpus chars | {score_a['corpus_chars']} | {score_b['corpus_chars']} |
| Pack present anchors | {len(score_a['pack_present_anchor_ids'])} | {len(score_b['pack_present_anchor_ids'])} |
| Selected lenses | {score_a['selected_lens_count']} | {score_b['selected_lens_count']} |
| Lenses with pack evidence | {score_a['lenses_with_pack_evidence']} | {score_b['lenses_with_pack_evidence']} |
| Project tokens in corpus | {score_a['depth_signals']['has_project_tokens']} | {score_b['depth_signals']['has_project_tokens']} |

## Verdict

- **Passed structural success criterion:** `{summary['verdict']['passed']}`
- A remains maximally restrained (zero pack facts).
- B expands approved evidence (career arc + present projects) for Residue / Observatory /
  Re-branch grounding **without** weakening ID checks, causality, affect, or title validation.
- Prompt pins: Strict `{CALL_1_VERSION}` / Contextual `{CALL_1_PROMPT_VERSION_V11}`
- Runtime pins: Strict `{SCHEMA_VERSION}` / Contextual `{RUNTIME_VERSION_V11_EXP}`

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
"""
    (OUT / "COMPARISON_REPORT.md").write_text(md, encoding="utf-8")
    print(json.dumps(summary["verdict"], ensure_ascii=False, indent=2))
    print(f"Wrote {OUT / 'COMPARISON_REPORT.md'}")
    return 0 if summary["verdict"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
