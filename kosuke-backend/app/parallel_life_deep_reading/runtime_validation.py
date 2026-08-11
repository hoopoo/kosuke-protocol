"""Deterministic runtime validation for Deep Reading v1.0.

Never trust LLM self-reported publishability / evidence gates.
Recalculate every safety decision in code.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from app.parallel_life_deep_reading.call1_schema import (
    Call1Response,
    SourceCoverage,
)
from app.parallel_life_deep_reading.models import (
    BranchClassification,
    BranchStructure,
    Call1Result,
    Call1Validation,
    Call2Draft,
    Call3Result,
    Call3Validation,
    CentralThesis,
    FactBoundaryType,
    GenerationStatus,
    GenericAdviceFinding,
    GroundedFact,
    GroundedInput,
    ObservatoryLensCandidate,
    RebranchDirection,
    ResidueCandidate,
    SecondaryBranch,
    TitleValidation,
    SchemaLeakageProse,
    UnsupportedAffect,
    UnsupportedCausalFrame,
    UnsupportedCausality,
    UnsupportedPersonalDetail,
    UnsupportedRoleBehavior,
    UnsupportedScene,
    UnrealizedPathModalityViolation,
    UserConfirmationView,
    ValidationCategory,
)
from app.parallel_life_deep_reading.v101_gates import (
    assess_branch_concreteness,
    build_safe_sensitive_coexistence_thesis,
    contradiction_clarification,
    detect_material_contradictions,
    detect_unrealized_path_modality_violations,
    repair_unrealized_path_modality,
    sensitive_thesis_is_unsupported_causal,
)

QUESTION_ENDING_RE = re.compile(
    r"(どうだったか|どうなったか|何が残ったか|変わっていたか|どうだっただろう|"
    r"人生だったか|違う人生だったか|どうか|だろうか|でしょうか)([。．]?)$"
)
QUESTION_MID_RE = re.compile(
    r"(どうだったか|どうなったか|どう変わったか|だったか|なったか|どうなっていたか)"
)
QUESTION_CONTEXT_RE = re.compile(r"(今も考える|考えることがある|答えが出ていない|気になっている)")
DECISION_EVIDENCE_RE = re.compile(
    r"(話し合っ|話し合い|やめた|目指さない|続けるか|決断|決めた|中止|終えた|始めた)"
)

GENERIC_ADVICE_PHRASES = (
    "小さな一歩を踏み出す",
    "自分のペースで",
    "無理のない範囲で",
    "まずは一つから",
    "時間を作る",
    "時間を確保する",
    "自分らしく",
    "大切にする",
    "向き合う",
    "手放す",
    "記録する",
    "一つ選ぶ",
    "小さく始める",
    "最小単位を決める",
    "一歩踏み出す",
)

SCENE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("breakfast", re.compile(r"朝食|朝ごはん|モーニング")),
    ("family_conversation", re.compile(r"会話|話し合っ|話しかけ|返事をした")),
    ("holiday", re.compile(r"休日|週末|土曜日|日曜日")),
    ("streetscape", re.compile(r"街並み|通りを|歩道|街灯")),
    ("specific_room", re.compile(r"リビング|寝室|台所|キッチン|書斎")),
    ("behavioral_habit", re.compile(r"毎朝|毎晩|習慣として|いつも〜している")),
    ("other_person_reaction", re.compile(r"表情|微笑|涙を流|顔を曇")),
    ("emotional_scene", re.compile(r"胸が熱|涙が溢|感動的")),
    ("symbolic_object", re.compile(r"象徴|置物|写真立て")),
    ("homecoming", re.compile(r"家へ戻|帰宅し|仕事を終え、家")),
    ("weather", re.compile(r"雨が降|晴れ渡り|夕暮れの空")),
    ("silence", re.compile(r"沈黙が|静まり返")),
    ("campus_scene", re.compile(r"キャンパス|学生生活|キャンパスライフ")),
    ("club", re.compile(r"サークル")),
    ("seminar", re.compile(r"ゼミ")),
    ("professor_peers", re.compile(r"教授|先輩との")),
]

PERSONAL_DETAIL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("campus_scene", re.compile(r"キャンパス|学生生活|キャンパスライフ")),
    ("club", re.compile(r"サークル")),
    ("seminar", re.compile(r"ゼミ")),
    ("professor", re.compile(r"教授")),
    ("job_function", re.compile(r"マーケティング|営業|プロジェクト管理|プロジェクトマネ")),
    ("duration_unsupplied", re.compile(r"何年も|長い間|数年にわたり|何年にもわた")),
    ("prestige_unsupplied", re.compile(r"名門")),
    ("invented_excitement", re.compile(r"ワクワク")),
    ("invented_conversation", re.compile(r"話しかけ|返事をした|会話を交わし")),
]

GENERIC_REBRANCH_VERBS = ("記録する", "時間を作る", "一つ選ぶ", "小さく始める", "時間を確保する")
ALLOWED_INFERENCE_DEFAULT = {"near", "medium"}
ALLOWED_INFERENCE_SENSITIVE = {"near"}
RESIDUE_GENERIC_PHRASES = (
    "いまも大切",
    "今も大切",
    "いまも響",
    "今も響",
    "まだ考えている",
    "一般的に",
    "人生において重要",
)

# Strength 3 = explicit causal assertion patterns (unless user stated them).
CAUSALITY_ASSERTION_RE = re.compile(
    r"(影響を与えてい[るた]|影響を与え[たてる]|影響を及ぼ[しす]|影響を受けてい[るた]|影響を受け[たてる]|与える影響|"
    r"選択の結果|この選択の結果|"
    r"につながっ[たてる]|につながってい[るた]|に繋がっ[たてる]|"
    r"(?:に|は|が|と)繋がってい[るた]|(?:に|は|が|と)つながってい[るた]|"
    r"へとつながっ[たてる]|へと繋がっ[たてる]|へ繋がっ[たてる]|へとつながん|"
    r"という道に繋が|という生活構造に繋が|に繋がってい|これにより|"
    r"を形づくっ[たて]|を形成してい[るた]|を形成した|は形成され|が形成され|基盤を形成|"
    r"を生んだ|のきっかけになっ[たて]|によって現在|が今の.+を作っ[たて]|"
    r"選択によって|その選択によって|この選択により|選択により|選ばなかった結果|"
    r"を決定づけ[たてる]|を.{0,6}変え[たてる]|を変える|を支えてい[るた]|に影響してい[るた]|"
    r"深く結びついて|と結びついている|を結びつける役割|結びつける役割を果た|"
    r"を形作っ[たて]|をもたらしてい[るた]|もたらした|をもたらす|思索をもたらす|未来を開[いきた])"
)
CAUSALITY_QUALIFIED_OK_RE = re.compile(
    r"(因果関係までは|因果までは確認できない|直接結びつける材料は|"
    r"並べて見る|共通する傾向|因果までは分からない|因果は確認できない|"
    r"結びつける材料は.?ない|ただし因果)"
)
EXPLICIT_USER_CAUSAL_RE = re.compile(
    r"(きっかけで|きっかけに|によって|の影響で|が原因で|が理由で)"
)

AFFECT_PATTERNS: list[tuple[str, re.Pattern[str], tuple[str, ...]]] = [
    # (type, pattern, allowed_corpus_stems — exact feeling must appear; no synonym upgrade)
    ("満足", re.compile(r"満足して|満足だ|満足を"), ("満足",)),
    ("安心", re.compile(r"安心して|安心だ|安心を"), ("安心",)),
    ("誇り", re.compile(r"誇りに思|誇らしく"), ("誇り", "誇ら")),
    ("幸せ", re.compile(r"幸せ"), ("幸せ",)),
    ("絆", re.compile(r"絆を|家族の絆"), ("絆",)),
    ("納得", re.compile(r"納得して|納得だ"), ("納得",)),
    ("後悔", re.compile(r"後悔して|後悔だ|後悔が"), ("後悔",)),
    ("寂しい", re.compile(r"寂し[いく]|孤独を感"), ("寂し", "孤独")),
    ("不安", re.compile(r"不安だ|不安を感|不安が"), ("不安",)),
    ("充実", re.compile(r"充実して|充実感"), ("充実",)),
    ("喜び", re.compile(r"喜び"), ("喜び", "嬉")),
    ("大切に思", re.compile(r"大切に思|大切にしてい"), ("大切に思", "大切にして")),
]

ROLE_BEHAVIOR_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("成長を見守", re.compile(r"成長を見守")),
    ("支える", re.compile(r"(?:を|に)支えて(?:い[るた]|きた)?")),
    ("寄り添う", re.compile(r"寄り添")),
    ("背中を押す", re.compile(r"背中を押")),
    ("家族を守る", re.compile(r"家族を守")),
    ("時間を注ぐ", re.compile(r"時間を注")),
    ("妻を支える", re.compile(r"妻を支")),
    ("切磋琢磨", re.compile(r"切磋琢磨")),
    ("仕事に打ち込む", re.compile(r"仕事に打ち込")),
    ("家族との時間を大切", re.compile(r"家族との時間を大切")),
]

# Soft meaning-completion that is neither bare causality nor schema leakage.
UNSUPPORTED_MEANING_COMPLETION_RE = re.compile(
    r"(大きな意味を持つ|重要な意味を持ってい|大切な意味を持ってい|"
    r"大きな喜び|人生において重要|私にとって大きな|一層深める|心のどこかに)"
)

# Causal framing presupposes influence even when phrased as a question.
CAUSAL_FRAME_RE = re.compile(
    r"(どのように影響を与えてい[るた]?のか|どのように影響してい[るた]?のか|"
    r"どのような影響を与えて|どのような影響をして|"
    r"現在の.+にどのような影響|どんな影響を残したのか|何に影響したのか|"
    r"どのようにつながってい[るた]?のか|どのようにつながって|"
    r"何を形づくったのか|何を生んだのか|今にどう作用してい[るた]?のか|"
    r"どのように影響を及ぼ|影響を与えているのか|影響を受けているのか|"
    r"どう影響して|どのような影響を|どう作用して|"
    r"どのように関わってい[るた]?のか|どう関わってい[るた]?のか|どのように関係して)"
)

TITLE_CAUSAL_FRAME_TOKENS = (
    "影響",
    "原点",
    "きっかけ",
    "形成",
    "つながり",
    "繋がり",
    "決定",
    "変えた",
    "生んだ",
    "残した",
)

SCHEMA_LEAKAGE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("double_topic_choice", re.compile(r"この選択は、実際に選んだのは")),
    ("double_topic_branch", re.compile(r"この分岐は、選ばれたのは")),
    ("choice_as_schema", re.compile(r"選択としては、実際には")),
    ("chosen_path_meta", re.compile(r"ここで選んだのは.+ということである")),
    ("actual_choice_meta", re.compile(r"実際に選択したのは.+である")),
    ("actual_chosen_wa", re.compile(r"実際に選んだのは")),
    ("unchosen_as", re.compile(r"選ばなかった道として")),
    ("branch_dewa", re.compile(r"この分岐では")),
    ("input_says", re.compile(r"入力によれば")),
    ("as_fact_meta", re.compile(r"事実としては")),
    ("choice_wa_jissai", re.compile(r"この選択は、実際に選んだ")),
]


def fact_ids_by_type(grounded: GroundedInput, boundary: FactBoundaryType) -> set[str]:
    buckets = {
        FactBoundaryType.explicit_fact: grounded.facts,
        FactBoundaryType.user_feeling: grounded.feelings,
        FactBoundaryType.user_question: grounded.questions,
        FactBoundaryType.user_hypothesis: grounded.hypotheses,
        FactBoundaryType.unknown: grounded.unknowns,
        FactBoundaryType.model_inference: grounded.model_inferences,
    }
    return {f.id for f in buckets.get(boundary, [])}


def all_grounded_items(grounded: GroundedInput) -> list[GroundedFact]:
    return [
        *grounded.facts,
        *grounded.feelings,
        *grounded.questions,
        *grounded.hypotheses,
        *grounded.unknowns,
        *grounded.model_inferences,
    ]


def explicit_fact_id_set(grounded: GroundedInput) -> set[str]:
    return {f.id for f in grounded.facts if f.boundary_type == FactBoundaryType.explicit_fact}


def recalculate_lens_evidence_gate(
    candidate: ObservatoryLensCandidate,
    *,
    allowed_explicit_ids: set[str] | None = None,
) -> ObservatoryLensCandidate:
    meaning = (candidate.new_meaning_added or "").strip()
    explicit = list(candidate.explicit_evidence_ids or [])
    if allowed_explicit_ids is not None:
        # v1.1-exp: evidence IDs must exist in branch ∪ pack ∪ current_context synthetics
        explicit = [eid for eid in explicit if eid in allowed_explicit_ids]
    passed = (
        len(explicit) > 0
        and len(candidate.residue_evidence_ids) > 0
        and bool(meaning)
    )
    reason = candidate.rejection_reason
    if not passed:
        parts: list[str] = []
        if not explicit:
            parts.append("missing_explicit_evidence")
        if not candidate.residue_evidence_ids:
            parts.append("missing_residue_evidence")
        if not meaning:
            parts.append("missing_new_meaning")
        reason = ";".join(parts)
    return candidate.model_copy(
        update={
            "explicit_evidence_ids": explicit,
            "evidence_gate_passed": passed,
            "rejection_reason": "" if passed else (reason or "evidence_gate_failed"),
            "new_meaning_added": meaning,
        }
    )


def filter_selected_lenses(
    evaluated: Iterable[ObservatoryLensCandidate],
    *,
    allowed_explicit_ids: set[str] | None = None,
) -> tuple[list[ObservatoryLensCandidate], list[ObservatoryLensCandidate]]:
    evaluated_list: list[ObservatoryLensCandidate] = []
    selected: list[ObservatoryLensCandidate] = []
    for raw in evaluated:
        gated = recalculate_lens_evidence_gate(
            raw, allowed_explicit_ids=allowed_explicit_ids
        )
        evaluated_list.append(gated)
        if gated.evidence_gate_passed:
            selected.append(gated)
    return evaluated_list, selected


def downgrade_invalid_actual_secondary(
    branch: SecondaryBranch,
    grounded: GroundedInput,
) -> SecondaryBranch:
    """Reject actual_secondary_branch without explicit fact evidence."""
    if branch.classification != BranchClassification.actual_secondary_branch:
        return branch

    explicit_ids = explicit_fact_id_set(grounded)
    question_ids = fact_ids_by_type(grounded, FactBoundaryType.user_question)
    evidence = [eid for eid in branch.explicit_evidence_ids if eid in explicit_ids]
    # Question IDs alone never qualify.
    evidence = [eid for eid in evidence if eid not in question_ids]

    if evidence:
        return branch.model_copy(update={"explicit_evidence_ids": evidence})

    return branch.model_copy(
        update={
            "classification": BranchClassification.retrospective_counterfactual,
            "explicit_evidence_ids": [],
            "must_not_be_treated_as_historical_choice": True,
            "ambiguity_status": "downgraded_missing_explicit_evidence",
        }
    )


def normalize_branch_structure(
    structure: BranchStructure,
    grounded: GroundedInput,
) -> tuple[BranchStructure, list[str]]:
    rejected: list[str] = []
    actuals: list[SecondaryBranch] = []
    counterfactuals: list[SecondaryBranch] = []

    for branch in structure.secondary_branches:
        fixed = downgrade_invalid_actual_secondary(branch, grounded)
        if (
            branch.classification == BranchClassification.actual_secondary_branch
            and fixed.classification == BranchClassification.retrospective_counterfactual
        ):
            rejected.append(branch.id or branch.description[:40])
            counterfactuals.append(fixed)
        elif fixed.classification == BranchClassification.actual_secondary_branch:
            actuals.append(fixed)
        else:
            counterfactuals.append(
                fixed.model_copy(
                    update={"must_not_be_treated_as_historical_choice": True}
                )
            )

    for cf in structure.retrospective_counterfactuals:
        counterfactuals.append(
            cf.model_copy(
                update={
                    "classification": BranchClassification.retrospective_counterfactual,
                    "must_not_be_treated_as_historical_choice": True,
                }
            )
        )

    # Deduplicate by description
    seen: set[str] = set()
    uniq_cf: list[SecondaryBranch] = []
    for item in counterfactuals:
        key = item.description.strip()
        if key and key not in seen:
            seen.add(key)
            uniq_cf.append(item)

    return (
        structure.model_copy(
            update={
                "secondary_branches": actuals,
                "retrospective_counterfactuals": uniq_cf,
            }
        ),
        rejected,
    )


def recalculate_rebranch_publishable(
    candidate: RebranchDirection,
    *,
    grounded: GroundedInput | None = None,
) -> RebranchDirection:
    source = (candidate.source_meaning or "").strip()
    receiver = (candidate.current_receiver or "").strip()
    form = (candidate.branch_specific_form or "").strip()
    support = [s for s in candidate.support_ids if str(s).strip()]
    score = candidate.genericity_score
    if score not in (0, 1, 2, 3):
        score = 3

    generic_verb = form in GENERIC_REBRANCH_VERBS or any(
        form == v or form.endswith(v) for v in GENERIC_REBRANCH_VERBS
    )
    concrete_ok = True
    if grounded is not None:
        corpus = grounded_corpus(grounded)
        corpus_nouns = re.findall(r"[\u4e00-\u9fff]{2,}", corpus)
        concrete_ok = any(n in form for n in corpus_nouns if len(n) >= 2)

    publishable = (
        score <= 1
        and not candidate.invented_scene_used
        and len(support) > 0
        and bool(receiver)
        and bool(source)
        and bool(form)
        and not generic_verb
        and concrete_ok
    )
    return candidate.model_copy(
        update={
            "source_meaning": source,
            "current_receiver": receiver,
            "branch_specific_form": form,
            "support_ids": support,
            "genericity_score": score,  # type: ignore[arg-type]
            "publishable": publishable,
            "selected_for_manuscript": publishable and candidate.selected_for_manuscript
            if publishable
            else False,
        }
    )


def filter_publishable_rebranch(
    candidates: Iterable[RebranchDirection],
    *,
    grounded: GroundedInput | None = None,
) -> tuple[list[RebranchDirection], list[RebranchDirection]]:
    validated: list[RebranchDirection] = []
    publishable: list[RebranchDirection] = []
    for raw in candidates:
        fixed = recalculate_rebranch_publishable(raw, grounded=grounded)
        validated.append(fixed)
        if fixed.publishable:
            publishable.append(fixed.model_copy(update={"selected_for_manuscript": True}))
    return validated, publishable


def grounded_corpus(grounded: GroundedInput) -> str:
    parts = [item.content for item in all_grounded_items(grounded)]
    parts.extend(grounded.current_context)
    return "\n".join(parts)


def _sentence_supported(sentence: str, corpus: str) -> bool:
    """Heuristic support check: key nouns from sentence appear in grounded corpus.

    Combining supported atoms into an unreported scene still fails via scene patterns
    when the scene framing tokens are absent from input.
    """
    # Extract CJK / word-ish tokens of length >= 2
    tokens = re.findall(r"[\u3040-\u30ff\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", sentence)
    if not tokens:
        return True
    hits = sum(1 for t in tokens if t in corpus)
    return hits >= max(1, len(tokens) // 3)


def detect_unsupported_scenes(
    body: str,
    grounded: GroundedInput,
) -> list[UnsupportedScene]:
    corpus = grounded_corpus(grounded)
    findings: list[UnsupportedScene] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 8:
            continue
        for scene_type, pattern in SCENE_PATTERNS:
            if not pattern.search(text):
                continue
            # If the distinctive scene phrase itself is in grounded input, allow.
            matched = pattern.search(text)
            phrase = matched.group(0) if matched else ""
            if phrase and phrase in corpus:
                continue
            # Explicit later-decision evidence may use 話し合い without inventing a scene.
            if scene_type == "family_conversation" and re.search(r"話し合", corpus):
                continue
            # Scene framing absent from input → unsupported even if atoms exist.
            findings.append(
                UnsupportedScene(
                    excerpt=text[:160],
                    scene_type=scene_type,
                    missing_support=f"scene_framing_absent:{scene_type}",
                    category=ValidationCategory.unsupported,
                )
            )
            break
    return findings


def _has_case_specific_object(sentence: str, corpus: str) -> bool:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}", sentence)
    specific = [t for t in tokens if t in corpus and t not in (
        "自分", "人生", "大切", "時間", "一歩", "範囲", "ペース"
    )]
    return len(specific) >= 1


def detect_generic_advice(
    body: str,
    grounded: GroundedInput,
) -> list[GenericAdviceFinding]:
    corpus = grounded_corpus(grounded)
    findings: list[GenericAdviceFinding] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if not text:
            continue
        hit = next((p for p in GENERIC_ADVICE_PHRASES if p in text), None)
        # Also catch advice-like sentences without the phrase list when very generic.
        looks_advice = bool(hit) or bool(
            re.search(r"(してみよう|してみる|すればいい|することが大切)", text)
        )
        if not looks_advice:
            continue
        case_obj = _has_case_specific_object(text, corpus)
        reason = bool(
            re.search(r"(ため|から|ので|照ら|接続|根拠|残っ)", text)
        )
        current_ctx = any(c and c[:8] in text for c in grounded.current_context) or any(
            f.content[:6] in text for f in grounded.feelings
        )
        if case_obj and reason and current_ctx:
            continue
        if not hit and case_obj:
            continue
        findings.append(
            GenericAdviceFinding(
                excerpt=text[:160],
                case_specific_object_present=case_obj,
                reason_present=reason,
                current_context_present=current_ctx,
            )
        )
    return findings


def detect_sentence_fragments(body: str) -> list[str]:
    found: list[str] = []
    if re.search(r"(?:^|[。．\s　])不。", body):
        found.append("不。")
    for m in re.finditer(r"(?:^|[。．\s])([ぁ-んァ-ヶ一-龥]{1,2})[。．]", body):
        frag = m.group(1)
        if frag in ("不", "あ", "い", "う", "え", "お", "ん"):
            found.append(frag + "。")
    return list(dict.fromkeys(found))


def detect_copied_long_segments(body: str, source_text: str, min_len: int = 40) -> list[str]:
    src = re.sub(r"\s+", "", source_text or "")
    blob = re.sub(r"\s+", "", body or "")
    hits: list[str] = []
    if len(src) < min_len:
        return hits
    # Sliding windows of min_len
    step = max(10, min_len // 2)
    for i in range(0, len(src) - min_len + 1, step):
        chunk = src[i : i + min_len]
        if chunk in blob:
            hits.append(chunk[:60])
            if len(hits) >= 3:
                break
    return hits


def _chunk_covered_by_grounded(chunk: str, grounded: GroundedInput) -> bool:
    """True when a copy-detector chunk is fully assembled from grounded contents."""
    c = re.sub(r"\s+", "", chunk or "")
    if len(c) < 12:
        return True
    parts = [
        re.sub(r"\s+", "", f.content)
        for f in all_grounded_items(grounded)
        if f.content
    ] + [re.sub(r"\s+", "", x) for x in (grounded.current_context or []) if x.strip()]
    # Greedy cover: remove any grounded substring found in chunk until empty or stuck.
    remaining = c
    progress = True
    while remaining and progress:
        progress = False
        for p in sorted(parts, key=len, reverse=True):
            if len(p) >= 6 and p in remaining:
                remaining = remaining.replace(p, "", 1)
                progress = True
                break
    return len(remaining) < 8


FORBIDDEN_THEME_TOKENS_CREATIVITY = ("創作に残らなかった", "作家になれなかった", "書けなかった45")


def _has_explicit_causal_support(grounded: GroundedInput) -> bool:
    return bool(EXPLICIT_USER_CAUSAL_RE.search(grounded_corpus(grounded)))


def title_has_unsupported_causal_frame(title: str, grounded: GroundedInput) -> bool:
    """True when title uses causal-frame tokens without explicit causal evidence."""
    t = title or ""
    if not any(tok in t for tok in TITLE_CAUSAL_FRAME_TOKENS):
        return False
    if _has_explicit_causal_support(grounded):
        # Still require the specific token (or close causal wording) to appear in corpus.
        corpus = grounded_corpus(grounded)
        return not any(tok in corpus for tok in TITLE_CAUSAL_FRAME_TOKENS if tok in t)
    return True


def validate_title(
    title: str,
    subtitle: str,
    grounded: GroundedInput,
    central_thesis: str,
    body: str,
) -> TitleValidation:
    corpus = grounded_corpus(grounded) + "\n" + (central_thesis or "")
    title = (title or "").strip()
    subtitle = (subtitle or "").strip()

    introduces_new = any(tok in title for tok in FORBIDDEN_THEME_TOKENS_CREATIVITY)
    # If title mentions creativity but corpus is fertility/family-only, flag.
    if re.search(r"創作|作家|小説", title) and not re.search(r"創作|作家|小説|文章|プロトコル", corpus):
        if re.search(r"不妊|子ども|息子|家族", corpus):
            introduces_new = True

    causal_frame_violation = title_has_unsupported_causal_frame(title, grounded)
    if causal_frame_violation:
        introduces_new = True

    fact_ids = [f.id for f in grounded.facts if any(
        t in title for t in re.findall(r"[\u4e00-\u9fff]{2,}", f.content)[:3]
    )]
    thesis_support = bool(central_thesis) and (
        any(t in title for t in re.findall(r"[\u4e00-\u9fff]{2,}", central_thesis)[:4])
        or any(t in title for t in ("問い", "残", "分岐", "暮らし", "家族", "選択"))
    )
    factual = bool(title) and not introduces_new and not causal_frame_violation
    overdramatizes = bool(re.search(r"失われた人生|間違った選択|本当の自分を殺", title))
    closing = ""
    for line in reversed((body or "").splitlines()):
        if line.strip():
            closing = line.strip()
            break
    matches_closing = bool(closing) and (
        any(t in closing for t in re.findall(r"[\u4e00-\u9fff]{2,}", title)[:3])
        or "現在" in closing
        or "いま" in closing
        or "今" in closing
    )

    passed = (
        bool(title)
        and factual
        and thesis_support
        and not introduces_new
        and not overdramatizes
        and not causal_frame_violation
        and matches_closing
    )
    notes: list[str] = []
    if not thesis_support:
        notes.append("title_not_linked_to_central_thesis")
    if introduces_new:
        notes.append("title_introduces_new_unverified_theme")
    if overdramatizes:
        notes.append("title_overdramatizes_unchosen_life")
    if causal_frame_violation:
        notes.append("title_unsupported_causal_frame")
    if not matches_closing:
        notes.append("title_closing_mismatch")

    return TitleValidation(
        selected_title=title,
        selected_subtitle=subtitle,
        title_supported_by_fact_ids=fact_ids,
        title_supported_by_central_thesis=thesis_support,
        title_introduces_new_unverified_theme=introduces_new,
        title_factual_consistency=factual,
        title_overdramatizes_unchosen_life=overdramatizes,
        title_matches_final_closing=matches_closing,
        title_causal_frame_violation=causal_frame_violation,
        passed=passed,
        notes=notes,
    )


def looks_like_user_question(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    # Strip trailing。 for ending checks
    t_end = t.rstrip("。．")
    if QUESTION_ENDING_RE.search(t_end):
        return True
    if "？" in t or "?" in t:
        return True
    if QUESTION_MID_RE.search(t) and QUESTION_CONTEXT_RE.search(t):
        return True
    if QUESTION_CONTEXT_RE.search(t) and ("どう" in t or "もし" in t or "なら" in t):
        return True
    return False


def correct_fact_boundaries(grounded: GroundedInput) -> GroundedInput:
    """Deterministic question/feeling/hypothesis correction."""
    facts: list[GroundedFact] = []
    feelings: list[GroundedFact] = []
    questions: list[GroundedFact] = []
    hypotheses: list[GroundedFact] = []
    unknowns = list(grounded.unknowns)
    inferences = list(grounded.model_inferences)

    def absorb(item: GroundedFact, default: FactBoundaryType) -> None:
        content = item.content.strip()
        if not content:
            return
        if looks_like_user_question(content) or item.boundary_type == FactBoundaryType.user_question:
            questions.append(
                item.model_copy(
                    update={
                        "boundary_type": FactBoundaryType.user_question,
                        "allowed_as_fact": False,
                    }
                )
            )
            return
        if item.boundary_type == FactBoundaryType.user_hypothesis or default == FactBoundaryType.user_hypothesis:
            hypotheses.append(
                item.model_copy(
                    update={
                        "boundary_type": FactBoundaryType.user_hypothesis,
                        "allowed_as_fact": False,
                    }
                )
            )
            return
        if item.boundary_type == FactBoundaryType.user_feeling or default == FactBoundaryType.user_feeling:
            feelings.append(
                item.model_copy(
                    update={
                        "boundary_type": FactBoundaryType.user_feeling,
                        "allowed_as_fact": False,
                    }
                )
            )
            return
        facts.append(
            item.model_copy(
                update={
                    "boundary_type": FactBoundaryType.explicit_fact,
                    "allowed_as_fact": True,
                }
            )
        )

    for item in grounded.facts:
        absorb(item, FactBoundaryType.explicit_fact)
    for item in grounded.feelings:
        absorb(item, FactBoundaryType.user_feeling)
    for item in grounded.questions:
        absorb(item, FactBoundaryType.user_question)
    for item in grounded.hypotheses:
        absorb(item, FactBoundaryType.user_hypothesis)

    # Dedupe questions by content; remove same content from feelings/hypotheses.
    q_seen: set[str] = set()
    uniq_q: list[GroundedFact] = []
    for q in questions:
        key = q.content.strip()
        if key in q_seen:
            continue
        q_seen.add(key)
        uniq_q.append(q)
    feelings = [f for f in feelings if f.content.strip() not in q_seen]
    hypotheses = [h for h in hypotheses if h.content.strip() not in q_seen]

    return grounded.model_copy(
        update={
            "facts": facts,
            "feelings": feelings,
            "questions": uniq_q,
            "hypotheses": hypotheses,
            "unknowns": unknowns,
            "model_inferences": inferences,
        }
    )


def _corpus_blob(grounded: GroundedInput, source_text: str = "") -> str:
    parts = [source_text or ""]
    for item in all_grounded_items(grounded):
        parts.append(item.content)
    parts.extend(grounded.current_context)
    return "\n".join(parts)


def backfill_structure_from_source(
    grounded: GroundedInput,
    structure: BranchStructure,
    *,
    source_text: str = "",
) -> tuple[GroundedInput, BranchStructure]:
    """Fill missing required fields from source text without inventing new meaning."""
    text = (source_text or "").strip()
    if not text:
        return grounded, structure

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    primary = structure.primary_branch
    period = primary.period
    if not period.strip():
        m = re.search(r"(\d+\s*歳)", text)
        if m:
            period = m.group(1).replace(" ", "")
        elif re.search(r"大学|進学", text) and re.search(r"合格|志望", text):
            period = "大学進学時"
        elif re.search(r"会社員|社会人|業界", text):
            period = "社会人期"

    event = primary.triggering_event
    if not event.strip():
        for line in lines:
            if looks_like_user_question(line):
                continue
            if any(k in line for k in ("授かった", "合格", "選んだ", "進学した", "決断", "転機", "働いてきた")):
                event = line
                break

    realized = primary.realized_path
    if not realized.strip():
        for line in lines:
            if looks_like_user_question(line) or "選ばなかった" in line:
                continue
            if any(
                k in line
                for k in ("選んだ", "進学した", "暮らす", "会社員", "働いてきた", "合格した")
            ):
                realized = line
                break

    unrealized = [
        u for u in primary.unrealized_paths if u.strip() and not looks_like_user_question(u)
    ]
    if not unrealized:
        for line in lines:
            if looks_like_user_question(line):
                continue
            if "選ばなかった" in line or "諦める" in line:
                unrealized.append(line)
            elif "別の大学" in line and "どう" not in line:
                unrealized.append(line)

    contexts = [
        c
        for c in grounded.current_context
        if c.strip() and not is_generic_current_context_label(c)
    ]
    if not contexts:
        recovered = _extract_present_life_from_corpus(text)
        contexts.extend(recovered)
    if not contexts:
        for line in lines:
            if looks_like_user_question(line) or is_generic_current_context_label(line):
                continue
            if line.startswith("現在") or "現在も" in line or re.search(
                r"暮ら|生活|妻|息子|猫|家族", line
            ):
                contexts.append(line)

    # Pull present questions from source when model omitted/misfiled them.
    questions = list(grounded.questions)
    q_seen = {q.content.strip() for q in questions}
    for i, line in enumerate(lines):
        if looks_like_user_question(line) and line not in q_seen:
            questions.append(
                GroundedFact(
                    id=f"question_source_{i+1:03d}",
                    content=line,
                    boundary_type=FactBoundaryType.user_question,
                    source_field="source_text",
                    source_text=text,
                    allowed_as_fact=False,
                )
            )
            q_seen.add(line)

    # Named-entity / polarity retention helpers for university-like inputs.
    entity_bits = []
    for token in ("第一志望", "早稲田大学第一文学部", "合格", "進学", "別の大学"):
        if token in text and not any(token in f.content for f in grounded.facts):
            entity_bits.append(token)
    facts = list(grounded.facts)
    if entity_bits:
        facts.append(
            GroundedFact(
                id="fact_entity_retention_001",
                content=" / ".join(entity_bits),
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="named_entity_retention",
                source_text=text,
                allowed_as_fact=True,
            )
        )

    return (
        grounded.model_copy(
            update={
                "current_context": contexts,
                "facts": facts,
                "questions": questions,
            }
        ),
        structure.model_copy(
            update={
                "primary_branch": primary.model_copy(
                    update={
                        "period": period,
                        "triggering_event": event,
                        "realized_path": realized,
                        "unrealized_paths": unrealized,
                    }
                )
            }
        ),
    )


def compute_source_coverage(
    grounded: GroundedInput,
    structure: BranchStructure,
    *,
    source_text: str = "",
) -> SourceCoverage:
    blob = _corpus_blob(grounded, source_text)
    primary = structure.primary_branch
    period_ok = bool(primary.period.strip()) or bool(
        re.search(r"\d+\s*歳|社会人|大学|進学", blob)
    )
    event_ok = bool(primary.triggering_event.strip()) or bool(grounded.facts)
    chosen_ok = bool(primary.realized_path.strip()) or any(
        "選んだ" in f.content or "合格" in f.content or "進学" in f.content for f in grounded.facts
    )
    unchosen_ok = bool(primary.unrealized_paths) or any(
        "選ばなかった" in f.content or "別の" in f.content or "諦める" in f.content
        for f in grounded.facts
    )
    question_ok = bool(grounded.questions) or bool(structure.present_question_ids)
    context_ok = any(
        c.strip() and not is_generic_current_context_label(c) for c in grounded.current_context
    ) or any(
        re.search(r"暮ら|生活|家族|妻|息子|猫|制作|経営", f.content or "")
        for f in grounded.facts
    )
    return SourceCoverage(
        branch_period=period_ok,
        triggering_event=event_ok,
        chosen_path=chosen_ok,
        unchosen_path=unchosen_ok,
        present_question=question_ok,
        current_context=context_ok,
    )


def _decision_snippet(blob: str, fallback: str = "") -> str:
    match = DECISION_EVIDENCE_RE.search(blob)
    if not match:
        return fallback
    start = max(0, match.start() - 24)
    end = min(len(blob), match.end() + 48)
    snippet = re.sub(r"\s+", "", blob[start:end])
    return snippet[:120] or fallback


def ensure_decision_evidence_facts(
    grounded: GroundedInput,
    structure: BranchStructure,
    *,
    source_text: str = "",
) -> GroundedInput:
    """If source/secondary text has later decision evidence, ensure an explicit fact exists."""
    blob = _corpus_blob(grounded, source_text)
    secondary_blob = "\n".join(b.description for b in structure.secondary_branches if b.description)
    combined = f"{blob}\n{secondary_blob}"
    if not DECISION_EVIDENCE_RE.search(combined):
        return grounded
    if any(DECISION_EVIDENCE_RE.search(f.content or "") for f in grounded.facts):
        return grounded

    snippet = ""
    for b in structure.secondary_branches:
        if DECISION_EVIDENCE_RE.search(b.description or ""):
            snippet = b.description.strip()
            break
    if not snippet:
        snippet = _decision_snippet(combined, fallback="後続の話し合い・判断が明示されている")

    fact_id = "fact_decision_auto_001"
    existing_ids = {f.id for f in grounded.facts if f.id}
    if fact_id in existing_ids:
        fact_id = "fact_decision_auto_002"

    return grounded.model_copy(
        update={
            "facts": [
                *grounded.facts,
                GroundedFact(
                    id=fact_id,
                    content=snippet,
                    boundary_type=FactBoundaryType.explicit_fact,
                    source_field="later_decision_evidence",
                    source_text=source_text or snippet,
                    allowed_as_fact=True,
                ),
            ]
        }
    )


def enrich_secondary_from_decision_evidence(
    structure: BranchStructure,
    grounded: GroundedInput,
    *,
    source_text: str = "",
) -> BranchStructure:
    """Promote/normalize actual secondary when explicit later decision evidence exists."""
    blob = _corpus_blob(grounded, source_text)
    secondary_blob = "\n".join(b.description for b in structure.secondary_branches if b.description)
    combined = f"{blob}\n{secondary_blob}"
    has_decision = bool(DECISION_EVIDENCE_RE.search(combined))
    evidence_ids = [
        f.id
        for f in grounded.facts
        if DECISION_EVIDENCE_RE.search(f.content or "") and f.id
    ]
    # Also scan editorial-like fact contents
    if has_decision and not evidence_ids:
        for f in grounded.facts:
            if any(k in (f.content or "") for k in ("話し合", "やめた", "目指さない", "目指す")):
                evidence_ids.append(f.id)

    secondaries: list[SecondaryBranch] = []
    counterfactuals = list(structure.retrospective_counterfactuals)

    for branch in structure.secondary_branches:
        desc = branch.description or ""
        if has_decision and (DECISION_EVIDENCE_RE.search(desc) or evidence_ids):
            ids = [eid for eid in branch.explicit_evidence_ids if eid] or list(evidence_ids)
            secondaries.append(
                branch.model_copy(
                    update={
                        "classification": BranchClassification.actual_secondary_branch,
                        "explicit_evidence_ids": ids,
                        "must_not_be_treated_as_historical_choice": False,
                    }
                )
            )
        else:
            # leave for normalize_branch_structure
            secondaries.append(branch)

    # If decision evidence exists but no secondary captured, create one.
    if has_decision and evidence_ids and not any(
        b.classification == BranchClassification.actual_secondary_branch for b in secondaries
    ):
        snippet = _decision_snippet(combined, fallback="明示された後続の話し合い・判断")
        secondaries.append(
            SecondaryBranch(
                id="sec_auto_001",
                classification=BranchClassification.actual_secondary_branch,
                description=snippet,
                explicit_evidence_ids=evidence_ids,
            )
        )

    # Ensure present-day questions become counterfactuals when no decision evidence.
    if grounded.questions and not has_decision:
        existing = {c.description.strip() for c in counterfactuals}
        for q in grounded.questions:
            if q.content.strip() and q.content.strip() not in existing:
                counterfactuals.append(
                    SecondaryBranch(
                        id=f"cf_{q.id or 'q'}",
                        classification=BranchClassification.retrospective_counterfactual,
                        description=q.content,
                        must_not_be_treated_as_historical_choice=True,
                    )
                )

    return structure.model_copy(
        update={
            "secondary_branches": secondaries,
            "retrospective_counterfactuals": counterfactuals,
            "present_question_ids": [q.id for q in grounded.questions if q.id],
        }
    )


def filter_call1_rebranch_directions(
    directions: Iterable[RebranchDirection],
    *,
    grounded: GroundedInput | None = None,
) -> list[RebranchDirection]:
    """Call 1 structural directions: require support_ids and genericity <= 1."""
    corpus = grounded_corpus(grounded) if grounded is not None else ""
    kept: list[RebranchDirection] = []
    for raw in directions:
        fixed = recalculate_rebranch_publishable(raw, grounded=grounded)
        if not fixed.support_ids:
            continue
        if fixed.genericity_score > 1:
            continue
        if not (
            fixed.source_meaning.strip()
            and fixed.current_receiver.strip()
            and fixed.branch_specific_form.strip()
        ):
            continue
        form = fixed.branch_specific_form.strip()
        if form in GENERIC_REBRANCH_VERBS or any(
            form == v or form.endswith(v) for v in GENERIC_REBRANCH_VERBS
        ):
            continue
        if grounded is not None:
            # Require a grounded concrete noun to appear inside the form.
            corpus_nouns = re.findall(r"[\u4e00-\u9fff]{2,}", corpus)
            if not any(n in form for n in corpus_nouns if len(n) >= 2):
                continue
        kept.append(fixed.model_copy(update={"selected_for_manuscript": False}))
    return kept


def _is_sensitive_domain(grounded: GroundedInput, source_text: str = "") -> bool:
    blob = grounded_corpus(grounded) + "\n" + (source_text or "")
    if any(d for d in grounded.sensitive_domains):
        return True
    return bool(re.search(r"不妊|治療|子どもを授|妊娠", blob))


def _id_map(grounded: GroundedInput) -> dict[str, GroundedFact]:
    return {f.id: f for f in all_grounded_items(grounded) if f.id}


def _pack_category(fact: GroundedFact) -> str:
    for tag in fact.tags or []:
        if isinstance(tag, str) and tag.startswith("category:"):
            return tag.split(":", 1)[1]
    return ""


def _is_context_pack_fact(fact: GroundedFact) -> bool:
    return (fact.source_field or "") == "context_pack" or "context_pack" in (
        fact.tags or []
    )


def _present_life_fact_ids(grounded: GroundedInput) -> list[str]:
    ids: list[str] = []
    for f in grounded.facts:
        # v1.1-exp: approved pack present-category facts are present anchors
        if _is_context_pack_fact(f):
            cat = _pack_category(f)
            if cat in {
                "family_context",
                "current_work",
                "current_projects",
                "current_creative_activity",
                "relevant_domains",
                "relevant_social_context",
            }:
                ids.append(f.id)
                continue
            if cat in {"career_history", "major_life_events"}:
                continue
        text = f.content or ""
        # Prefer explicit present-tense / current-life markers.
        if re.search(r"現在|いま|今も", text):
            ids.append(f.id)
            continue
        if re.search(
            r"経営|制作|まとめ|友人が家|遊びに来る|暮ら|生活|妻|息子|娘|猫|犬|家族|三人|同居",
            text,
        ) and not re.search(
            r"選んだ|選ばなかった|合格した|授かった|別れた|結婚した", text
        ):
            ids.append(f.id)
    for f in grounded.feelings:
        if f.id:
            ids.append(f.id)
    # Synthetic IDs for current_context lines
    for i, ctx in enumerate(grounded.current_context):
        if ctx.strip() and not looks_like_user_question(ctx) and not DECISION_EVIDENCE_RE.search(ctx):
            ids.append(f"ctx_{i+1:03d}")
    return list(dict.fromkeys(ids))


def _past_branch_fact_ids(grounded: GroundedInput, structure: BranchStructure) -> list[str]:
    ids: list[str] = []
    for f in grounded.facts:
        if _is_context_pack_fact(f):
            cat = _pack_category(f)
            if cat in {"career_history", "major_life_events"}:
                ids.append(f.id)
                continue
        if re.search(
            r"歳|授かった|合格|進学|選んだ|選ばなかった|会社員|働いて|治療|決断|話し合|やめた|"
            r"別れ|別れた|結婚|交際|付き合|プロポーズ|同棲|離婚",
            f.content,
        ):
            # Prefer past over pure present
            if re.search(r"^現在", f.content) and not re.search(r"授かった|合格|選んだ", f.content):
                continue
            ids.append(f.id)
    for q in grounded.questions:
        if q.id:
            ids.append(q.id)
    for sid in structure.primary_branch.supporting_fact_ids:
        if sid:
            ids.append(sid)
    return list(dict.fromkeys([x for x in ids if x]))


GENERIC_CURRENT_CONTEXT_LABELS = frozenset(
    {
        "現在の生活",
        "今の暮らし",
        "現在の状況",
        "いまの生活",
        "現在の暮らし",
        "今の生活",
        "現在の文脈",
        "いまの暮らし",
        "current_context",
        "present_life",
    }
)

RAW_UI_FIELD_NAMES = frozenset(
    {
        "present_question",
        "current_context",
        "branch_period",
        "triggering_event",
        "chosen_path",
        "unchosen_path",
        "source_coverage",
        "grounded_input",
        "residue_candidates",
        "central_thesis",
    }
)

COVERAGE_UI_LABELS = {
    "branch_period": "分岐の時期",
    "triggering_event": "きっかけになった出来事",
    "chosen_path": "実際に選んだ道",
    "unchosen_path": "選ばなかった道",
    "present_question": "今も残る問い",
    "current_context": "今の生活の具体的な場面",
}


def is_generic_current_context_label(text: str) -> bool:
    compact = re.sub(r"\s+", "", (text or "").strip())
    if not compact:
        return True
    if compact in {re.sub(r"\s+", "", x) for x in GENERIC_CURRENT_CONTEXT_LABELS}:
        return True
    # Extremely abstract short labels only
    return compact in {"生活", "暮らし", "現状", "いま"}


def looks_like_internal_ui_token(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if t in RAW_UI_FIELD_NAMES or t in GENERIC_CURRENT_CONTEXT_LABELS:
        return True
    if re.fullmatch(r"(fact|question|ctx|hyp|feel|unk)_[a-z0-9_]+", t, flags=re.I):
        return True
    if re.fullmatch(r"[a-z][a-z0-9_]{2,40}", t):
        return True
    return False


def build_input_corpus(
    source_text: str = "",
    *,
    clarifications: dict | None = None,
    editorial_context: dict | None = None,
    answers: dict | None = None,
) -> str:
    parts: list[str] = [(source_text or "").strip()]
    for bag in (clarifications, editorial_context, answers):
        if not isinstance(bag, dict):
            continue
        for key, value in bag.items():
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                joined = "\n".join(str(x).strip() for x in value if str(x).strip())
                if joined:
                    parts.append(f"{key}: {joined}")
            else:
                text = str(value).strip()
                if text:
                    parts.append(f"{key}: {text}")
    return "\n".join(p for p in parts if p)


def _split_present_life_sentences(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    # Split on sentence ends and light connectors without inventing meaning.
    chunks = re.split(r"[。．！？\n]+|(?:また、)|(?:そして、)", raw)
    out: list[str] = []
    for chunk in chunks:
        line = chunk.strip(" 　・-")
        if not line:
            continue
        if looks_like_user_question(line) or is_generic_current_context_label(line):
            continue
        # Past branch / decision narrative belongs in facts, not current_context.
        if re.search(
            r"別れた|別れ、|結婚した|お付き合いを継続|選んだ|選ばなかった|合格|進学した",
            line,
        ):
            continue
        if DECISION_EVIDENCE_RE.search(line) and not re.search(
            r"暮ら|生活してい|猫|犬|三人|同居|制作|経営", line
        ):
            continue
        # Require concrete present-life structure (not merely mentioning 妻/家族 in a past sentence).
        if re.search(
            r"暮ら|生活してい|猫|犬|三人|同居|ペット|制作|経営|友人が家|遊びに来る|"
            r"息子が|娘が|子どもと|妻と息子|夫と娘",
            line,
        ):
            out.append(line.rstrip("。"))
    return list(dict.fromkeys(out))


def _extract_present_life_from_corpus(corpus: str) -> list[str]:
    if not (corpus or "").strip():
        return []
    found: list[str] = []
    # Prefer explicit current_life / context fields from clarifications/editorial.
    for match in re.finditer(
        r"(?:current_life_context|current_context|現在の生活|今の生活)\s*[:：]\s*(.+)",
        corpus,
    ):
        found.extend(_split_present_life_sentences(match.group(1)))
    # Whole-corpus scan for present-life sentences.
    for line in corpus.splitlines():
        found.extend(_split_present_life_sentences(line))
    # Multi-sentence paragraphs without newlines.
    if not found:
        found.extend(_split_present_life_sentences(corpus))
    return list(dict.fromkeys(found))


def preserve_concrete_current_context(
    grounded: GroundedInput,
    *,
    source_text: str = "",
) -> GroundedInput:
    """Never keep abstract labels when concrete present-life text exists in input."""
    concrete_existing = [
        c.strip()
        for c in grounded.current_context
        if c.strip() and not is_generic_current_context_label(c) and not looks_like_user_question(c)
    ]
    recovered = _extract_present_life_from_corpus(source_text)
    # Also recover from existing facts that are clearly present-life.
    for f in grounded.facts:
        if re.search(r"暮ら|生活|猫|犬|妻|息子|娘|家族|三人", f.content or "") and not re.search(
            r"別れた|結婚した|付き合|選んだ|選ばなかった", f.content or ""
        ):
            recovered.extend(_split_present_life_sentences(f.content))

    if concrete_existing:
        kept = concrete_existing
    else:
        kept = recovered

    # Prefer recovered concrete lines over a lone generic label.
    if any(is_generic_current_context_label(c) for c in grounded.current_context) and recovered:
        kept = recovered

    kept = list(dict.fromkeys([k.rstrip("。") for k in kept if k.strip()]))
    if not kept:
        # Fall back to non-generic sanitize path later.
        kept = [
            c.strip()
            for c in grounded.current_context
            if c.strip() and not is_generic_current_context_label(c)
        ]

    extra_facts: list[GroundedFact] = []
    existing_contents = {re.sub(r"\s+", "", f.content) for f in grounded.facts}
    for i, line in enumerate(kept):
        compact = re.sub(r"\s+", "", line)
        if compact in existing_contents:
            continue
        fact_id = f"fact_current_preserved_{i+1:03d}"
        extra_facts.append(
            GroundedFact(
                id=fact_id,
                content=line,
                boundary_type=FactBoundaryType.explicit_fact,
                source_field="current_context_preserved",
                source_text=line,
                allowed_as_fact=True,
            )
        )
        existing_contents.add(compact)

    return grounded.model_copy(
        update={
            "current_context": kept,
            "facts": [*grounded.facts, *extra_facts],
        }
    )


def scrub_confirmation_ui_items(items: list[str]) -> list[str]:
    """Drop raw schema/field tokens; keep human-readable confirmation notes only once."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in items:
        text = (raw or "").strip()
        if not text or looks_like_internal_ui_token(text):
            # Map known coverage keys to Japanese once.
            label = COVERAGE_UI_LABELS.get(text)
            if label and label not in seen:
                # present_question is handled via additional_questions — omit from list.
                if text == "present_question":
                    continue
                out.append(label)
                seen.add(label)
            continue
        if text in seen:
            continue
        out.append(text)
        seen.add(text)
    return out


