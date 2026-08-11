"""Deep Reading v1.1.2-exp Observatory-Core (pre-thesis lenses).

Contextual / flag-gated only. Production Strict v1.0.2 ignores this module.

Pipeline (Contextual):
  Branch + Approved Context Pack
  → Candidate Lens Selection (structural)
  → Observatory Evidence Retrieval (curated, capped)
  → CrossLensRelations
  → Relevant Context Selection / Meaning Compression / Central Thesis
  → Lost / Protected / Residue / Re-branch → Manuscript

Privacy: Observatory store holds only public/editorial SHIRO & Co. observations.
Never store private user facts here. Never invent personal biography from evidence.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.parallel_life_deep_reading.context_pack import (
    ContextPack,
    ContextPackCategory,
    approved_items,
)

CALL_1_PROMPT_VERSION_V112 = "parallel-life-call-1-v1.1.2-exp"
RUNTIME_VERSION_V112_EXP = "parallel-life-runtime-v1.1.2-exp"

# Experimental curated lens subset (Body Meaning → registry id `body`).
CURATED_LENS_IDS: tuple[str, ...] = (
    "education-employment",
    "market-signals",
    "clean-society",
    "body",
    "after-success",
    "protocol-publishing",
)

MAX_CANDIDATE_LENSES = 4
MAX_EVIDENCE_PER_LENS = 3
MAX_EVIDENCE_GLOBAL = 6
MAX_CROSS_LENS_RELATIONS = 4

# Project / brand strings that must never drive lens selection (anti-self-promotion).
PROMO_BLOCK_RE = re.compile(
    r"(?:観測所|Observatory|Protocol\s*Publishing|プロトコル.?パブリッシング|"
    r"Market\s*Signals|Clean\s*Society|SHIRO\s*&\s*Co|Kosuke\s*Protocol)",
    re.I,
)

RelationType = Literal[
    "parallel",
    "contrast",
    "continuity",
    "tension",
    "historical_alignment",
    "institutional_context",
    "market_context",
    "cultural_context",
]

CausalityStatus = Literal[
    "non_causal_parallel",
    "supported_causal",
    "unsupported_causal_rejected",
]


class FreshnessClass(str, Enum):
    historical_conceptual = "historical_conceptual"
    time_sensitive = "time_sensitive"
    unknown = "unknown"


class ObservatoryEvidence(BaseModel):
    """Compact structural observation — not a prose essay."""

    id: str = ""
    lens_id: str = ""
    observation_id: str = ""
    structural_pattern: str = ""
    scope: str = ""
    time_context: str = ""
    evidence_source: str = ""
    relevance_hint: str = ""
    confidence: float = 0.0
    freshness: FreshnessClass = FreshnessClass.historical_conceptual
    # ISO date for time_sensitive items; empty if conceptual.
    as_of: str = ""
    allowed_for_interpretation: bool = True


class CandidateLens(BaseModel):
    lens_id: str = ""
    structural_reason: str = ""
    structures_matched: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    rejected_promo: bool = False


class CandidateLensSelection(BaseModel):
    candidates: list[CandidateLens] = Field(default_factory=list)
    zero_lens_reason: str = ""
    selection_method: str = "structural_v1"


class CrossLensRelation(BaseModel):
    id: str = ""
    personal_structure: str = ""
    social_structure: str = ""
    relation_type: RelationType = "parallel"
    branch_evidence_ids: list[str] = Field(default_factory=list)
    context_pack_ids: list[str] = Field(default_factory=list)
    observatory_evidence_ids: list[str] = Field(default_factory=list)
    interpretation: str = ""
    causality_status: CausalityStatus = "non_causal_parallel"
    confidence: float = 0.0


class ObservatoryCoreBundle(BaseModel):
    """Server-built pre-thesis observatory package injected into Call1."""

    candidate_lens_selection: CandidateLensSelection = Field(
        default_factory=CandidateLensSelection
    )
    retrieved_observatory_evidence: list[ObservatoryEvidence] = Field(
        default_factory=list
    )
    cross_lens_relations: list[CrossLensRelation] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


# --- Curated store (repository-grounded only; sources cited) -----------------
# Sources:
# - app/observatory_lenses.py descriptors/descriptions
# - app/parallel_life_engine.py `_lens_body_ja` / tension keys (compressed)

_CURATED: list[ObservatoryEvidence] = [
    ObservatoryEvidence(
        id="obs_ee_001",
        lens_id="education-employment",
        observation_id="ee_longterm_vs_mobile",
        structural_pattern=(
            "日本型の長期雇用・一社内での役割蓄積モデルと、"
            "企業間移動を前提とするキャリアモデルが併存してきた"
        ),
        scope="employment_regime",
        time_context="japan_postwar_to_present",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:education-employment;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="stay_inside_one_firm_vs_leave_for_mobile_career",
        confidence=0.9,
        freshness=FreshnessClass.historical_conceptual,
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_ee_002",
        lens_id="education-employment",
        observation_id="ee_institution_sets_terms",
        structural_pattern=(
            "教育から就労への移行や配属・転勤の制度が、"
            "仕事だけでなく住む場所や独立のタイミングまで同時に条件づけることがある"
        ),
        scope="school_to_work_and_firm_internal",
        time_context="japan_institutional_transition",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:education-employment;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="education_to_employment_or_internal_ladder",
        confidence=0.85,
        freshness=FreshnessClass.historical_conceptual,
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_ms_001",
        lens_id="market-signals",
        observation_id="ms_livelihood_conditions",
        structural_pattern=(
            "住まい・収入・地域の労働市場・世帯形成の条件が、"
            "個人の意思だけでは決めきれない生活の可否を形づくる"
        ),
        scope="livelihood_market",
        time_context="general_contemporary",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:market-signals;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="housing_income_household_constraints",
        confidence=0.85,
        freshness=FreshnessClass.time_sensitive,
        as_of="2024-01-01",
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_ms_002",
        lens_id="market-signals",
        observation_id="ms_job_mobility_cost",
        structural_pattern=(
            "転職・転居に伴う収入リスクと移動コストが、"
            "『残る／移る』の分岐の重さを経済条件として左右しうる"
        ),
        scope="job_mobility_market",
        time_context="contemporary_labor_market",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:market-signals;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="leave_vs_stay_with_economic_weight",
        confidence=0.8,
        freshness=FreshnessClass.time_sensitive,
        as_of="2024-01-01",
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_cs_001",
        lens_id="clean-society",
        observation_id="cs_normal_path_narrowing",
        structural_pattern=(
            "『普通はこうするものだ』という規範が、"
            "一社に留まり役割を積む道を標準として選択の幅を静かに狭めることがある"
        ),
        scope="normative_narrowing",
        time_context="era_dependent_norms",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:clean-society;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="normal_large_firm_path_vs_exit",
        confidence=0.85,
        freshness=FreshnessClass.historical_conceptual,
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_body_001",
        lens_id="body",
        observation_id="body_lived_choice",
        structural_pattern=(
            "分岐は思考上の選択だけでなく、疲れ・回復・ケアなど身体で経験された時間でもある"
        ),
        scope="embodied_branch",
        time_context="ahistorical_structural",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:body;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="illness_fatigue_care_or_fertility_body",
        confidence=0.85,
        freshness=FreshnessClass.historical_conceptual,
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_as_001",
        lens_id="after-success",
        observation_id="as_questions_after_achievement",
        structural_pattern=(
            "達成や評価のあとに残る問いは、達成前の問いとは形が違い、"
            "承認だけでは閉じない生活の問いが残ることがある"
        ),
        scope="post_achievement",
        time_context="ahistorical_structural",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:after-success;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="achievement_then_unresolved_life_question",
        confidence=0.8,
        freshness=FreshnessClass.historical_conceptual,
        allowed_for_interpretation=True,
    ),
    ObservatoryEvidence(
        id="obs_pp_001",
        lens_id="protocol-publishing",
        observation_id="pp_anonymous_social_pattern",
        structural_pattern=(
            "一つの分岐を、似た年齢・就労形態・時代条件の匿名記録と並べると、"
            "個人選択の背後に社会的パターンが見えることがある（実名なし・比較軸のみ）"
        ),
        scope="anonymous_comparative_reading",
        time_context="methodological",
        evidence_source=(
            "kosuke-backend/app/observatory_lenses.py:protocol-publishing;"
            "kosuke-backend/app/parallel_life_engine.py:_lens_body_ja"
        ),
        relevance_hint="asks_for_social_pattern_reading_not_project_ownership",
        confidence=0.75,
        freshness=FreshnessClass.historical_conceptual,
        allowed_for_interpretation=True,
    ),
]


def curated_evidence_store() -> list[ObservatoryEvidence]:
    return list(_CURATED)


def evidence_by_id(eid: str) -> ObservatoryEvidence | None:
    for e in _CURATED:
        if e.id == eid:
            return e
    return None


# --- Structural detection (not lens-name / project-name matching) ------------

def _blob(branch_text: str, pack: ContextPack | None) -> str:
    parts = [branch_text or ""]
    for item in approved_items(pack):
        # Strip promo lines from detection blob used for protocol-publishing
        content = (item.content or "").strip()
        if content:
            parts.append(content)
    return "\n".join(parts)


def detect_structures(
    branch_text: str,
    pack: ContextPack | None,
    *,
    branch_semantics: dict[str, Any] | None = None,
) -> set[str]:
    """Return structural feature tags — independent of observatory project names.

    BranchSemantics may refine matching (never loosens confidence thresholds).
    """
    text = branch_text or ""
    pack_text = "\n".join(
        (i.content or "")
        for i in approved_items(pack)
        if not PROMO_BLOCK_RE.search(i.content or "")
    )
    combined = f"{text}\n{pack_text}"
    found: set[str] = set()
    sem = branch_semantics or {}
    domain = (sem.get("domain") or "").strip()
    explicit_employment = bool((sem.get("diagnostics") or {}).get("explicit_employment_evidence"))

    # Employment regime boundary: require firm/job markers — not bare 残る/移る
    stay = bool(re.search(r"(?:残[るりっ]|留ま|一企業|内部で役割|積み上げ)", text))
    leave = bool(re.search(r"(?:離[れれ]|退職|転職|移[るりっ]|外資)", text))
    firmish = bool(
        re.search(r"(?:一企業|内部で役割|積み上げ|退職|転職|外資|NTT|大企業|社内|組織内|勤務)", text)
        or explicit_employment
    )
    if stay and leave and firmish:
        found.add("employment_regime_boundary")
    if leave and re.search(r"(?:NTT|大企業|社内|組織内)", text):
        found.add("employment_regime_boundary")
    # Non-career BranchSemantics: do not keep employment from weak stay/leave alone
    if domain in {
        "family",
        "romance",
        "health",
        "creative",
        "place",
        "caregiving",
        "education",
    } and not explicit_employment:
        found.discard("employment_regime_boundary")

    if re.search(r"(?:大学|進学|卒業|就職|受験|学部)", combined):
        found.add("education_transition")

    if re.search(r"(?:家賃|収入|給料|生活費|転居|住まい|経済)", combined):
        found.add("livelihood_constraints")

    if re.search(r"(?:普通|べき|世間|常識|期待に応)", combined) or (
        "employment_regime_boundary" in found
    ):
        # Normative "stay" path is often silent; regime boundary implies clean-society candidate
        if "employment_regime_boundary" in found:
            found.add("normative_standard_path")

    if re.search(
        r"(?:病|疲れ|体調|入院|介護|不妊|治療|身体|妊娠|授かり)", combined
    ) or domain in {"family", "health", "caregiving"}:
        if re.search(
            r"(?:病|疲れ|体調|入院|介護|不妊|治療|身体|妊娠|授かり|家族)", combined
        ):
            found.add("embodied_or_fertility")

    if re.search(r"(?:成功|達成|評価|受賞|経営している|自分の会社)", combined) and re.search(
        r"(?:問い|考える|残る|いまも)", combined
    ):
        found.add("post_achievement_question")

    # Social-pattern *reading intent* — not project ownership
    if re.search(
        r"(?:社会的なパターン|匿名の記録|他の人の記録|同じ条件の人)", text
    ) and not PROMO_BLOCK_RE.search(text):
        found.add("social_pattern_reading_intent")

    if re.search(r"(?:創作|小説|芸術|音楽|表現)", combined) and re.search(
        r"(?:会社|就職|企業|安定)", combined
    ):
        found.add("creative_vs_corporate")

    if re.search(r"(?:家族|妻|夫|息子|娘|子ども|三人家族)", combined) or domain == "family":
        found.add("family_life")

    return found


# Map structures → candidate lenses (curated subset only)
_STRUCTURE_TO_LENSES: dict[str, list[tuple[str, str, float]]] = {
    "employment_regime_boundary": [
        (
            "education-employment",
            "一社内蓄積キャリアと企業間移動キャリアの境界として読める",
            0.92,
        ),
        (
            "clean-society",
            "『普通の』長期雇用パスが選択幅を狭めていた可能性を構造として置ける",
            0.78,
        ),
    ],
    "education_transition": [
        (
            "education-employment",
            "教育→就労の制度条件が分岐の枠を与えている",
            0.88,
        ),
    ],
    "livelihood_constraints": [
        (
            "market-signals",
            "生活成立の市場条件が分岐の重さに関わる",
            0.84,
        ),
    ],
    "normative_standard_path": [
        (
            "clean-society",
            "標準化された進路規範との緊張として読める",
            0.8,
        ),
    ],
    "embodied_or_fertility": [
        (
            "body",
            "身体・ケア・生殖の経験として分岐が生きられている",
            0.9,
        ),
    ],
    "post_achievement_question": [
        (
            "after-success",
            "達成後にも閉じない問いが残る構造",
            0.82,
        ),
    ],
    "social_pattern_reading_intent": [
        (
            "protocol-publishing",
            "匿名比較として社会パターンを読む意図が分岐側にある",
            0.7,
        ),
    ],
    "creative_vs_corporate": [
        (
            "education-employment",
            "進路・就労の制度と表現活動のあいだの分岐",
            0.72,
        ),
        (
            "after-success",
            "どちらの達成尺度が残るかを問う構造",
            0.65,
        ),
    ],
}


def select_candidate_lenses(
    branch_text: str,
    pack: ContextPack | None,
    *,
    max_lenses: int = MAX_CANDIDATE_LENSES,
    branch_semantics: dict[str, Any] | None = None,
) -> CandidateLensSelection:
    """Structural selection. Zero lenses is valid. Never select for project names."""
    structures = detect_structures(
        branch_text, pack, branch_semantics=branch_semantics
    )
    promo_in_pack = any(
        PROMO_BLOCK_RE.search(i.content or "") for i in approved_items(pack)
    )

    scored: dict[str, CandidateLens] = {}
    for struct in structures:
        for lens_id, reason, conf in _STRUCTURE_TO_LENSES.get(struct, []):
            if lens_id not in CURATED_LENS_IDS:
                continue
            # Anti-self-promotion: never select protocol-publishing because pack
            # mentions Observatory / Protocol Publishing projects.
            if lens_id == "protocol-publishing" and promo_in_pack:
                if "social_pattern_reading_intent" not in structures:
                    continue
            if lens_id == "protocol-publishing" and struct != "social_pattern_reading_intent":
                continue
            prev = scored.get(lens_id)
            if prev is None or conf > prev.confidence:
                matched = list(dict.fromkeys([*(prev.structures_matched if prev else []), struct]))
                scored[lens_id] = CandidateLens(
                    lens_id=lens_id,
                    structural_reason=reason,
                    structures_matched=matched,
                    confidence=conf,
                    rejected_promo=False,
                )
            elif prev is not None:
                matched = list(dict.fromkeys([*prev.structures_matched, struct]))
                scored[lens_id] = prev.model_copy(update={"structures_matched": matched})

    ranked = sorted(scored.values(), key=lambda c: (-c.confidence, c.lens_id))
    # Prefer distinct explanatory structures; cap
    selected = ranked[:max_lenses]
    zero_reason = ""
    if not selected:
        zero_reason = "no_structural_lens_advantage"
    return CandidateLensSelection(
        candidates=selected,
        zero_lens_reason=zero_reason,
        selection_method="structural_v1",
    )


def _freshness_ok(ev: ObservatoryEvidence, *, today: date | None = None) -> bool:
    if ev.freshness != FreshnessClass.time_sensitive:
        return True
    if not ev.as_of:
        return True
    today = today or date.today()
    try:
        y, m, d = (int(x) for x in ev.as_of.split("-")[:3])
        as_of = date(y, m, d)
    except Exception:
        return True
    # Downweight/exclude if older than ~3 years for time_sensitive market/employment notes
    return (today - as_of).days <= 365 * 3


def retrieve_observatory_evidence(
    candidates: CandidateLensSelection,
    *,
    structures: set[str],
    today: date | None = None,
) -> list[ObservatoryEvidence]:
    """Retrieve 1–3 items per lens, global max 6. No full dump."""
    if not candidates.candidates:
        return []
    picked: list[ObservatoryEvidence] = []
    per_lens: dict[str, int] = {}

    # Rank store items by relevance to detected structures + candidate confidence
    cand_conf = {c.lens_id: c.confidence for c in candidates.candidates}
    pool = [
        e
        for e in _CURATED
        if e.lens_id in cand_conf
        and e.allowed_for_interpretation
        and _freshness_ok(e, today=today)
    ]

    def score(e: ObservatoryEvidence) -> float:
        s = e.confidence * 10 + cand_conf.get(e.lens_id, 0) * 5
        hint = e.relevance_hint or ""
        if "employment_regime_boundary" in structures and (
            "mobile" in hint or "leave" in hint or "firm" in hint
        ):
            s += 3
        if "education_transition" in structures and "education" in hint:
            s += 3
        if "livelihood_constraints" in structures and e.lens_id == "market-signals":
            s += 3
        if "embodied_or_fertility" in structures and e.lens_id == "body":
            s += 4
        if "post_achievement_question" in structures and e.lens_id == "after-success":
            s += 3
        if e.freshness == FreshnessClass.time_sensitive:
            s -= 0.5  # slight preference for conceptual when both apply
        # Novelty: prefer distinct observation_ids
        return s

    for e in sorted(pool, key=score, reverse=True):
        n = per_lens.get(e.lens_id, 0)
        if n >= MAX_EVIDENCE_PER_LENS:
            continue
        if len(picked) >= MAX_EVIDENCE_GLOBAL:
            break
        picked.append(e)
        per_lens[e.lens_id] = n + 1
    return picked


def _pack_career_ids(pack: ContextPack | None) -> list[str]:
    ids: list[str] = []
    for i in approved_items(pack):
        if i.category in (
            ContextPackCategory.career_history,
            ContextPackCategory.current_work,
            ContextPackCategory.major_life_events,
        ):
            if not PROMO_BLOCK_RE.search(i.content or ""):
                ids.append(i.id)
    return ids


def _branch_fact_ids_placeholder() -> list[str]:
    # Filled later by runtime with real fact ids; drafts use generic anchors.
    return []


CAUSAL_REJECT_RE = re.compile(
    r"(?:引き起こ|追いや|せざるを得|のせいだ|が原因で|させた|強いた)"
)


def draft_cross_lens_relations(
    *,
    branch_text: str,
    pack: ContextPack | None,
    structures: set[str],
    evidence: list[ObservatoryEvidence],
    branch_evidence_ids: list[str] | None = None,
) -> list[CrossLensRelation]:
    """Deterministic non-causal relations for pre-thesis compression."""
    if not evidence:
        return []
    branch_ids = list(branch_evidence_ids or [])
    pack_ids = _pack_career_ids(pack)[:4]
    relations: list[CrossLensRelation] = []

    by_lens: dict[str, list[ObservatoryEvidence]] = {}
    for e in evidence:
        by_lens.setdefault(e.lens_id, []).append(e)

    if "employment_regime_boundary" in structures and "education-employment" in by_lens:
        ev = by_lens["education-employment"][0]
        personal = "一企業の内部で役割を積み上げる道を離れた"
        if not re.search(r"(?:離|退職|転職|移)", branch_text or ""):
            personal = "一社内での役割蓄積と、別の就労形態とのあいだに立っていた"
        interp = (
            "個人の会社選択であると同時に、一社内で地位を蓄積するキャリアと、"
            "企業間を移動しながら専門性を持ち運ぶキャリアの境界として読むことができる"
        )
        relations.append(
            CrossLensRelation(
                id="clr_ee_regime_001",
                personal_structure=personal,
                social_structure=ev.structural_pattern,
                relation_type="institutional_context",
                branch_evidence_ids=branch_ids[:3],
                context_pack_ids=pack_ids[:3],
                observatory_evidence_ids=[ev.id],
                interpretation=interp,
                causality_status="non_causal_parallel",
                confidence=0.88,
            )
        )
    elif "education_transition" in structures and "education-employment" in by_lens:
        ev = by_lens["education-employment"][-1]
        relations.append(
            CrossLensRelation(
                id="clr_ee_transition_001",
                personal_structure="進学・就労の分岐を個人の選択として生きた",
                social_structure=ev.structural_pattern,
                relation_type="institutional_context",
                branch_evidence_ids=branch_ids[:3],
                context_pack_ids=pack_ids[:2],
                observatory_evidence_ids=[ev.id],
                interpretation=(
                    "個人の進学選択は、教育から就労へ移る制度条件と並べて読める"
                    "（制度が進路を決定したとは断言しない）"
                ),
                causality_status="non_causal_parallel",
                confidence=0.84,
            )
        )

    if "normative_standard_path" in structures and "clean-society" in by_lens:
        ev = by_lens["clean-society"][0]
        relations.append(
            CrossLensRelation(
                id="clr_cs_norm_001",
                personal_structure="『残る』側が標準の進路として置かれていた",
                social_structure=ev.structural_pattern,
                relation_type="cultural_context",
                branch_evidence_ids=branch_ids[:2],
                context_pack_ids=pack_ids[:2],
                observatory_evidence_ids=[ev.id],
                interpretation=(
                    "個人の去就は、当時『普通』とされていた長期雇用パスと並べて読める"
                    "（規範が強制したとは断言しない）"
                ),
                causality_status="non_causal_parallel",
                confidence=0.8,
            )
        )

    if "livelihood_constraints" in structures and "market-signals" in by_lens:
        ev = by_lens["market-signals"][0]
        relations.append(
            CrossLensRelation(
                id="clr_ms_livelihood_001",
                personal_structure="生活を成り立たせる条件のなかで分岐を経験した",
                social_structure=ev.structural_pattern,
                relation_type="market_context",
                branch_evidence_ids=branch_ids[:2],
                context_pack_ids=pack_ids[:2],
                observatory_evidence_ids=[ev.id],
                interpretation="個人の選択の重さは、市場条件と並べて読める（因果断定なし）",
                causality_status="non_causal_parallel",
                confidence=0.8,
            )
        )

    if "embodied_or_fertility" in structures and "body" in by_lens:
        ev = by_lens["body"][0]
        relations.append(
            CrossLensRelation(
                id="clr_body_001",
                personal_structure="身体とケアの時間のなかで分岐が生きられた",
                social_structure=ev.structural_pattern,
                relation_type="continuity",
                branch_evidence_ids=branch_ids[:2],
                context_pack_ids=[
                    i.id
                    for i in approved_items(pack)
                    if i.category == ContextPackCategory.family_context
                ][:2],
                observatory_evidence_ids=[ev.id],
                interpretation="個人史は身体経験として続き、制度説明に還元しない",
                causality_status="non_causal_parallel",
                confidence=0.86,
            )
        )

    if "post_achievement_question" in structures and "after-success" in by_lens:
        ev = by_lens["after-success"][0]
        relations.append(
            CrossLensRelation(
                id="clr_as_001",
                personal_structure="何かを形にしたあとも、閉じない問いが残っている",
                social_structure=ev.structural_pattern,
                relation_type="tension",
                branch_evidence_ids=branch_ids[:2],
                context_pack_ids=pack_ids[:2],
                observatory_evidence_ids=[ev.id],
                interpretation="達成の事実と、なお残る問いを並置して読める",
                causality_status="non_causal_parallel",
                confidence=0.78,
            )
        )

    if "social_pattern_reading_intent" in structures and "protocol-publishing" in by_lens:
        ev = by_lens["protocol-publishing"][0]
        relations.append(
            CrossLensRelation(
                id="clr_pp_001",
                personal_structure="この分岐を個人の逸話だけで閉じたくない",
                social_structure=ev.structural_pattern,
                relation_type="parallel",
                branch_evidence_ids=branch_ids[:2],
                context_pack_ids=[],
                observatory_evidence_ids=[ev.id],
                interpretation="匿名比較の読みとして社会パターンを置く（プロジェクト宣伝ではない）",
                causality_status="non_causal_parallel",
                confidence=0.7,
            )
        )

    # Sanitize causality
    cleaned: list[CrossLensRelation] = []
    for r in relations[:MAX_CROSS_LENS_RELATIONS]:
        if CAUSAL_REJECT_RE.search(r.interpretation or ""):
            cleaned.append(
                r.model_copy(update={"causality_status": "unsupported_causal_rejected"})
            )
        else:
            cleaned.append(r)
    return [r for r in cleaned if r.causality_status != "unsupported_causal_rejected"]


def build_observatory_core_bundle(
    branch_text: str,
    pack: ContextPack | None,
    *,
    branch_evidence_ids: list[str] | None = None,
    branch_semantics: dict[str, Any] | None = None,
) -> ObservatoryCoreBundle:
    structures = detect_structures(
        branch_text, pack, branch_semantics=branch_semantics
    )
    selection = select_candidate_lenses(
        branch_text, pack, branch_semantics=branch_semantics
    )
    evidence = retrieve_observatory_evidence(selection, structures=structures)
    relations = draft_cross_lens_relations(
        branch_text=branch_text,
        pack=pack,
        structures=structures,
        evidence=evidence,
        branch_evidence_ids=branch_evidence_ids,
    )
    stale_excluded = [
        e.id
        for e in _CURATED
        if e.lens_id in {c.lens_id for c in selection.candidates}
        and not _freshness_ok(e)
    ]
    return ObservatoryCoreBundle(
        candidate_lens_selection=selection,
        retrieved_observatory_evidence=evidence,
        cross_lens_relations=relations,
        diagnostics={
            "structures_detected": sorted(structures),
            "candidate_lens_ids": [c.lens_id for c in selection.candidates],
            "evidence_ids": [e.id for e in evidence],
            "relation_ids": [r.id for r in relations],
            "stale_excluded_ids": stale_excluded,
            "promo_blocked_from_selection": any(
                PROMO_BLOCK_RE.search(i.content or "") for i in approved_items(pack)
            ),
            "branch_semantics_domain": (branch_semantics or {}).get("domain"),
            "runtime_pin": RUNTIME_VERSION_V112_EXP,
            "prompt_pin": CALL_1_PROMPT_VERSION_V112,
        },
    )


def serialize_bundle_for_prompt(bundle: ObservatoryCoreBundle) -> dict[str, Any]:
    return {
        "candidate_lenses": [
            {
                "lens_id": c.lens_id,
                "structural_reason": c.structural_reason,
                "confidence": c.confidence,
            }
            for c in bundle.candidate_lens_selection.candidates
        ],
        "observatory_evidence": [
            {
                "id": e.id,
                "lens_id": e.lens_id,
                "structural_pattern": e.structural_pattern,
                "scope": e.scope,
                "confidence": e.confidence,
                "freshness": e.freshness.value
                if hasattr(e.freshness, "value")
                else str(e.freshness),
            }
            for e in bundle.retrieved_observatory_evidence
        ],
        "cross_lens_relations": [
            r.model_dump(mode="json") for r in bundle.cross_lens_relations
        ],
        "rules": {
            "causality_default": "non_causal_parallel",
            "do_not_advertise_lens_names_in_manuscript": True,
            "zero_lenses_valid": True,
            "personal_branch_primary": True,
            "observatory_section_only_if_new_meaning": True,
        },
    }


def merge_bundle_into_call1_fields(
    *,
    bundle: ObservatoryCoreBundle,
    llm_relations: list[Any] | None = None,
) -> tuple[CandidateLensSelection, list[ObservatoryEvidence], list[CrossLensRelation]]:
    """Prefer server evidence; allow LLM to refine relations within bounds."""
    relations = list(bundle.cross_lens_relations)
    if llm_relations:
        parsed: list[CrossLensRelation] = []
        for raw in llm_relations:
            try:
                if isinstance(raw, CrossLensRelation):
                    r = raw
                elif isinstance(raw, dict):
                    r = CrossLensRelation.model_validate(raw)
                else:
                    continue
            except Exception:
                continue
            if CAUSAL_REJECT_RE.search(r.interpretation or ""):
                continue
            if r.causality_status == "supported_causal":
                # Downgrade unless we later add explicit support checks
                r = r.model_copy(update={"causality_status": "non_causal_parallel"})
            # Evidence ids must be from retrieved set
            allowed = {e.id for e in bundle.retrieved_observatory_evidence}
            obs_ids = [x for x in r.observatory_evidence_ids if x in allowed]
            if not obs_ids and allowed:
                continue
            parsed.append(r.model_copy(update={"observatory_evidence_ids": obs_ids}))
        if parsed:
            relations = parsed[:MAX_CROSS_LENS_RELATIONS]
    return (
        bundle.candidate_lens_selection,
        list(bundle.retrieved_observatory_evidence),
        relations,
    )


def relation_density_score(relations: list[CrossLensRelation], body: str = "") -> float:
    """0–10 heuristic for A/B reports."""
    if not relations and not body:
        return 0.0
    score = 0.0
    score += min(6.0, len(relations) * 2.5)
    blob = body or " ".join(r.interpretation for r in relations)
    if any(t in blob for t in ("並べて", "境界", "並置", "制度", "持ち運", "規範")):
        score += 2.0
    if CAUSAL_REJECT_RE.search(blob):
        score -= 3.0
    if any(t in blob for t in ("Market Signals", "Clean Society", "Education–Employment")):
        score -= 1.5  # lens-name advertising penalty
    return float(max(0.0, min(10.0, round(score, 1))))


def should_omit_observatory_section(
    relations: list[CrossLensRelation],
    selected_lenses_count: int,
) -> bool:
    """If relations already carry lens meaning, omit decorative Observatory section."""
    if selected_lenses_count == 0:
        return True
    if relations:
        return True  # meaning already in thesis path
    return False