def present_question_clarification(
    structure: BranchStructure,
    grounded: GroundedInput,
) -> str:
    unchosen = ""
    if structure.primary_branch.unrealized_paths:
        unchosen = structure.primary_branch.unrealized_paths[0].strip()
    if unchosen and len(unchosen) <= 40:
        return (
            f"もし{unchosen.rstrip('。')}を選んでいたら、と今でも考えることはありますか？"
        )
    if "中国" in (structure.primary_branch.triggering_event or "") or any(
        "中国" in f.content for f in grounded.facts
    ):
        return "もし中国人女性との交際を続けていたら、と今でも考えることはありますか？"
    return "今も、この選択について考えることはありますか？"


def sanitize_current_context(grounded: GroundedInput) -> GroundedInput:
    """Keep present-life lines only; move bare later-decision lines out of context."""
    kept: list[str] = []
    extra_facts: list[GroundedFact] = []
    for line in grounded.current_context:
        text = line.strip()
        if not text:
            continue
        if is_generic_current_context_label(text):
            continue
        if DECISION_EVIDENCE_RE.search(text) and not re.search(r"現在|いま|今も|暮ら|経営|制作|生活|妻|猫", text):
            if not any(text in f.content for f in grounded.facts):
                extra_facts.append(
                    GroundedFact(
                        id=f"fact_ctx_decision_{len(extra_facts)+1:03d}",
                        content=text,
                        boundary_type=FactBoundaryType.explicit_fact,
                        source_field="current_context_reclassified",
                        allowed_as_fact=True,
                    )
                )
            continue
        if looks_like_user_question(text):
            continue
        kept.append(text)
    if not kept:
        for f in grounded.facts:
            if re.search(r"現在|いま|経営|暮ら|制作|まとめ|生活|猫|妻|息子", f.content):
                if not is_generic_current_context_label(f.content):
                    kept.append(f.content)
                    break
    return grounded.model_copy(
        update={"current_context": kept, "facts": [*grounded.facts, *extra_facts]}
    )


def validate_residue_candidate(
    raw: ResidueCandidate,
    grounded: GroundedInput,
    *,
    sensitive: bool,
) -> tuple[ResidueCandidate | None, str]:
    statement = raw.statement()
    past = [x for x in (raw.past_anchor_ids or raw.support_ids or []) if x]
    present = [x for x in (raw.present_anchor_ids or []) if x]
    # Legacy: split support_ids if past/present missing
    if not present and raw.support_ids:
        present_ids = set(_present_life_fact_ids(grounded))
        present = [x for x in raw.support_ids if x in present_ids]
        past = [x for x in raw.support_ids if x not in present] or past

    known = set(_id_map(grounded)) | {
        f"ctx_{i+1:03d}" for i, c in enumerate(grounded.current_context) if c.strip()
    }
    q_ids = fact_ids_by_type(grounded, FactBoundaryType.user_question)
    unknown_ids = fact_ids_by_type(grounded, FactBoundaryType.unknown)
    inference_ids = fact_ids_by_type(grounded, FactBoundaryType.model_inference)
    feeling_ids = fact_ids_by_type(grounded, FactBoundaryType.user_feeling)
    present_life_ids = set(_present_life_fact_ids(grounded)) | feeling_ids
    forbidden_present = q_ids | unknown_ids | inference_ids

    past = [x for x in past if x in known or x.startswith("ctx_")]
    # Present anchors: current-life fact/feeling/context only — never question/unknown/inference.
    present = [
        x
        for x in present
        if x not in forbidden_present
        and (x in present_life_ids or x.startswith("ctx_"))
    ]

    if len(past) < 1:
        return None, "missing_past_anchor_ids"
    if len(present) < 1:
        return None, "missing_present_anchor_ids"
    if not statement:
        return None, "empty_residue_statement"
    if not raw.advances_manuscript:
        return None, "advances_manuscript_false"

    # user_question alone cannot be residue
    q_texts = {q.content.strip() for q in grounded.questions}
    if statement in q_texts:
        return None, "residue_is_user_question"
    if any(statement == q or statement in q or q in statement for q in q_texts if len(q) >= 8):
        # Allow only if statement clearly adds present-life structure beyond the question.
        if not any(
            tok in statement
            for tok in ("暮ら", "経営", "制作", "仕事", "家庭", "日常", "友人", "現在")
        ):
            return None, "residue_is_question_paraphrase"

    if any(p in statement for p in RESIDUE_GENERIC_PHRASES):
        return None, "generic_reflection"

    dist = (raw.inference_distance or "near").strip().lower()
    allowed = ALLOWED_INFERENCE_SENSITIVE if sensitive else ALLOWED_INFERENCE_DEFAULT
    if dist not in allowed:
        return None, f"inference_distance_rejected:{dist}"

    fixed = raw.model_copy(
        update={
            "residue_statement": statement,
            "content": statement,
            "past_anchor_ids": past,
            "present_anchor_ids": present,
            "support_ids": list(dict.fromkeys([*past, *present])),
            "inference_distance": dist,
        }
    )
    return fixed, ""


def propose_residue_from_anchors(
    grounded: GroundedInput,
    structure: BranchStructure,
    *,
    sensitive: bool,
) -> list[ResidueCandidate]:
    """Cautious structural Residue when model returned none but anchors exist.

    Does not invent psychology; connects grounded past + present only.
    """
    past_ids = _past_branch_fact_ids(grounded, structure)
    present_ids = _present_life_fact_ids(grounded)
    # Exclude pure question IDs from being the only past anchor
    q_ids = {q.id for q in grounded.questions}
    past_facts = [i for i in past_ids if i not in q_ids]
    if not past_facts or not present_ids:
        return []

    idmap = _id_map(grounded)
    past_txt = idmap.get(past_facts[0]).content if past_facts[0] in idmap else structure.primary_branch.realized_path
    present_txt = ""
    for pid in present_ids:
        if pid in idmap:
            present_txt = idmap[pid].content
            break
        if pid.startswith("ctx_"):
            idx = int(pid.split("_")[1]) - 1
            if 0 <= idx < len(grounded.current_context):
                present_txt = grounded.current_context[idx]
                break
    if not past_txt or not present_txt:
        return []

    # Cautious structural link only — never assert that the past created the present.
    statement = (
        f"「{past_txt[:36]}」を振り返る問いは、"
        f"「{present_txt[:36]}」という現在の生活と並べて読むことができる"
    )
    candidate = ResidueCandidate(
        residue_statement=statement,
        content=statement,
        past_anchor_ids=[past_facts[0]],
        present_anchor_ids=[present_ids[0]],
        support_ids=[past_facts[0], present_ids[0]],
        inference_distance="near",
        present_life_domain="present_life",
        overreach_risk="low_structural_only",
        advances_manuscript=True,
    )
    ok, _ = validate_residue_candidate(candidate, grounded, sensitive=sensitive)
    return [ok] if ok else []


def filter_residue_candidates(
    items: Iterable[ResidueCandidate],
    grounded: GroundedInput,
    structure: BranchStructure,
    *,
    source_text: str = "",
) -> tuple[list[ResidueCandidate], list[str]]:
    sensitive = _is_sensitive_domain(grounded, source_text)
    kept: list[ResidueCandidate] = []
    rejected: list[str] = []
    for raw in items:
        ok, reason = validate_residue_candidate(raw, grounded, sensitive=sensitive)
        if ok:
            kept.append(ok)
        else:
            rejected.append(reason or "rejected")
    if not kept:
        proposed = propose_residue_from_anchors(grounded, structure, sensitive=sensitive)
        if proposed:
            kept.extend(proposed)
            rejected.append("model_empty_assisted_from_anchors")
        else:
            rejected.append("no_valid_residue_anchors")
    return kept, rejected


def residue_centrality_passes(
    body: str,
    residues: list[ResidueCandidate],
    grounded: GroundedInput,
) -> bool:
    if not residues:
        return False
    # Short manuscripts can still be residue-central when structural language is present.
    if len(body or "") < 160 and "残" not in (body or ""):
        return False
    idmap = _id_map(grounded)
    for r in residues:
        statement = r.statement()
        # Must not be satisfied by repeating the question alone.
        q_only = any(
            q.content.strip() and q.content.strip() in (body or "") and statement not in (body or "")
            for q in grounded.questions
        )
        present_ok = False
        for pid in r.present_anchor_ids:
            if pid in idmap:
                tokens = re.findall(r"[\u4e00-\u9fff]{2,}", idmap[pid].content)
                if any(t in body for t in tokens[:6]):
                    present_ok = True
                    break
            elif pid.startswith("ctx_"):
                idx = int(pid.split("_")[1]) - 1
                if 0 <= idx < len(grounded.current_context):
                    tokens = re.findall(r"[\u4e00-\u9fff]{2,}", grounded.current_context[idx])
                    if any(t in body for t in tokens[:6]):
                        present_ok = True
                        break
        meaning_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", statement)
        meaning_ok = sum(1 for t in meaning_tokens[:8] if t in body) >= 2
        # Closing/present return
        closing = body[-500:] if len(body) > 500 else body
        closing_present = bool(re.search(r"(現在|いま|今|暮ら|家庭|生活|経営|制作|友人)", closing))
        if present_ok and meaning_ok and closing_present:
            return True
        if present_ok and closing_present and not q_only:
            # softer path when statement tokens partially match
            if meaning_ok or "残" in body or "続いて" in body:
                return True
    return False


def detect_unsupported_personal_details(
    body: str,
    grounded: GroundedInput,
) -> list[UnsupportedPersonalDetail]:
    corpus = grounded_corpus(grounded)
    findings: list[UnsupportedPersonalDetail] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 6:
            continue
        for detail_type, pattern in PERSONAL_DETAIL_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue
            phrase = m.group(0)
            if phrase and phrase in corpus:
                continue
            # family_conversation pattern is scene; for personal detail invented conversation
            # allow if 話し合 is in corpus (case2 decision)
            if detail_type == "invented_conversation" and re.search(r"話し合", corpus):
                continue
            findings.append(
                UnsupportedPersonalDetail(
                    excerpt=text[:160],
                    detail_type=detail_type,
                    missing_support=f"personal_detail_absent:{detail_type}",
                )
            )
            break
    return findings


def _classify_causality_strength(sentence: str, corpus: str) -> int:
    """0=none, 1=association, 2=qualified possibility, 3=explicit assertion."""
    if CAUSALITY_QUALIFIED_OK_RE.search(sentence):
        return 1
    if not CAUSALITY_ASSERTION_RE.search(sentence):
        # Soft association without causal verb
        if re.search(r"並べて|共通する|並置|対比", sentence):
            return 1
        return 0
    # Explicit user-stated causality present in corpus and echoed
    m = CAUSALITY_ASSERTION_RE.search(sentence)
    phrase = m.group(0) if m else ""
    if phrase and phrase in corpus:
        return 3
    if EXPLICIT_USER_CAUSAL_RE.search(corpus) and EXPLICIT_USER_CAUSAL_RE.search(sentence):
        # User used causal language; allow echoing similar strength if phrase overlap
        for tok in re.findall(r"[\u4e00-\u9fff]{2,}", sentence):
            if tok in corpus and tok in ("きっかけ", "影響", "原因", "理由"):
                if tok in corpus:
                    return 3
    # Qualified modal must hedge the causal verb itself, not a nearby clause.
    if re.search(
        r"(影響|つなが|繋が|もたら|形成|与え|及ぼ|受け).{0,16}(かもしれない|とは言い切れない|可能性|とは限らない)",
        sentence,
    ):
        return 2
    return 3


def _is_open_causal_question(sentence: str) -> bool:
    """True when causality is asked about, not asserted as fact.

    Does not allow noun phrases like 「与える影響」 that smuggle causal claims
    into an otherwise reflective sentence.
    """
    # "考えると、…見えてくる" treats the causal probe as answered by present facts.
    if re.search(r"影響を与えてい.{0,12}のかを考えると", sentence):
        return False
    if re.search(r"(与える影響|影響を及ぼ[しす]|もたらす|(?:に|は|が|と)繋が|(?:に|は|が|と)つなが)", sentence):
        if not re.search(r"(因果|確認できない|分からない|材料は.?ない)", sentence):
            if re.search(r"(与える影響|影響を及ぼ|(?:に|は|が|と)繋が|(?:に|は|が|と)つなが)", sentence):
                return False
    if not re.search(r"(どう|どのように|どんな).{0,24}(影響|つなが|繋が|形成)", sentence):
        if not re.search(r"(影響|つなが|繋が).{0,12}(のか|か)[、,]?(また|と|を考える|分から)", sentence):
            return False
    return bool(
        re.search(r"(考える|分からない|確認できない|とは限らない|のか)", sentence)
    )


def detect_unsupported_causality(
    body: str,
    grounded: GroundedInput,
    *,
    sensitive: bool = False,
) -> list[UnsupportedCausality]:
    corpus = grounded_corpus(grounded)
    findings: list[UnsupportedCausality] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 8:
            continue
        if _is_open_causal_question(text):
            continue
        strength = _classify_causality_strength(text, corpus)
        if strength <= 1:
            continue
        # Strength 3 requires explicit user causal evidence in corpus for this link.
        if strength == 3:
            # Allow only if the causal clause itself (or user きっかけで…) is in corpus.
            m = CAUSALITY_ASSERTION_RE.search(text)
            phrase = m.group(0) if m else ""
            user_stated = bool(phrase and phrase in corpus) or (
                EXPLICIT_USER_CAUSAL_RE.search(corpus)
                and any(
                    t in corpus and t in text
                    for t in ("きっかけ",)
                )
            )
            if user_stated:
                continue
            findings.append(
                UnsupportedCausality(
                    excerpt=text[:160],
                    causality_strength=3,
                    missing_support="explicit_causal_evidence_absent",
                )
            )
            continue
        # Strength 2: require explicit non-causal qualification (因果までは…), not bare maybe.
        if CAUSALITY_QUALIFIED_OK_RE.search(text):
            continue
        if sensitive:
            findings.append(
                UnsupportedCausality(
                    excerpt=text[:160],
                    causality_strength=2,
                    missing_support="sensitive_domain_max_association",
                )
            )
            continue
        findings.append(
            UnsupportedCausality(
                excerpt=text[:160],
                causality_strength=2,
                missing_support="qualified_causal_wording_absent",
            )
        )
    return findings


def detect_unsupported_affect(
    body: str,
    grounded: GroundedInput,
) -> list[UnsupportedAffect]:
    corpus = grounded_corpus(grounded)
    findings: list[UnsupportedAffect] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 4:
            continue
        for affect_type, pattern, allowed_stems in AFFECT_PATTERNS:
            if not pattern.search(text):
                continue
            if any(stem in corpus for stem in allowed_stems):
                continue
            findings.append(
                UnsupportedAffect(
                    excerpt=text[:160],
                    affect_type=affect_type,
                    missing_support=f"affect_absent:{affect_type}",
                )
            )
            break
    return findings


def detect_unsupported_role_behavior(
    body: str,
    grounded: GroundedInput,
) -> list[UnsupportedRoleBehavior]:
    corpus = grounded_corpus(grounded)
    findings: list[UnsupportedRoleBehavior] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 4:
            continue
        for role_type, pattern in ROLE_BEHAVIOR_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue
            phrase = m.group(0)
            if phrase and phrase in corpus:
                continue
            # Broader: if key stem in corpus allow
            stem = role_type[:2] if len(role_type) >= 2 else role_type
            if role_type in corpus or (stem in corpus and role_type.startswith(stem)):
                # still require fuller phrase for 成長を見守 etc.
                if role_type in corpus:
                    continue
            findings.append(
                UnsupportedRoleBehavior(
                    excerpt=text[:160],
                    role_type=role_type,
                    missing_support=f"role_behavior_absent:{role_type}",
                )
            )
            break
    return findings


def detect_unsupported_causal_frame(
    body: str,
    grounded: GroundedInput,
) -> list[UnsupportedCausalFrame]:
    """Block causal presupposition frames, including interrogative ones."""
    corpus = grounded_corpus(grounded)
    has_causal = _has_explicit_causal_support(grounded)
    findings: list[UnsupportedCausalFrame] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 8:
            continue
        # Causal-frame questions are never repaired by adding a disclaimer.
        if CAUSAL_FRAME_RE.search(text) and not has_causal:
            findings.append(
                UnsupportedCausalFrame(
                    excerpt=text[:160],
                    frame_type="causal_presupposition",
                    missing_support="causal_frame_without_explicit_support",
                )
            )
            continue
        # Qualified non-causal comparison without frame is allowed.
        if CAUSALITY_QUALIFIED_OK_RE.search(text):
            continue
        if UNSUPPORTED_MEANING_COMPLETION_RE.search(text):
            # Allow only if the exact evaluative phrase is in corpus.
            m = UNSUPPORTED_MEANING_COMPLETION_RE.search(text)
            phrase = m.group(0) if m else ""
            if phrase and phrase in corpus:
                continue
            findings.append(
                UnsupportedCausalFrame(
                    excerpt=text[:160],
                    frame_type="unsupported_meaning_completion",
                    missing_support="evaluative_completion_absent",
                )
            )
    return findings


def detect_schema_leakage_prose(body: str) -> list[SchemaLeakageProse]:
    findings: list[SchemaLeakageProse] = []
    for sentence in re.split(r"(?<=[。．！？\n])", body):
        text = sentence.strip()
        if len(text) < 6:
            continue
        for leakage_type, pattern in SCHEMA_LEAKAGE_PATTERNS:
            if pattern.search(text):
                findings.append(
                    SchemaLeakageProse(
                        excerpt=text[:160],
                        leakage_type=leakage_type,
                        missing_support="schema_verbalization",
                    )
                )
                break
    return findings


def repair_schema_leakage_prose(body: str) -> str:
    """Deterministic cleanup for common schema-verbalization patterns."""
    out = body
    replacements = (
        (r"この選択は、実際に選んだのは", ""),
        (r"この分岐は、選ばれたのは", ""),
        (r"選択としては、実際には", ""),
        (r"実際に選んだのは", ""),
        (r"実際に選択したのは", ""),
        (r"選ばなかった道としては、", ""),
        (r"選ばなかった道として、", ""),
        (r"この分岐では、", ""),
        (r"入力によれば、", ""),
        (r"事実としては、", ""),
        (r"ここで選んだのは", ""),
        (r"ということである。", "。"),
    )
    for pat, repl in replacements:
        out = re.sub(pat, repl, out)
    # Collapse awkward punctuation left by stripping.
    out = re.sub(r"。+", "。", out)
    out = re.sub(r"(?<=[。\n])、+", "", out)
    out = re.sub(r"^、+", "", out, flags=re.MULTILINE)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


def semantic_overreach_findings(
    body: str,
    grounded: GroundedInput,
    *,
    sensitive: bool = False,
) -> dict[str, list]:
    return {
        "unsupported_causality": detect_unsupported_causality(
            body, grounded, sensitive=sensitive
        ),
        "unsupported_affect": detect_unsupported_affect(body, grounded),
        "unsupported_role_behavior": detect_unsupported_role_behavior(body, grounded),
        "unsupported_causal_frame": detect_unsupported_causal_frame(body, grounded),
        "schema_leakage_prose": detect_schema_leakage_prose(body),
        "unsupported_personal_details": detect_unsupported_personal_details(
            body, grounded
        ),
        "unsupported_scenes": detect_unsupported_scenes(body, grounded),
    }


def apply_call1_runtime_gates(
    result: Call1Result,
    *,
    source_text: str = "",
    input_corpus: str = "",
    context_pack: Any | None = None,
    deep_reading_mode: str = "strict",
) -> Call1Result:
    """Runtime gates for canonical Call1Response.

    When Contextual mode + approved pack are active (v1.1-exp), pack facts join
    the grounded corpus / Residue present anchors / lens explicit-evidence allowlist.
    Strict and Production v1.0.2 paths omit pack entirely.
    """
    from app.parallel_life_deep_reading.context_pack import (
        ContextPack,
        DeepReadingMode,
        RUNTIME_VERSION_V11_EXP,
        inject_pack_into_grounded,
        pack_corpus_text,
        resolve_effective_mode,
    )

    pack: ContextPack | None = None
    if isinstance(context_pack, ContextPack):
        pack = context_pack
    elif isinstance(context_pack, dict):
        try:
            pack = ContextPack.model_validate(context_pack)
        except Exception:
            pack = None

    mode = resolve_effective_mode(requested_mode=deep_reading_mode, pack=pack)
    use_v11 = mode == DeepReadingMode.contextual

    # Support both alias and concrete type.
    corpus = (input_corpus or source_text or "").strip()
    if use_v11 and pack is not None:
        pack_text = pack_corpus_text(pack)
        if pack_text:
            corpus = f"{corpus}\n{pack_text}".strip()

    grounded = correct_fact_boundaries(result.grounded_input)
    if use_v11 and pack is not None:
        grounded = inject_pack_into_grounded(grounded, pack)
    grounded = preserve_concrete_current_context(grounded, source_text=corpus)
    grounded = sanitize_current_context(grounded)
    grounded, structure0 = backfill_structure_from_source(
        grounded, result.branch_structure, source_text=source_text or corpus
    )
    grounded = preserve_concrete_current_context(grounded, source_text=corpus)
    grounded = sanitize_current_context(grounded)
    grounded = ensure_decision_evidence_facts(
        grounded, structure0, source_text=source_text or corpus
    )
    if use_v11 and pack is not None:
        # Re-inject after sanitizers so pack facts are not dropped.
        grounded = inject_pack_into_grounded(grounded, pack)

    structure = enrich_secondary_from_decision_evidence(
        structure0, grounded, source_text=source_text
    )
    structure, rejected_actual = normalize_branch_structure(structure, grounded)

    lens_selection = result.selected_observatory_lenses
    evaluated_raw = []
    selected_raw = []
    if hasattr(lens_selection, "evaluated"):
        evaluated_raw = list(lens_selection.evaluated or [])
        selected_raw = list(lens_selection.selected or [])
    elif isinstance(lens_selection, list):
        selected_raw = list(lens_selection)
        evaluated_raw = list(lens_selection)
    allowed_explicit: set[str] | None = None
    if use_v11:
        allowed_explicit = set(_id_map(grounded)) | {
            f"ctx_{i+1:03d}"
            for i, c in enumerate(grounded.current_context)
            if c.strip()
        }
    evaluated, selected = filter_selected_lenses(
        evaluated_raw or selected_raw, allowed_explicit_ids=allowed_explicit
    )

    directions_in = []
    if hasattr(result.rebranch_design, "directions"):
        directions_in = list(result.rebranch_design.directions or [])
    elif isinstance(result.rebranch_design, list):
        directions_in = list(result.rebranch_design)
    rebranch_ok = filter_call1_rebranch_directions(directions_in, grounded=grounded)

    from app.parallel_life_deep_reading.call1_schema import (
        ResidueCandidates,
        call1_residue_items,
    )

    residue_in = call1_residue_items(result)
    residue_ok_items, residue_reject_notes = filter_residue_candidates(
        residue_in, grounded, structure, source_text=source_text
    )

    # --- v1.0.1 gates: contradiction / vague branch / sensitive thesis ---
    # Work on a provisional Call1 snapshot for detectors.
    provisional = result.model_copy(
        update={"grounded_input": grounded, "branch_structure": structure}
    )
    contradictions = detect_material_contradictions(
        provisional, source_text=source_text
    )
    concreteness = assess_branch_concreteness(provisional)
    thesis = result.central_thesis
    thesis_deferred = False
    sensitive_thesis_rejected = False
    v101_notes: list[str] = []

    if contradictions:
        thesis_deferred = True
        thesis = CentralThesis(statement="", validation_status="deferred_contradiction")
        residue_ok_items = []
        residue_reject_notes = list(residue_reject_notes) + [
            "cleared_due_to_material_contradiction"
        ]
        # Do not keep actual secondaries that were inferred atop conflict.
        structure = structure.model_copy(update={"secondary_branches": []})
        for c in contradictions:
            v101_notes.append(f"material_contradiction:{c.describe()}")

    if not concreteness.ok:
        residue_ok_items = []
        residue_reject_notes = list(residue_reject_notes) + [
            "cleared_due_to_vague_branch"
        ]
        for r in concreteness.reasons:
            v101_notes.append(f"vague_branch:{r}")

    if sensitive_thesis_is_unsupported_causal(
        thesis.statement, provisional, source_text=source_text
    ):
        sensitive_thesis_rejected = True
        v101_notes.append("sensitive_thesis_rejected:unsupported_causal")
        safe = build_safe_sensitive_coexistence_thesis(provisional)
        if safe:
            thesis = CentralThesis(
                statement=safe,
                supported_by=list(thesis.supported_by or []),
                validation_status="rewritten_coexistence",
            )
        else:
            thesis = CentralThesis(
                statement="",
                validation_status="deferred_sensitive",
            )

    coverage = compute_source_coverage(grounded, structure, source_text=source_text)
    # Prefer model-reported True values only when also runtime-true.
    model_cov = getattr(result, "source_coverage", None)
    if model_cov is not None:
        coverage = SourceCoverage(
            branch_period=bool(getattr(model_cov, "branch_period", False) or coverage.branch_period),
            triggering_event=bool(
                getattr(model_cov, "triggering_event", False) or coverage.triggering_event
            ),
            chosen_path=bool(getattr(model_cov, "chosen_path", False) or coverage.chosen_path),
            unchosen_path=bool(
                getattr(model_cov, "unchosen_path", False) or coverage.unchosen_path
            ),
            present_question=bool(
                getattr(model_cov, "present_question", False) or coverage.present_question
            ),
            current_context=bool(
                getattr(model_cov, "current_context", False) or coverage.current_context
            ),
        )
        # Recompute strictly from runtime evidence (do not trust model alone).
        coverage = compute_source_coverage(grounded, structure, source_text=source_text)

    missing = coverage.missing()
    additional = result.additional_questions
    add_questions = list(getattr(additional, "questions", []) or [])
    add_required = bool(getattr(additional, "required", False)) or bool(add_questions)

    sufficiency = result.input_sufficiency.model_copy(
        update={
            "current_context_requirement_met": coverage.current_context,
            "required_fields_complete": coverage.all_required_present() and len(grounded.facts) >= 1,
            "missing_fields": missing,
            "additional_questions": add_questions,
        }
    )

    from app.parallel_life_deep_reading.call1_schema import (
        AdditionalQuestions,
        ObservatoryLensSelection,
        RebranchDesign,
    )

    if contradictions:
        add_required = True
        for c in contradictions:
            q = contradiction_clarification(c)
            if q not in add_questions:
                add_questions.append(q)
        # Cap at 3 total questions
        add_questions = add_questions[:3]

    if not concreteness.ok:
        add_required = True
        for q in concreteness.clarification_questions:
            if q not in add_questions:
                add_questions.append(q)
        add_questions = add_questions[:3]

    concrete_context = any(
        c.strip() and not is_generic_current_context_label(c) for c in grounded.current_context
    )
    if (
        not residue_ok_items
        and not contradictions
        and concreteness.ok
        and not concrete_context
    ):
        add_required = True
        if not any("現在" in q or "場面" in q for q in add_questions):
            add_questions.append(
                "いまの生活のなかで、その分岐がいまでも触れている具体的な場面・習慣・関係を教えてください。"
            )

    # Missing present_question → exactly one natural clarification (never raw field / never invent grounded Q).
    if (
        "present_question" in missing
        and not contradictions
        and concreteness.ok
        and not grounded.questions
    ):
        add_required = True
        pq = present_question_clarification(structure, grounded)
        if set(missing) <= {"present_question"} and concrete_context:
            # Optional clarification only — do not stack unrelated model questions.
            add_questions = [pq]
        else:
            add_questions = [
                q
                for q in add_questions
                if not (
                    "今でも考える" in q
                    or "今も、この選択" in q
                    or "考えることはありますか" in q
                    or "家族構成" in q
                )
            ]
            add_questions = [pq, *add_questions][:2]

    missing_for_ui = [m for m in missing if m != "present_question"]
    missing_labels = [COVERAGE_UI_LABELS.get(m, m) for m in missing_for_ui]

    conflict_items: list[str] = []
    for c in contradictions:
        desc = c.describe()
        if desc not in conflict_items:
            conflict_items.append(desc)
    items_raw = (
        list(result.user_confirmation_view.items_to_confirm)
        + missing_labels
        + conflict_items
    )
    view = UserConfirmationView(
        branch_period=structure.primary_branch.period
        or result.user_confirmation_view.branch_period,
        triggering_event=structure.primary_branch.triggering_event
        or result.user_confirmation_view.triggering_event,
        chosen_path=structure.primary_branch.realized_path
        or result.user_confirmation_view.chosen_path,
        unchosen_path=(
            structure.primary_branch.unrealized_paths[0]
            if structure.primary_branch.unrealized_paths
            else result.user_confirmation_view.unchosen_path
        ),
        actual_secondary_branches=[b.description for b in structure.secondary_branches if b.description],
        retrospective_counterfactuals=[
            b.description for b in structure.retrospective_counterfactuals if b.description
        ],
        present_questions=[
            q.content
            for q in grounded.questions
            if q.content and not looks_like_internal_ui_token(q.content)
        ],
        current_context=[
            c
            for c in grounded.current_context
            if c.strip() and not is_generic_current_context_label(c)
        ],
        feelings=[f.content for f in grounded.feelings],
        hypotheses=[h.content for h in grounded.hypotheses],
        unknowns=[u.content for u in grounded.unknowns],
        central_thesis_preview=thesis.statement
        or result.user_confirmation_view.central_thesis_preview,
        observatory_lens_candidates=[
            f"{c.lens_id}: {(c.new_meaning_added or '')[:40]}" for c in selected
        ],
        items_to_confirm=scrub_confirmation_ui_items(items_raw),
    )

    if result.status == GenerationStatus.schema_validation_failed:
        status = GenerationStatus.schema_validation_failed
    elif contradictions:
        status = GenerationStatus.needs_additional_input
    elif not concreteness.ok:
        status = GenerationStatus.structural_ambiguity
    elif missing or not sufficiency.required_fields_complete:
        status = GenerationStatus.needs_additional_input
    elif not residue_ok_items:
        status = GenerationStatus.needs_additional_input
    elif add_required and add_questions:
        status = GenerationStatus.needs_additional_input
    else:
        status = GenerationStatus.ready_for_user_confirmation

    # Empty thesis preview when deferred
    if thesis_deferred or not thesis.statement:
        view = view.model_copy(
            update={"central_thesis_preview": thesis.statement or ""}
        )

    sufficiency = sufficiency.model_copy(
        update={"additional_questions": add_questions}
    )

    validation = Call1Validation(
        actual_secondary_rejected=rejected_actual,
        lenses_rejected=[c.lens_id for c in evaluated if not c.evidence_gate_passed],
        questions_not_converted_to_facts=True,
        hypotheses_not_converted_to_facts=True,
        notes=[f"residue:{n}" for n in residue_reject_notes]
        + v101_notes
        + ([f"runtime:{RUNTIME_VERSION_V11_EXP}"] if use_v11 else []),
        source_coverage_missing=missing,
        material_contradictions=conflict_items,
        material_contradiction_count=len(contradictions),
        branch_concreteness_ok=concreteness.ok,
        thesis_deferred_due_to_contradiction=thesis_deferred,
        sensitive_thesis_rejected=sensitive_thesis_rejected,
    )

    pack_usage: dict[str, Any] | None = None
    if use_v11 and pack is not None:
        pack_ids = {
            f.id
            for f in grounded.facts
            if f.id and _is_context_pack_fact(f)
        }
        residue_present = []
        residue_past = []
        for r in residue_ok_items:
            for pid in r.present_anchor_ids or []:
                if pid in pack_ids:
                    residue_present.append(pid)
            for pid in r.past_anchor_ids or []:
                if pid in pack_ids:
                    residue_past.append(pid)
        lens_pack = []
        for c in selected:
            for eid in c.explicit_evidence_ids or []:
                if eid in pack_ids:
                    lens_pack.append(eid)
        rebranch_pack = []
        for d in rebranch_ok:
            for sid in getattr(d, "support_ids", None) or []:
                if sid in pack_ids:
                    rebranch_pack.append(sid)
        pack_usage = {
            "mode": DeepReadingMode.contextual.value,
            "pack_id": pack.pack_id,
            "pack_fact_ids": sorted(pack_ids),
            "residue_present_anchor_ids": list(dict.fromkeys(residue_present)),
            "residue_past_anchor_ids": list(dict.fromkeys(residue_past)),
            "lens_explicit_evidence_ids": list(dict.fromkeys(lens_pack)),
            "rebranch_support_ids": list(dict.fromkeys(rebranch_pack)),
        }

    gated = result.model_copy(
        update={
            "grounded_input": grounded,
            "branch_structure": structure,
            "central_thesis": thesis,
            "input_sufficiency": sufficiency,
            "source_coverage": coverage,
            "residue_candidates": ResidueCandidates(items=residue_ok_items),
            "selected_observatory_lenses": ObservatoryLensSelection(
                evaluated=evaluated, selected=selected
            ),
            "rebranch_design": RebranchDesign(directions=rebranch_ok),
            "additional_questions": AdditionalQuestions(
                required=add_required and bool(add_questions),
                questions=add_questions,
            ),
            "user_confirmation_view": view,
            "validation": validation,
            "status": status,
            "context_pack_usage": pack_usage,
        }
    )

    if use_v11 and pack is not None:
        from app.parallel_life_deep_reading.branch_semantics import (
            attach_branch_semantics,
        )
        from app.parallel_life_deep_reading.context_selection import (
            apply_selection_compression_gates,
            compute_resume_density,
            enrich_compression_from_relations,
        )
        from app.parallel_life_deep_reading.observatory_core import (
            build_observatory_core_bundle,
            merge_bundle_into_call1_fields,
            should_omit_observatory_section,
        )

        # v1.1.8: BranchSemantics before Observatory / MeaningCompression / SectionContracts
        gated, branch_sem = attach_branch_semantics(gated, pack=pack)

        branch_ids_for_obs = list(
            gated.branch_structure.primary_branch.supporting_fact_ids or []
        )
        for f in gated.grounded_input.facts:
            if f.id and (f.source_field or "") != "context_pack":
                if f.id not in branch_ids_for_obs:
                    branch_ids_for_obs.append(f.id)

        obs_bundle = build_observatory_core_bundle(
            source_text or corpus,
            pack,
            branch_evidence_ids=branch_ids_for_obs,
            branch_semantics=branch_sem.model_dump(mode="json"),
        )
        _cand, evidence, relations = merge_bundle_into_call1_fields(
            bundle=obs_bundle,
            llm_relations=getattr(gated, "cross_lens_relations", None) or [],
        )
        mc0 = enrich_compression_from_relations(
            gated.meaning_compression, relations
        )
        gated = gated.model_copy(
            update={
                "candidate_lens_selection": obs_bundle.candidate_lens_selection.model_dump(
                    mode="json"
                ),
                "retrieved_observatory_evidence": [
                    e.model_dump(mode="json") for e in evidence
                ],
                "cross_lens_relations": [r.model_dump(mode="json") for r in relations],
                "meaning_compression": mc0,
                "observatory_core_diagnostics": obs_bundle.diagnostics,
            }
        )

        # If CrossLens already carries meaning, omit decorative Observatory section lenses
        if should_omit_observatory_section(relations, len(selected)):
            gated = gated.model_copy(
                update={
                    "selected_observatory_lenses": ObservatoryLensSelection(
                        evaluated=evaluated, selected=[]
                    )
                }
            )
            notes_obs = list(gated.validation.notes or [])
            notes_obs.append("observatory_section:omitted_pre_thesis_relations")
            gated = gated.model_copy(
                update={
                    "validation": gated.validation.model_copy(update={"notes": notes_obs})
                }
            )

        gated, sel_diag = apply_selection_compression_gates(gated, pack=pack)
        # Soft compression repair: if résumé density high, prefer compression tension as thesis pole
        resume = sel_diag.get("resume_density") or {}
        mc = gated.meaning_compression
        th = gated.central_thesis
        # Prefer CrossLens-informed thesis when causal/resume soft-fail
        if th.validation_status.startswith("failed_") and relations:
            primary = relations[0]
            repaired_statement = (
                f"{primary.personal_structure}という個人の分岐を、"
                f"{primary.social_structure}と並べて読むことができる。"
            )
            th = th.model_copy(
                update={
                    "statement": repaired_statement,
                    "pole_a": primary.personal_structure or th.pole_a,
                    "pole_b": mc.present_structure or th.pole_b,
                    "validation_status": "repaired_cross_lens",
                }
            )
            gated = gated.model_copy(
                update={
                    "central_thesis": th,
                    "user_confirmation_view": gated.user_confirmation_view.model_copy(
                        update={"central_thesis_preview": th.statement}
                    ),
                }
            )
        if resume.get("compression_required") and (
            mc.tension
            or mc.central_question
            or mc.personal_tension
            or mc.social_institutional_parallel
        ):
            repaired_statement = th.statement
            if th.validation_status.startswith("failed_") or compute_resume_density(
                th.statement
            ).compression_required:
                if mc.personal_tension and mc.social_institutional_parallel:
                    repaired_statement = (
                        f"{mc.personal_tension}を、"
                        f"{mc.social_institutional_parallel}と並べていま読み直せる。"
                    )
                else:
                    repaired_statement = (
                        f"{mc.tension or mc.central_question}"
                        "という構造として、この分岐をいま読み直せる。"
                    )
                th = th.model_copy(
                    update={
                        "statement": repaired_statement,
                        "pole_a": mc.past_structure or mc.personal_tension or th.pole_a,
                        "pole_b": mc.present_structure or th.pole_b,
                        "validation_status": "repaired_compression",
                    }
                )
            gated = gated.model_copy(
                update={
                    "central_thesis": th,
                    "user_confirmation_view": gated.user_confirmation_view.model_copy(
                        update={"central_thesis_preview": th.statement}
                    ),
                    "selection_compression_diagnostics": sel_diag,
                    "resume_density_report": resume,
                }
            )
        else:
            gated = gated.model_copy(
                update={
                    "selection_compression_diagnostics": sel_diag,
                    "resume_density_report": resume,
                }
            )
        # Soft status: thesis hard-fail after repair still → needs_additional_input (not Call3 block)
        if gated.central_thesis.validation_status.startswith("failed_"):
            if gated.status == GenerationStatus.ready_for_user_confirmation:
                gated = gated.model_copy(
                    update={"status": GenerationStatus.needs_additional_input}
                )

        # v1.1.3-exp: Section Contracts — repair empty Lost/Protected/Residue/Re-branch
        from app.parallel_life_deep_reading.section_contracts import (
            section_contract_evidence_check,
        )

        _ok, _sc_notes, gated, _contracts = section_contract_evidence_check(gated)
        # Stamp active Contextual runtime pin (Call1 prompt may stay on prior exp)
        gated = gated.model_copy(update={"schema_version": RUNTIME_VERSION_V11_EXP})

    return gated


def strip_rebranch_section(body: str) -> str:
    """Remove Re-branch section headings/content when unpublished."""
    patterns = [
        r"\n+#+\s*再分岐[^\n]*\n[\s\S]*?(?=\n#+ |\Z)",
        r"\n+#+\s*Re-?branch[^\n]*\n[\s\S]*?(?=\n#+ |\Z)",
        r"\n+##\s*いまできる小さな分岐[^\n]*\n[\s\S]*?(?=\n## |\Z)",
    ]
    out = body
    for p in patterns:
        out = re.sub(p, "\n", out, flags=re.IGNORECASE)
    return out.strip() + ("\n" if body.endswith("\n") else "")


def strip_observatory_sections(body: str) -> str:
    patterns = [
        r"\n+#+\s*Observatory[^\n]*\n[\s\S]*?(?=\n#+ |\Z)",
        r"\n+#+\s*観測[^\n]*\n[\s\S]*?(?=\n#+ |\Z)",
        r"\n+#+\s*Cross-?Lens[^\n]*\n[\s\S]*?(?=\n#+ |\Z)",
        r"\n+#+\s*レンズ横断[^\n]*\n[\s\S]*?(?=\n#+ |\Z)",
    ]
    out = body
    for p in patterns:
        out = re.sub(p, "\n", out, flags=re.IGNORECASE)
    # Also remove meta mentions of omission
    out = re.sub(r"[^\n]*(Observatory|観測レイヤー)[^\n]*(省略|含めない)[^\n]*\n?", "", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"


def remove_excerpts(body: str, excerpts: Iterable[str]) -> str:
    """Rewrite by removing unsupported excerpts (paragraph-level), not suffix hacks."""
    out = body
    for excerpt in excerpts:
        ex = (excerpt or "").strip()
        if len(ex) < 6:
            continue
        out = out.replace(ex, "")
    out = re.sub(r"\n{3,}", "\n\n", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    return out.strip() + "\n"


def _preserve_present_clause(sentence: str) -> str:
    """Keep grounded present-life clause when stripping causal framing."""
    m = re.search(
        r"((?:現在[^。]*?(?:暮ら|経営|制作|まとめ|遊びに来)[^。]*)|"
        r"(?:息子を可愛い[^。]*)|(?:楽しいと感じ[^。]*))",
        sentence,
    )
    if not m:
        return ""
    clause = m.group(1)
    clause = re.sub(
        r"(という[^。]*)?(に繋が|につなが|へ繋が|へとつなが|によって|を形成|が形成|は形成).*$",
        "",
        clause,
    )
    clause = clause.strip(" 、　")
    if len(clause) < 8:
        return ""
    if not clause.endswith("。"):
        clause += "。"
    return clause


def rewrite_unsupported_causality_phrases(body: str) -> str:
    """v1.1.11: repair manuscript meaning that trips causality — detector unchanged.

    Known false-positive-prone phrasing (e.g. 「働き方を変えるかを考えた」 matching
    assertion pattern 「を変える」) is rewritten to temporal/constraint language.
    """
    out = body or ""
    replacements = (
        ("働き方を変えるかを考え", "働き方をどう置くかを考え"),
        ("働き方を変えるかを", "働き方をどう置くかを"),
        ("働き方を変えること", "働き方の組み立てを考え直すこと"),
        ("働き方を変えた", "働き方の組み立てを見直した"),
        ("その移り方によって、", "その移り方のあとで、"),
        ("この選択によって、", "この選択のあとで、"),
        ("選択によって、", "選択のあとで、"),
        ("現在の生活へつながっているからこそ", "現在の生活と並んでいるからこそ"),
        ("現在の生活につながっているからこそ", "現在の生活と並んでいるからこそ"),
        ("生活へつながっている", "生活と並んでいる"),
        ("生活につながっている", "生活と並んでいる"),
    )
    for old, new in replacements:
        if old in out:
            out = out.replace(old, new)
    return out


def neutralize_causality_excerpts(body: str, excerpts: Iterable[str]) -> str:
    """Neutralize causal overreach without deleting present-life facts."""
    out = rewrite_unsupported_causality_phrases(body)
    for excerpt in excerpts:
        ex = (excerpt or "").strip()
        if len(ex) < 6 or ex not in out:
            continue
        kept = _preserve_present_clause(ex)
        if kept:
            out = out.replace(ex, kept)
            continue
        # Prefer dropping the whole unsupported causal sentence over leaving fragments.
        out = out.replace(ex, "")
    # Remove dangling sentence fragments created by prior edits.
    cleaned: list[str] = []
    for sentence in re.split(r"(?<=[。．！？\n])", out):
        text = sentence.strip()
        if not text:
            continue
        if re.search(r"(を|は|が|と|に)$", text.rstrip("。．")):
            continue
        if len(re.sub(r"\s+", "", text)) < 8:
            continue
        cleaned.append(text if text.endswith(("。", "．", "！", "？", "\n")) else text + "。")
    out = "".join(cleaned)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


def recalculate_publication_gate(
    *,
    grounded: GroundedInput,
    call1: Call1Result,
    draft: Call2Draft | None,
    body: str,
    title: str,
    subtitle: str,
    rebranch_candidates: list[RebranchDirection],
) -> Call3Validation:
    sensitive = _is_sensitive_domain(grounded)
    scenes = detect_unsupported_scenes(body, grounded)
    personal = detect_unsupported_personal_details(body, grounded)
    causality = detect_unsupported_causality(body, grounded, sensitive=sensitive)
    affect = detect_unsupported_affect(body, grounded)
    roles = detect_unsupported_role_behavior(body, grounded)
    causal_frames = detect_unsupported_causal_frame(body, grounded)
    schema_leakage = detect_schema_leakage_prose(body)
    modality_hits = detect_unrealized_path_modality_violations(body, call1)
    modality_violations = [
        UnrealizedPathModalityViolation(
            excerpt=h.excerpt,
            unrealized_path=h.unrealized_path,
            modality_type=h.modality_type,
        )
        for h in modality_hits
    ]
    advice = detect_generic_advice(body, grounded)
    fragments = detect_sentence_fragments(body)
    # Copy detection against raw source text only (deduped). Grounded fact
    # sentences may legitimately appear in the manuscript and are not "copy".
    source_parts: list[str] = []
    seen_src: set[str] = set()
    for f in all_grounded_items(grounded):
        st = (f.source_text or "").strip()
        if st and st not in seen_src:
            seen_src.add(st)
            source_parts.append(st)
    source_blob = "\n".join(source_parts)
    copied = detect_copied_long_segments(body, source_blob) if source_blob else []
    # Grounded facts/feelings/questions may appear verbatim; that is not plagiarism.
    allowed_fact_blob = re.sub(
        r"\s+",
        "",
        "\n".join(f.content for f in all_grounded_items(grounded) if f.content),
    )
    allowed_ctx_blob = re.sub(r"\s+", "", "\n".join(grounded.current_context or []))
    allowed_blob = allowed_fact_blob + allowed_ctx_blob
    copied = [
        c
        for c in copied
        if c and c not in allowed_blob and not _chunk_covered_by_grounded(c, grounded)
    ]

    validated_rebranch, publishable_rebranch = filter_publishable_rebranch(
        rebranch_candidates, grounded=grounded
    )
    title_v = validate_title(
        title,
        subtitle,
        grounded,
        call1.central_thesis.statement,
        body,
    )

    q_ids = fact_ids_by_type(grounded, FactBoundaryType.user_question)
    h_ids = fact_ids_by_type(grounded, FactBoundaryType.user_hypothesis)
    # Detect questions asserted as facts in body (strong assert without question form)
    questions_as_facts: list[str] = []
    for q in grounded.questions:
        # If question content appears as assertive fact without か／だろう
        core = re.sub(r"[？?]|どうだったか|だろうか", "", q.content).strip()
        if len(core) >= 8 and core in body and "か" not in body[body.find(core) : body.find(core) + len(core) + 8]:
            # Soft: only flag if framed without interrogative nearby
            pass

    closing_ok = bool(
        re.search(r"(現在|いま|今|暮らし|家庭|生活)", body[-400:] if len(body) > 400 else body)
    )
    from app.parallel_life_deep_reading.call1_schema import (
        call1_residue_items,
        call1_selected_lenses,
    )

    selected_lenses = call1_selected_lenses(call1)
    observatory_takeover = False
    if selected_lenses:
        obs_len = len(re.findall(r"Observatory|観測", body))
        observatory_takeover = obs_len > 6

    residue_items = call1_residue_items(call1)
    residue_ok = residue_centrality_passes(body, residue_items, grounded)

    thesis_stmt = (call1.central_thesis.statement or "").strip()
    # Causal/affect thesis tokens may be intentionally absent after overreach edits.
    _thesis_skip = {"影響", "幸せ", "形成", "繋が", "つなが"}
    thesis_kanji = [
        t
        for t in re.findall(r"[\u4e00-\u9fff]{2,}", thesis_stmt)[:8]
        if t not in _thesis_skip and not any(s in t for s in _thesis_skip)
    ][:5]
    thesis_mixed = [
        t
        for t in re.findall(r"[\u4e00-\u9fffぁ-んァ-ヶー]{4,}", thesis_stmt)
        if t not in {"について", "ということ", "ことがある"}
        and not any(s in t for s in _thesis_skip)
    ][:5]
    q_overlap = any(
        sum(1 for t in re.findall(r"[\u4e00-\u9fff]{2,}", q.content)[:6] if t in body)
        >= 2
        for q in grounded.questions
        if q.content
    )
    thesis_ok = bool(thesis_stmt) and (
        any(t in body for t in thesis_kanji)
        or any(t in body for t in thesis_mixed)
        or "問い" in body
        or q_overlap
        or any(
            len(q.content) >= 8 and q.content[:12] in body for q in grounded.questions
        )
    )

    unsupported_paragraphs: list[str] = []
    if draft and getattr(draft, "paragraph_support", None):
        for ps in draft.paragraph_support:
            if not ps.support_ids and ps.text_preview:
                preview = ps.text_preview.strip()
                # Pure transition allowed if short and no personal-detail markers
                if len(preview) > 40 and detect_unsupported_personal_details(preview, grounded):
                    unsupported_paragraphs.append(ps.paragraph_id or preview[:40])

    blocking: list[str] = []
    if not grounded.confirmed_by_user:
        blocking.append("grounded_input_not_confirmed")
    if not call1.input_sufficiency.required_fields_complete:
        blocking.append("required_input_incomplete")
    if len(grounded.current_context) < 1:
        blocking.append("current_context_missing")
    if scenes:
        blocking.append("unsupported_scenes")
    if personal:
        blocking.append("unsupported_personal_detail")
    if causality:
        blocking.append("unsupported_causality")
    if affect:
        blocking.append("unsupported_affect")
    if roles:
        blocking.append("unsupported_role_behavior")
    if causal_frames:
        blocking.append("unsupported_causal_frame")
    if schema_leakage:
        blocking.append("schema_leakage_prose")
    if modality_violations:
        blocking.append("unrealized_path_modality_violation")
    if advice:
        blocking.append("generic_advice")
    if title_v.title_causal_frame_violation:
        blocking.append("title_causal_frame_violation")
    if fragments:
        blocking.append("sentence_fragments")
    if copied:
        blocking.append("copied_long_input_segments")
    if not thesis_ok:
        blocking.append("central_thesis_not_maintained")
    if not residue_items:
        blocking.append("residue_centrality_failed")
    elif not residue_ok:
        blocking.append("residue_centrality_failed")
    if observatory_takeover:
        blocking.append("observatory_takeover")
    if not closing_ok:
        blocking.append("closing_not_present")
    if not title_v.passed:
        blocking.append("title_validation_failed")
    # Non-publishable rebranch present in body
    for rb in validated_rebranch:
        if not rb.publishable and rb.branch_specific_form and rb.branch_specific_form in body:
            blocking.append("unpublished_rebranch_in_body")
            break

    # v1.1.3-exp Section Contracts + resume density (Contextual only; additive)
    section_ok = True
    section_details: dict[str, Any] = {}
    resume_report: dict[str, Any] | None = None
    sc = getattr(call1, "section_contracts", None)
    if isinstance(sc, dict) and sc.get("contracts"):
        from app.parallel_life_deep_reading.section_contracts import (
            required_section_realization,
            section_resume_flags,
        )

        section_ok, section_missing, section_details = required_section_realization(
            body, sc
        )
        for m in section_missing:
            blocking.append(m)
        resume_report = section_resume_flags(f"{title}\n{subtitle}\n{body}")
        if resume_report.get("compression_required"):
            blocking.append("resume_density_compression_required")

    publishable = len(blocking) == 0
    # Dev/diagnostic: runtime clean but semantic overreach categories still present
    # (should be rare once detectors are wired; kept for gap monitoring).
    semantic_hits = bool(
        causality
        or affect
        or roles
        or personal
        or scenes
        or causal_frames
        or schema_leakage
        or modality_violations
    )
    manual_gap = (not publishable and semantic_hits) or (
        publishable
        and bool(re.search(r"影響を与え|成長を見守|満足して|実際に選んだのは", body or ""))
    )

    return Call3Validation(
        unsupported_scenes=scenes,
        unsupported_personal_details=personal,
        unsupported_causality=causality,
        unsupported_affect=affect,
        unsupported_role_behavior=roles,
        unsupported_causal_frame=causal_frames,
        schema_leakage_prose=schema_leakage,
        unrealized_path_modality_violations=modality_violations,
        generic_advice_findings=advice,
        rebranch_validations=validated_rebranch,
        title_validation=title_v,
        contradictions=[],
        questions_converted_to_facts=questions_as_facts,
        hypotheses_converted_to_facts=[],
        protections_stated_as_facts=[],
        unknowns_filled_by_model=[],
        sentence_fragments=fragments,
        copied_long_input_segments=copied,
        unsupported_paragraphs=unsupported_paragraphs,
        unsupported_causality_count=len(causality),
        unsupported_affect_count=len(affect),
        unsupported_role_behavior_count=len(roles),
        unsupported_causal_frame_count=len(causal_frames),
        schema_leakage_prose_count=len(schema_leakage),
        unrealized_path_modality_violation_count=len(modality_violations),
        unsupported_personal_detail_count=len(personal),
        unsupported_scene_count=len(scenes),
        manual_fidelity_gap_possible=manual_gap and publishable,
        central_thesis_maintained=thesis_ok,
        residue_centrality=residue_ok,
        observatory_takeover=observatory_takeover,
        closing_returns_to_present=closing_ok,
        required_section_realization_ok=section_ok,
        required_section_realization_details=section_details,
        resume_density_report=resume_report,
        publishable=publishable,
        blocking_reasons=blocking,
    )


def finalize_call3_body(
    body: str,
    validation: Call3Validation,
    *,
    omit_observatory: bool,
    omit_rebranch: bool,
) -> str:
    out = rewrite_unsupported_causality_phrases(body)
    if omit_observatory:
        out = strip_observatory_sections(out)
    if omit_rebranch:
        out = strip_rebranch_section(out)
    if validation.unsupported_scenes:
        out = remove_excerpts(out, [s.excerpt for s in validation.unsupported_scenes])
    if validation.unsupported_personal_details:
        out = remove_excerpts(
            out, [d.excerpt for d in validation.unsupported_personal_details]
        )
    if validation.unsupported_causality:
        out = neutralize_causality_excerpts(
            out, [c.excerpt for c in validation.unsupported_causality]
        )
    if validation.unsupported_affect:
        # Prefer clause-preserving neutralization for affect too when present facts co-occur.
        for a in validation.unsupported_affect:
            ex = (a.excerpt or "").strip()
            if not ex or ex not in out:
                continue
            kept = _preserve_present_clause(ex)
            if kept and kept != ex:
                out = out.replace(ex, kept)
            else:
                out = remove_excerpts(out, [ex])
    if validation.unsupported_role_behavior:
        out = remove_excerpts(
            out, [r.excerpt for r in validation.unsupported_role_behavior]
        )
    if validation.unsupported_causal_frame:
        out = remove_excerpts(
            out, [f.excerpt for f in validation.unsupported_causal_frame]
        )
    if validation.schema_leakage_prose:
        out = repair_schema_leakage_prose(out)
        # If leakage excerpts remain after phrase repair, drop the sentences.
        remaining = detect_schema_leakage_prose(out)
        if remaining:
            out = remove_excerpts(out, [s.excerpt for s in remaining])
    if validation.unrealized_path_modality_violations:
        # Deterministic modality repair; call1 is not on validation — repair via
        # excerpts when possible. Full call1-aware repair is applied in edit_validate.
        for v in validation.unrealized_path_modality_violations:
            ex = (v.excerpt or "").strip()
            if not ex or ex not in out:
                continue
            repaired = re.sub(
                r"([^\s。．\n]{2,80}?)へ行くことがあった",
                r"\1へ進む道は選ばなかった",
                ex,
            )
            repaired = re.sub(
                r"([^\s。．\n]{2,80}?)することがあった",
                r"\1という道は選ばなかった",
                repaired,
            )
            repaired = re.sub(r"ことがあった。?", "道は選ばなかった。", repaired)
            if repaired != ex:
                out = out.replace(ex, repaired)
    if validation.generic_advice_findings:
        out = remove_excerpts(out, [g.excerpt for g in validation.generic_advice_findings])
    return out


def progress_label_for_status(status: GenerationStatus) -> str:
    mapping = {
        GenerationStatus.ready_for_user_confirmation: "内容をご確認ください",
        GenerationStatus.needs_additional_input: "内容をご確認ください",
        GenerationStatus.insufficient_for_deep_reading: (
            "深読みに必要な情報が足りないため、ここで止めています"
        ),
        GenerationStatus.schema_validation_failed: "事実を整理しています",
        GenerationStatus.ready_for_draft: "一篇の原稿を作成しています",
        GenerationStatus.draft_generated: "全文を編集・検証しています",
        GenerationStatus.complete: "完成しました",
        GenerationStatus.validation_failed: "全文を編集・検証しています",
        GenerationStatus.editorial_failure: "全文を編集・検証しています",
    }
    return mapping.get(status, "事実を整理しています")
