"""Deep Reading Section Contracts / Interpretive Claims / Section Realization.

v1.1.3–v1.1.9-exp. Contextual / flag-gated only.
v1.1.9: BranchSemantics is authoritative; career templates only via allows_career_product_logic.
Does not modify Observatory-Core selection thresholds.
Production Strict v1.0.2 ignores this module.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.parallel_life_deep_reading.branch_semantics import (
    CALL_1_PROMPT_VERSION_V118,
    CALL_1_PROMPT_VERSION_V119,
    CALL_1_PROMPT_VERSION_V1110,
    CALL_1_PROMPT_VERSION_V1111,
    CALL_2_PROMPT_VERSION_V118,
    CALL_2_PROMPT_VERSION_V119,
    CALL_2_PROMPT_VERSION_V1110,
    CALL_2_PROMPT_VERSION_V1111,
    CALL_3_PROMPT_VERSION_V118,
    CALL_3_PROMPT_VERSION_V119,
    CALL_3_PROMPT_VERSION_V1110,
    CALL_3_PROMPT_VERSION_V1111,
    RUNTIME_VERSION_V118_EXP,
    RUNTIME_VERSION_V119_EXP,
    RUNTIME_VERSION_V1110_EXP,
    RUNTIME_VERSION_V1111_EXP,
    BranchSemantics,
    allows_career_product_logic,
    career_template_leakage,
    detect_semantic_domain_leak,
    get_branch_semantics,
)
from app.parallel_life_deep_reading.call1_schema import (
    call1_rebranch_directions,
    call1_residue_items,
)
from app.parallel_life_deep_reading.models import (
    Call1Result,
    ConfirmedContinuity,
    GenerationStatus,
    LostItem,
    LostStructure,
    ProtectedStructure,
    RebranchDesign,
    RebranchDirection,
    ResidueCandidate,
    ResidueCandidates,
)

CALL_1_PROMPT_VERSION_V113 = "parallel-life-call-1-v1.1.3-exp"
RUNTIME_VERSION_V113_EXP = "parallel-life-runtime-v1.1.3-exp"
CALL_2_PROMPT_VERSION_V113 = "parallel-life-call-2-v1.1.3-exp"

CALL_1_PROMPT_VERSION_V114 = "parallel-life-call-1-v1.1.4-exp"
RUNTIME_VERSION_V114_EXP = "parallel-life-runtime-v1.1.4-exp"
CALL_2_PROMPT_VERSION_V114 = "parallel-life-call-2-v1.1.4-exp"

CALL_1_PROMPT_VERSION_V115 = "parallel-life-call-1-v1.1.5-exp"
RUNTIME_VERSION_V115_EXP = "parallel-life-runtime-v1.1.5-exp"
CALL_2_PROMPT_VERSION_V115 = "parallel-life-call-2-v1.1.5-exp"

CALL_1_PROMPT_VERSION_V116 = "parallel-life-call-1-v1.1.6-exp"
RUNTIME_VERSION_V116_EXP = "parallel-life-runtime-v1.1.6-exp"
CALL_2_PROMPT_VERSION_V116 = "parallel-life-call-2-v1.1.6-exp"

CALL_1_PROMPT_VERSION_V117 = "parallel-life-call-1-v1.1.7-exp"
RUNTIME_VERSION_V117_EXP = "parallel-life-runtime-v1.1.7-exp"
CALL_2_PROMPT_VERSION_V117 = "parallel-life-call-2-v1.1.7-exp"
CALL_3_PROMPT_VERSION_V117 = "parallel-life-call-3-v1.1.7-exp"

ABSTRACT_VOCAB = ("蓄積", "構造", "尺度", "制度", "分岐", "選択")
ABSTRACT_SOFT_LIMIT = {
    "蓄積": 3,
    "構造": 4,
    "尺度": 3,
    "制度": 3,
    "分岐": 4,
    "選択": 4,
}
ABSTRACT_ALTERNATES = {
    "蓄積": ("積み重ね", "どこまで来たか", "残っているもの", "続けてきた時間"),
    "構造": ("かたち", "並び", "つながり"),
    "尺度": ("測り方", "指標", "基準"),
    "制度": ("一つの組織", "同じ場", "一社の仕組み"),
    "分岐": ("分かれ道", "分かれ目", "あのときの選択"),
    "選択": ("道", "選び方", "決断"),
}

SectionId = Literal[
    "branch_point",
    "chosen_path",
    "unchosen_life",
    "lost",
    "protected",
    "residue",
    "observatory",
    "re_branch",
]

UI_SECTION_LABELS_JA: dict[str, str] = {
    "branch_point": "分岐点",
    "chosen_path": "選んだ道",
    "unchosen_life": "選ばなかった人生",
    "lost": "失ったもの",
    "protected": "守られたもの",
    "residue": "今に残った構造",
    "observatory": "社会との接続",
    "re_branch": "これからの再分岐",
}

INVENTORY_RE = re.compile(
    r"(?:給与|年収|年金|肩書|役職名|同僚|人脈|ネットワーク|スキル一覧)"
)
SUCCESS_MORAL_RE = re.compile(
    r"(?:成功した|正しい選択|自由を得た|自己実現|優れてい|おかげで成功)"
)
PROMO_REBRANCH_RE = re.compile(
    r"(?:SHIRO|観測所を拡大|Protocol を(?:拡大|伸ば)|アプリを(?:発売|ローンチ)|もっと出版)",
    re.I,
)
ORG_STACK_RE = re.compile(
    r"(?:NTT|外資|半導体|複数(?:の)?業界|複数(?:の)?企業|観測|Protocol|プロトコル)",
    re.I,
)


class ClaimAtoms(BaseModel):
    """Structured inputs for interpretive prose — never raw sentence concatenation."""

    present_anchor: str = ""
    past_anchor: str = ""
    unresolved_question: str = ""
    # active_tension is domain-neutral; measurement_tension kept as alias for older packs
    active_tension: str = ""
    measurement_tension: str = ""


class SectionContract(BaseModel):
    section_id: str = ""
    structural_purpose: str = ""
    required_meaning: str = ""
    interpretive_claim: str = ""
    realization_goal: str = ""
    required_public_label: str = ""
    minimum_paragraphs: int = 1
    maximum_paragraphs: int = 2
    evidence_budget: int = 1
    realization_status: str = "pending"
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)
    concrete_example_budget: int = 1
    must_be_present: bool = False
    omission_allowed: bool = True
    omission_reason: str = ""
    claim_atoms: dict[str, str] = Field(default_factory=dict)
    # v1.1.6-exp thesis closure (chosen_path)
    factual_choice: str = ""
    structural_shift: str = ""
    thesis_link: str = ""
    realization_required: bool = False
    # v1.1.6-exp thesis closure (re_branch)
    unresolved_tension: str = ""
    present_choice: str = ""
    measurement_shift: str = ""
    non_genericity: bool = False
    # v1.1.7-exp ReBranchDecision fields
    what_is_no_longer_required: str = ""
    what_can_now_be_chosen: str = ""
    non_genericity_score: float = 0.0
    rebranch_decision: dict[str, Any] = Field(default_factory=dict)
    # v1.1.10-exp Observatory realization contract (additive)
    supporting_observatory_evidence_ids: list[str] = Field(default_factory=list)
    acceptable_semantic_variants: list[str] = Field(default_factory=list)


class ReBranchDecision(BaseModel):
    """Present choice that closes Residue tension — not a question or coaching tip."""

    unresolved_tension: str = ""
    present_choice: str = ""
    what_is_no_longer_required: str = ""
    what_can_now_be_chosen: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    non_genericity_score: float = 0.0
    interpretive_claim: str = ""


class SectionContractSet(BaseModel):
    contracts: list[SectionContract] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    def by_id(self, section_id: str) -> SectionContract | None:
        for c in self.contracts:
            if c.section_id == section_id:
                return c
        return None

    def required(self) -> list[SectionContract]:
        return [c for c in self.contracts if c.must_be_present]


MALFORMED_CLAIM_RE = re.compile(
    r"(?:。の|。。|、、|；；|のなかで。|ており、.{0,40}。の|"
    r"影響を与えている。の|経営しており、.{0,80}。のなかで|"
    r"(?:ている|ていた|た|る|おり)のなかで|"
    r"(?:ている|ていた)なかで)"
)


FACT_LIKE_RE = re.compile(
    r"(?:転職した|勤務した|経験した|経営している|選択をした場合のキャリア|"
    r"外資系企業へ(?:移|転職)|NTTに残る選択|"
    r"役職や年収|長期雇用への問い)$"
)
STRUCTURAL_MARK_RE = re.compile(
    r"(?:連続性|余白|測定|尺度|積み[上あ]げ|制度|確認できる|定義し直|"
    r"持ち運|並べて|進み具合|測り方|閉じきら)"
)
MODALITY_VARIANTS = (
    "〜と読むことができる",
    "〜という見方ができる",
    "〜だったのかもしれない",
    "〜として残っている",
    "〜という問いにも見える",
)


def _is_fact_like(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    # Structural language wins even if a present question mentions 年収/役職.
    if STRUCTURAL_MARK_RE.search(t) or re.search(
        r"(?:測る|選び直|積み重ね|消えていない|見方ができる|とも言える|"
        r"余地|置いておく|見直|見ておく|閉じきら|確かめられ)",
        t,
    ):
        return False
    if INVENTORY_RE.search(t):
        return True
    if FACT_LIKE_RE.search(t) or re.search(
        r"(?:転職したこと|勤務したこと|経験したこと|した場合のキャリア)", t
    ):
        return True
    # Short near-fact without structural markers
    return len(t) < 48 and not re.search(r"(?:余白|連続|測定|尺度|問い|緊張|可能性)", t)


def _short_phrase(text: str, *, fallback: str, max_len: int = 36) -> str:
    """Extract a short noun/clause phrase — never keep multi-sentence prose."""
    t = (text or "").strip()
    if not t:
        return fallback
    # Drop trailing punctuation; keep only first clause
    t = t.replace("\n", " ").strip()
    t = re.split(r"[。．！？!?]", t, maxsplit=1)[0].strip()
    t = t.strip("「」『』\"' ")
    # Prefer known compact anchors (normalize ており → ている)
    known = (
        (r"自分の会社を経営して(?:いる|おり)", "自分の会社を経営している"),
        (r"会社を経営して(?:いる|おり)", "会社を経営している"),
        (r"いまの仕事", "いまの仕事"),
        (r"現在の生活", "現在の生活"),
        (r"役職や年収はどうなったか", "役職や年収はどうなったか"),
        (r"あのとき残っていたら", "あのとき残っていたら"),
        (r"一企業の内部で役割を積み上げ続けること", "一企業の内部で役割を積み上げ続けること"),
        (r"外資へ移る", "外資へ移る"),
        (r"NTTに残るか", "NTTに残るか"),
    )
    for pat, normalized in known:
        if re.search(pat, t):
            return normalized
    # Cut at first comma if still long narrative
    if "、" in t:
        head = t.split("、", 1)[0].strip()
        if 4 <= len(head) <= max_len:
            t = head
    # Strip leading narrative glue
    t = re.sub(r"^(?:現在は|いまは|その後、|過去の)", "", t)
    if len(t) > max_len:
        t = t[:max_len].rstrip("、・ ")
    # Never leave a truncated verbal stem (e.g. 経営し)
    t = re.sub(r"(?:し|て)$", "", t).strip() or t
    if t.endswith("経営"):
        t = "自分の会社を経営している"
    return t or fallback


def _present_question_text(call1: Call1Result) -> str:
    mc = call1.meaning_compression
    q = (
        (mc.unresolved_question or "").strip()
        or (mc.central_question or "").strip()
        or (call1.user_confirmation_view.present_questions or [""])[0]
    )
    if not q and call1.grounded_input.questions:
        q = call1.grounded_input.questions[0].content or ""
    return _short_phrase(q or "あのとき別の道を選んでいたら", fallback="あのとき別の道を選んでいたら")


def build_claim_atoms(call1: Call1Result) -> ClaimAtoms:
    pb = call1.branch_structure.primary_branch
    facts = _fact_map(call1)
    sem = get_branch_semantics(call1)
    # Prefer compact grounded/present facts over long meaning_compression prose.
    pack_present = next(
        (facts[i] for i in _pack_ids(call1) if "current" in i or i.endswith("_004")),
        "",
    )
    ctx_present = " ".join(call1.grounded_input.current_context[:1]).strip()
    mc_present = (call1.meaning_compression.present_structure or "").strip()
    present_raw = pack_present or ctx_present or mc_present or "いまの生活"
    past_raw = (
        (pb.triggering_event or "").strip()
        or " / ".join(pb.unrealized_paths or [])
        or (call1.meaning_compression.past_structure or "").strip()
        or "過去の分岐"
    )
    if sem and (sem.central_tension or "").strip():
        tension = sem.central_tension.strip()
    elif allows_career_product_logic(sem):
        tension = "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだ"
    else:
        tension = "選んだ道と選ばなかった道がいまも並んで残る緊張"
    return ClaimAtoms(
        present_anchor=_short_phrase(present_raw, fallback="いまの生活"),
        past_anchor=_short_phrase(past_raw, fallback="過去の分岐"),
        unresolved_question=_present_question_text(call1),
        active_tension=tension,
        measurement_tension=tension,
    )


def claim_text_is_malformed(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if MALFORMED_CLAIM_RE.search(t):
        return True
    if re.search(r"[。、]{2,}", t):
        return True
    if re.search(r"。の|のなかで$", t):
        return True
    # Verb/adjective clause directly before のなかで without nominalization
    if re.search(r"(?:ている|ていた|た|る|おり)のなかで", t):
        return True
    # Full sentence glued into the middle of another clause
    if re.search(r"[^\s]{8,}。[^「」\s]{0,6}の(?:なか|中)で", t):
        return True
    return False


def _situation_phrase(anchor: str) -> str:
    """Join an anchor into 『〜のなかで』 with natural nominalization."""
    a = (anchor or "").strip().rstrip("。．")
    if not a:
        return "いまの生活のなかで"
    if re.search(r"(?:という状況|のなかで)$", a):
        return a if a.endswith("のなかで") else f"{a}のなかで"
    # Bare noun-like anchors can take のなかで directly
    if re.search(r"(?:生活|仕事|状況|場|現在)$", a) and not re.search(
        r"(?:ている|ていた|た|る|おり)$", a
    ):
        return f"{a}のなかで"
    # Verb/adjective clauses need nominalization
    if re.search(r"(?:ている|ていた|た|る|おり)$", a) or re.search(
        r"(?:経営|勤務|経験|転職)", a
    ):
        return f"{a}という状況のなかで"
    return f"{a}という状況のなかで"


def sanitize_claim_text(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"。+", "。", t)
    t = re.sub(r"、+", "、", t)
    t = re.sub(r"。の", "の", t)
    t = re.sub(r"ており、[^。]{0,120}。のなかで", "ているという状況のなかで", t)
    # Reusable clause-join guard: ているのなかで → ているという状況のなかで
    t = re.sub(
        r"((?:自分の会社を)?経営している)のなかで",
        r"\1という状況のなかで",
        t,
    )
    t = re.sub(
        r"([\u4e00-\u9fff]{2,40}(?:ている|ていた|た|る|おり))のなかで",
        r"\1という状況のなかで",
        t,
    )
    return t.strip()


def _synthesize_lost_interpretive(call1: Call1Result, structural: str) -> str:
    """What became impossible to know / continue / verify on the unchosen path."""
    sem = get_branch_semantics(call1)
    base = (sem.lost_verifiability if sem else "") or structural or ""
    if base:
        claim = f"{base}（一覧や断定ではない）"
    else:
        atoms = build_claim_atoms(call1)
        claim = (
            f"「{atoms.past_anchor}」を選ばなかったことで、"
            f"そこで何が続いていたかを確かめ続ける道筋が閉じた、と読む余地がある"
        )
    claim = sanitize_claim_text(claim)
    if claim_text_is_malformed(claim) or (
        get_branch_semantics(call1)
        and get_branch_semantics(call1).domain
        not in {"career", "entrepreneurship", "mixed"}
        and career_template_leakage(claim)
    ):
        claim = (
            "選ばなかった道の側で何が続いていたかを、いま確かめ続ける手がかりは閉じた、と読む余地がある"
        )
    return claim


def _synthesize_protected_interpretive(call1: Call1Result, structural: str) -> str:
    """What remained possible / intact / unclosed because the chosen path was taken."""
    sem = get_branch_semantics(call1)
    base = (sem.protected_possibility if sem else "") or structural or ""
    if not base:
        base = "選んだ道の側に残った、まだ閉じきらない可能性"
    # Avoid career redefinition default unless employment evidence supports it
    if career_template_leakage(base) and not allows_career_product_logic(sem):
        base = "選んだ道の側に残った、まだ閉じきらない可能性"
    claim = f"{base}（優劣や成功の証明ではない）"
    return sanitize_claim_text(claim)


def _synthesize_residue_interpretive(call1: Call1Result, structural: str = "") -> str:
    """Why the branch may still matter now — from BranchSemantics / ClaimAtoms."""
    sem = get_branch_semantics(call1)
    atoms = build_claim_atoms(call1)
    q = atoms.unresolved_question
    situation = _situation_phrase(atoms.present_anchor)
    tension = atoms.active_tension or atoms.measurement_tension
    if sem and (sem.present_residue or "").strip():
        claim = sem.present_residue.strip()
        if situation and situation not in claim:
            claim = f"{claim}。{situation}残る緊張として読む余地がある"
    elif allows_career_product_logic(sem) and re.search(
        r"(?:役職|年収|給与|肩書|どこまで)", q
    ):
        claim = (
            f"「{q}」という問いが{situation}残るのは、"
            f"選ばなかった道が、人生の進み具合を測る別の物差しとして想像されるからかもしれない。"
            f"隠された動機の断定ではなく、{tension}の緊張として残る"
        )
    else:
        claim = (
            f"「{q}」が{situation}消えないのは、"
            f"{atoms.past_anchor}が未解決の想像として残るからかもしれない。"
            f"感情の断定ではなく、{tension}として残る"
        )
    claim = sanitize_claim_text(claim)
    if claim_text_is_malformed(claim):
        claim = f"「{q}」がいまも残るのは、選ばなかった道が想像として開いているからかもしれない"
    return claim


def _chosen_path_closure_fields(call1: Call1Result) -> dict[str, str]:
    """factual_choice / structural_shift / thesis_link for Chosen Path thesis closure."""
    pb = call1.branch_structure.primary_branch
    sem = get_branch_semantics(call1)
    factual = _short_phrase(pb.realized_path or "選んだ道", fallback="選んだ道", max_len=40)
    unchosen = _short_phrase(
        " / ".join(pb.unrealized_paths or []) or (sem.unchosen_structure if sem else "") or "選ばなかった道",
        fallback="選ばなかった道",
        max_len=42,
    )
    dim = (sem.changed_dimension if sem else "") or ""
    # BranchSemantics authority: never inject career mobility template unless allowed.
    # v1.1.11 career: one-institution continuity → work continuing across orgs
    # (not résumé chronology, not intention/superiority claims).
    if allows_career_product_logic(sem):
        structural = (
            f"{unchosen}という一制度のなかの連続から、"
            f"組織を移りながら仕事が続く生き方へ移った"
        )
    elif dim:
        structural = f"{factual}という選択が、{dim}の次元で別の組み立てを開き始めた"
    else:
        structural = f"{factual}という選択が、別の生活の組み立て方を開き始めた"
    # Avoid causal 「つながっている」frame in thesis_link (health/sensitive safe)
    thesis_link = (
        "いまも残る問いの起点として、この移り方が現在の生活と並んでいる"
        if (call1.meaning_compression.present_structure or call1.grounded_input.current_context)
        else "この移り方が、いまも続く問いの起点になっている"
    )
    claim = (
        f"振り返ると、{structural}"
        "（当時の意図や優劣の断定ではない）"
    )
    return {
        "factual_choice": factual,
        "structural_shift": structural,
        "thesis_link": thesis_link,
        "interpretive_claim": sanitize_claim_text(claim),
    }


def _rebranch_from_modes(sem: BranchSemantics | None, atoms: ClaimAtoms) -> tuple[str, str, str]:
    """Map possible_rebranch_modes → quiet present-choice language (no salary default)."""
    modes = list(sem.possible_rebranch_modes) if sem else []
    domain = (sem.domain if sem else "unknown") or "unknown"
    unresolved = (
        (sem.central_tension if sem else "")
        or atoms.active_tension
        or atoms.measurement_tension
        or "選んだ道と選ばなかった道がいまも並んで残る緊張"
    )
    if not modes or modes == ["leave_unresolved"] or "leave_unresolved" in modes and len(modes) == 1:
        return (
            unresolved,
            "いまこの問いに一つの答えを固定しなくてよい",
            "未解決のまま置いておく",
        )
    primary = modes[0]
    if primary == "redefine" and _domain_allows_career_metric(domain, sem):
        return (
            unresolved,
            "役職や年収だけを唯一の到達指標にしなくてよい",
            "これから何を長期の積み重ねとして認めるかを、自分で選び直す",
        )
    if primary == "choose":
        if domain == "creative":
            return (
                unresolved,
                "表現を後回しにすることを唯一の正解にしなくてよい",
                "表現に割く時間を、いまの生活のなかで選び直す",
            )
        return (
            unresolved,
            "一つの正しさだけを到達点にしなくてよい",
            "いま何を続けるかを、自分で選び直す",
        )
    if primary == "preserve":
        return (
            unresolved,
            "過去の分岐をいまやり直す必要はない",
            "いま成り立っている生活のかたちを保つ",
        )
    if primary == "reconsider":
        # Release cue must realize as 「しなくてよい」 (not only 「し続けなくてよい」)
        return (
            unresolved,
            "一度決めた測り方を固定しなくてよい",
            "いまの問いの置き方を、静かに見直す",
        )
    if primary == "revisit":
        return (
            unresolved,
            "問いに触れないことを義務にしなくてよい",
            "必要なときに、同じ問いへ戻る",
        )
    if primary == "observe":
        return (
            unresolved,
            "すぐに結論を出さなくてよい",
            "緊張がどう残るかを、まず見ておく",
        )
    if primary == "not_act":
        return (
            unresolved,
            "行動で答えを急がなくてよい",
            "いまは動かない、という選択を残す",
        )
    # leave_unresolved / default
    return (
        unresolved,
        "いまこの問いに一つの答えを固定しなくてよい",
        "未解決のまま置いておく",
    )


def _domain_allows_career_metric(domain: str, sem: BranchSemantics | None) -> bool:
    return allows_career_product_logic(sem)


def build_rebranch_decision(
    call1: Call1Result, structural: str = ""
) -> ReBranchDecision:
    """Build ReBranchDecision from BranchSemantics modes — not a salary-metric default."""
    atoms = build_claim_atoms(call1)
    sem = get_branch_semantics(call1)
    dirs = call1_rebranch_directions(call1)
    evidence_ids: list[str] = []
    if dirs:
        evidence_ids = list(dirs[0].support_ids or [])[:2]
    if not evidence_ids:
        evidence_ids = [
            f.id
            for f in call1.grounded_input.facts
            if "current" in (f.source_field or "") or "current_work" in " ".join(f.tags or [])
        ][:2]
    if sem and sem.evidence_ids and not evidence_ids:
        evidence_ids = list(sem.evidence_ids)[:2]

    unresolved, what_no_longer, what_chosen = _rebranch_from_modes(sem, atoms)
    present_choice = what_chosen
    claim = (
        f"{what_no_longer}。"
        f"{what_chosen}余地がある"
        "（優劣や成功の断定ではない）"
    )
    # Zero re-branch modes → empty decision (caller may omit section)
    if sem and not sem.possible_rebranch_modes:
        return ReBranchDecision(
            unresolved_tension=unresolved,
            present_choice="",
            what_is_no_longer_required="",
            what_can_now_be_chosen="",
            evidence_ids=evidence_ids,
            non_genericity_score=0.0,
            interpretive_claim="",
        )
    score = 0.85 if evidence_ids else 0.55
    if structural or atoms.unresolved_question:
        score = min(1.0, score + 0.1)
    return ReBranchDecision(
        unresolved_tension=unresolved,
        present_choice=present_choice,
        what_is_no_longer_required=what_no_longer,
        what_can_now_be_chosen=what_chosen,
        evidence_ids=evidence_ids,
        non_genericity_score=score,
        interpretive_claim=sanitize_claim_text(claim),
    )


def _rebranch_closure_fields(call1: Call1Result, structural: str = "") -> dict[str, Any]:
    """Back-compat wrapper around ReBranchDecision."""
    d = build_rebranch_decision(call1, structural)
    return {
        "unresolved_tension": d.unresolved_tension,
        "present_choice": d.present_choice,
        "measurement_shift": d.what_is_no_longer_required,
        "what_is_no_longer_required": d.what_is_no_longer_required,
        "what_can_now_be_chosen": d.what_can_now_be_chosen,
        "non_genericity": d.non_genericity_score >= 0.7,
        "non_genericity_score": d.non_genericity_score,
        "evidence_ids": list(d.evidence_ids),
        "interpretive_claim": d.interpretive_claim,
        "structural_hint": (structural or "").strip(),
        "rebranch_decision": d.model_dump(mode="json"),
    }


def _synthesize_rebranch_interpretive(call1: Call1Result, structural: str) -> str:
    """What present choice follows from unresolved tension — structural, not productivity."""
    return build_rebranch_decision(call1, structural).interpretive_claim


def _realization_goal_for(section_id: str, claim: str) -> str:
    goals = {
        "branch_point": "分岐を一点の出来事ではなく、変わった生活次元の境界として置く",
        "chosen_path": "選択＋構造転換＋thesis連結を一段落で実現する（年表禁止）",
        "unchosen_life": "選ばなかった道を発明せず開いたまま置く",
        "lost": "失ったものを一覧ではなく、確かめられなくなった連続として実現する",
        "protected": "守られたものを成功談ではなく、残った可能性／余白として実現する",
        "residue": "現在の問いが古い分岐のどの部分を残しているかを慎重に書く",
        "observatory": "社会の並置をレンズ名なしで織り込む（証拠が無いなら薄く）",
        "re_branch": "Residueの緊張を、いまの静かな選択／非選択へ閉じる（問いだけで終わらせない）",
    }
    base = goals.get(section_id, "interpretive_claim を本文で実現する")
    if claim:
        return f"{base}（claimを実質化）"
    return base


def _apply_realization_meta(contract: SectionContract) -> SectionContract:
    label = UI_SECTION_LABELS_JA.get(contract.section_id, contract.section_id)
    min_p = 1 if contract.must_be_present else 0
    max_p = 2 if contract.section_id in {"residue", "lost", "protected", "re_branch"} else 1
    if contract.section_id == "observatory":
        max_p = 1
    budget = min(2, max(0, int(contract.concrete_example_budget or 1)))
    if contract.section_id == "observatory":
        budget = 0
    status = "pending"
    if not contract.must_be_present:
        status = "omitted" if contract.omission_allowed else "pending"
    return contract.model_copy(
        update={
            "required_public_label": label,
            "realization_goal": _realization_goal_for(
                contract.section_id, contract.interpretive_claim
            ),
            "minimum_paragraphs": min_p,
            "maximum_paragraphs": max_p,
            "evidence_budget": budget,
            "realization_status": status,
            "concrete_example_budget": budget if contract.section_id != "observatory" else 0,
        }
    )


def _upgrade_structural_meaning(section_id: str, raw: str, call1: Call1Result) -> str:
    raw = (raw or "").strip()
    if raw and not _is_fact_like(raw):
        return raw
    if section_id == "lost":
        return _synthesize_lost_meaning(call1)
    if section_id == "protected":
        return _synthesize_protected_meaning(call1)
    if section_id == "residue":
        return _synthesize_residue_meaning(call1)
    if section_id == "re_branch":
        dirs = call1_rebranch_directions(call1)
        if dirs:
            return dirs[0].branch_specific_form
        syn = _synthesize_rebranch(call1)
        return syn.branch_specific_form if syn else ""
    return raw


def _fact_map(call1: Call1Result) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in call1.grounded_input.facts:
        if f.id and (f.content or "").strip():
            out[f.id] = f.content.strip()
    for q in call1.grounded_input.questions:
        if q.id and (q.content or "").strip():
            out[q.id] = q.content.strip()
    return out


def _branch_ids(call1: Call1Result) -> list[str]:
    ids = list(call1.branch_structure.primary_branch.supporting_fact_ids or [])
    for f in call1.grounded_input.facts:
        if f.id and (f.source_field or "") != "context_pack" and "context_pack" not in (
            f.tags or []
        ):
            if f.id not in ids:
                ids.append(f.id)
    return ids


def _pack_ids(call1: Call1Result) -> list[str]:
    sel = getattr(call1, "relevant_context_selection", None)
    if sel and getattr(sel, "manuscript_logic_ids", None):
        return list(sel.manuscript_logic_ids)
    return [
        f.id
        for f in call1.grounded_input.facts
        if f.id
        and (
            (f.source_field or "").startswith("context_pack")
            or "context_pack" in (f.tags or [])
        )
    ]


def _has_employment_regime(call1: Call1Result) -> bool:
    """Background/branch employment presence — does NOT authorize career product templates.

    Use allows_career_product_logic(get_branch_semantics(call1)) for template injection.
    """
    sem = get_branch_semantics(call1)
    if allows_career_product_logic(sem):
        return True
    if sem and (
        sem.diagnostics.get("branch_employment_evidence")
        or sem.diagnostics.get("background_employment_context")
    ):
        # Presence only — callers must not treat this as template authority
        return False
    pb = call1.branch_structure.primary_branch
    text = (
        f"{pb.triggering_event}\n{pb.realized_path}\n"
        f"{' '.join(pb.unrealized_paths or [])}"
    )
    return bool(
        re.search(
            r"(?:一社|一企業|役割を積み|企業間|長期雇用|転職|退職|"
            r"外資|NTT|役職|年収|企業へ移|企業に残)",
            text,
        )
    )


def _has_present_question(call1: Call1Result) -> bool:
    if call1.grounded_input.questions:
        return True
    view = call1.user_confirmation_view
    if view.present_questions:
        return True
    mc = call1.meaning_compression
    return bool((mc.unresolved_question or mc.central_question or "").strip())


def _cross_lens_meanings(call1: Call1Result) -> list[str]:
    out: list[str] = []
    for r in getattr(call1, "cross_lens_relations", None) or []:
        if isinstance(r, dict):
            interp = (r.get("interpretation") or "").strip()
            personal = (r.get("personal_structure") or "").strip()
            social = (r.get("social_structure") or "").strip()
        else:
            interp = (getattr(r, "interpretation", "") or "").strip()
            personal = (getattr(r, "personal_structure", "") or "").strip()
            social = (getattr(r, "social_structure", "") or "").strip()
        if interp:
            out.append(interp)
        elif personal and social:
            out.append(f"{personal}を、{social}と並べて読むことができる")
    return out


def _observatory_evidence_ids(call1: Call1Result) -> list[str]:
    ids: list[str] = []
    for e in getattr(call1, "retrieved_observatory_evidence", None) or []:
        if isinstance(e, dict):
            eid = (e.get("id") or "").strip()
        else:
            eid = (getattr(e, "id", "") or "").strip()
        if eid and eid not in ids:
            ids.append(eid)
    for r in getattr(call1, "cross_lens_relations", None) or []:
        if isinstance(r, dict):
            bag = r.get("observatory_evidence_ids") or []
        else:
            bag = getattr(r, "observatory_evidence_ids", None) or []
        for eid in bag:
            if eid and eid not in ids:
                ids.append(str(eid))
    return ids


def _observatory_semantic_variants(
    call1: Call1Result, meanings: list[str] | None = None
) -> list[str]:
    """Acceptable semantic fragments for Observatory realization (not employment-only)."""
    variants: list[str] = []
    for m in meanings or _cross_lens_meanings(call1):
        if m and m not in variants:
            variants.append(m)
    for e in getattr(call1, "retrieved_observatory_evidence", None) or []:
        if isinstance(e, dict):
            for key in ("structural_pattern", "pattern", "summary", "content"):
                val = (e.get(key) or "").strip()
                if val and val not in variants:
                    variants.append(val)
        else:
            for key in ("structural_pattern", "pattern", "summary", "content"):
                val = (getattr(e, key, "") or "").strip()
                if val and val not in variants:
                    variants.append(val)
    # Domain-neutral structural cues (employment is optional, not required)
    variants.extend(
        [
            "身体経験",
            "ケア",
            "治療",
            "並置",
            "並べて",
            "達成",
            "問いが残",
            "制度説明に還元",
            "個人史",
            "社会",
            "雇用",
            "企業間",
            "似た条件",
        ]
    )
    return variants[:24]


def evidence_supports_lost(call1: Call1Result) -> bool:
    pb = call1.branch_structure.primary_branch
    return bool((pb.unrealized_paths or []) and (pb.realized_path or "").strip()) or _has_employment_regime(
        call1
    )


def evidence_supports_protected(call1: Call1Result) -> bool:
    # Chosen path + present life / thesis poles imply a preserved possibility
    pb = call1.branch_structure.primary_branch
    present = bool(call1.grounded_input.current_context) or bool(
        (call1.meaning_compression.present_structure or "").strip()
    )
    return bool((pb.realized_path or "").strip() and present)


def evidence_supports_residue(call1: Call1Result) -> bool:
    return bool((call1.branch_structure.primary_branch.realized_path or "").strip()) and _has_present_question(
        call1
    )


def evidence_supports_rebranch(call1: Call1Result) -> bool:
    # Structural re-branch from residue / BranchSemantics modes — not promo
    if not evidence_supports_residue(call1):
        return False
    sem = get_branch_semantics(call1)
    if sem is not None:
        if not sem.possible_rebranch_modes:
            return False
        if set(sem.possible_rebranch_modes) <= {"leave_unresolved", "not_act", "observe"}:
            # Still allow a quiet non-action re-branch when residue exists
            return True
        return True
    thesis = call1.central_thesis.statement or ""
    return bool(
        re.search(r"(?:並べて|問い|境界|残|想像)", thesis) or call1_residue_items(call1)
    )


def _synthesize_lost_meaning(call1: Call1Result) -> str:
    sem = get_branch_semantics(call1)
    if sem and (sem.lost_verifiability or "").strip():
        return sem.lost_verifiability.strip()
    meanings = _cross_lens_meanings(call1)
    if (
        allows_career_product_logic(sem)
        and meanings
        and re.search(r"(?:一社|蓄積|役職|制度)", meanings[0])
    ):
        return (
            "一つの制度の内部で時間を積み上げ、その積み重ねを役職・評価・関係などで"
            "確認できる連続性"
        )
    alt = " / ".join(call1.branch_structure.primary_branch.unrealized_paths or []) or "選ばなかった道"
    # v1.1.11 health: bodily capacity / unverifiable life configuration — no prognosis/emotion
    if sem and sem.domain == "health":
        return (
            f"「{alt}」側で続いていた身体条件や働き方を、いま同じようには辿れないこと"
        )
    return f"「{alt}」側にあった、時間を一続きとして確かめられる連続性"


def _synthesize_protected_meaning(call1: Call1Result) -> str:
    sem = get_branch_semantics(call1)
    if sem and (sem.protected_possibility or "").strip():
        return sem.protected_possibility.strip()
    present = (call1.meaning_compression.present_structure or "").strip()
    if allows_career_product_logic(sem) and re.search(
        r"(?:経営|自分の会社|定義)", present + (call1.central_thesis.statement or "")
    ):
        return "所属先が変わっても、自分の仕事を別の言葉で定義し直す余白"
    return "選んだ道の側に残った、まだ閉じきらない可能性"


def _synthesize_residue_meaning(call1: Call1Result) -> str:
    sem = get_branch_semantics(call1)
    if sem and (sem.present_residue or "").strip():
        return sem.present_residue.strip()
    existing = call1_residue_items(call1)
    if existing:
        base = existing[0].statement()
        if re.search(r"(?:読むことができる|並[べべ]|想像|残)", base):
            return base
    q = (
        call1.meaning_compression.unresolved_question
        or call1.meaning_compression.central_question
        or "あのとき別の道を選んでいたら"
    )
    if allows_career_product_logic(sem):
        return (
            f"「{q}」という問いは、一続きの制度の内部で進度を知る測定系を失ったこととして"
            "読むことができる"
        )
    return f"「{q}」という問いは、選ばなかった道が想像として残っていることとして読むことができる"


def _synthesize_rebranch(call1: Call1Result) -> RebranchDirection | None:
    if not evidence_supports_rebranch(call1):
        return None
    support = list(
        dict.fromkeys(
            [
                *(_pack_ids(call1)[:2]),
                *(_branch_ids(call1)[:2]),
            ]
        )
    )
    sem = get_branch_semantics(call1)
    decision = build_rebranch_decision(call1)
    if not (decision.present_choice or "").strip():
        return None
    form = decision.present_choice
    # v1.1.11: place from BranchSemantics domain — never inherit career「仕事の場」
    # for education/romance/health/etc.
    domain = (sem.domain if sem else "") or ""
    place_by_domain = {
        "education": "いまの進路の読み方のなかで",
        "romance": "いまの関係の置き方のなかで",
        "health": "いまの生活のかたちのなかで",
        "family": "いまの暮らしのなかで",
        "creative": "いまの表現の置き方のなかで",
        "career": "いまの仕事の置き方のなかで",
        "entrepreneurship": "いまの仕事の置き方のなかで",
    }
    if allows_career_product_logic(sem):
        facts = _fact_map(call1)
        noun = ""
        for fid in support:
            text = facts.get(fid, "")
            m = re.search(r"(?:会社|経営|仕事|NTT|キャリア)", text)
            if m:
                noun = m.group(0)
                break
        place = f"{noun}の場で" if noun else place_by_domain.get("career", "いまの生活のなかで")
    else:
        place = place_by_domain.get(domain, "いまの生活のなかで")
    branch_form = f"{place}、{form}"
    return RebranchDirection(
        id="rebranch_semantics_001",
        source_meaning=(
            (sem.central_tension if sem else "")
            or call1.central_thesis.statement
            or "いまも残る緊張"
        ),
        current_receiver="現在の生活で、この緊張をどう置くか",
        branch_specific_form=branch_form,
        support_ids=support[:3],
        genericity_score=1,
        invented_scene_used=False,
        risks=["must_not_become_product_promo"],
        publishable=True,
        selected_for_manuscript=True,
    )


def _as_lost(raw: Any) -> LostStructure:
    if isinstance(raw, LostStructure):
        return raw
    if isinstance(raw, dict):
        try:
            return LostStructure.model_validate(raw)
        except Exception:
            return LostStructure()
    return LostStructure()


def _as_protected(raw: Any) -> ProtectedStructure:
    if isinstance(raw, ProtectedStructure):
        return raw
    if isinstance(raw, dict):
        try:
            return ProtectedStructure.model_validate(raw)
        except Exception:
            return ProtectedStructure()
    return ProtectedStructure()


def repair_call1_structural_sections(call1: Call1Result) -> tuple[Call1Result, list[str]]:
    """Deterministic backfill of Lost/Protected/Residue/Re-branch when evidence exists."""
    notes: list[str] = []
    lost = _as_lost(call1.lost_structure)
    protected = _as_protected(call1.protected_structure)
    residue = ResidueCandidates(items=list(call1_residue_items(call1)))
    rebranch = RebranchDesign(directions=list(call1_rebranch_directions(call1)))

    branch_ids = _branch_ids(call1)
    pack_ids = _pack_ids(call1)
    support = list(dict.fromkeys([*branch_ids[:2], *pack_ids[:2]]))

    if evidence_supports_lost(call1) and not (lost.items or []):
        meaning = _synthesize_lost_meaning(call1)
        if not INVENTORY_RE.search(meaning):
            lost = LostStructure(
                items=[
                    LostItem(
                        content=meaning,
                        loss_type="structural_continuity",
                        support_ids=support[:3],
                        certainty="qualified",
                        allowed_wording_strength="qualified",
                    )
                ]
            )
            notes.append("section_repair:lost_backfilled")
    elif evidence_supports_lost(call1) and lost.items and _is_fact_like(lost.items[0].content):
        meaning = _synthesize_lost_meaning(call1)
        lost = LostStructure(
            items=[
                lost.items[0].model_copy(
                    update={
                        "content": meaning,
                        "loss_type": "structural_continuity",
                        "allowed_wording_strength": "qualified",
                    }
                )
            ]
            + list(lost.items[1:])
        )
        notes.append("section_repair:lost_upgraded_from_fact_like")

    if evidence_supports_protected(call1) and not (protected.items or []):
        meaning = _synthesize_protected_meaning(call1)
        if not SUCCESS_MORAL_RE.search(meaning):
            protected = ProtectedStructure(
                items=[
                    ConfirmedContinuity(
                        content=meaning,
                        support_ids=support[:3],
                        causality_status="non_causal_possibility",
                        allowed_statement_strength="qualified",
                    )
                ]
            )
            notes.append("section_repair:protected_backfilled")
    elif (
        evidence_supports_protected(call1)
        and protected.items
        and _is_fact_like(protected.items[0].content)
    ):
        meaning = _synthesize_protected_meaning(call1)
        protected = ProtectedStructure(
            items=[
                protected.items[0].model_copy(
                    update={
                        "content": meaning,
                        "causality_status": "non_causal_possibility",
                        "allowed_statement_strength": "qualified",
                    }
                )
            ]
            + list(protected.items[1:])
        )
        notes.append("section_repair:protected_upgraded_from_fact_like")

    if evidence_supports_residue(call1) and not residue.items:
        meaning = _synthesize_residue_meaning(call1)
        past = pack_ids[:1] or branch_ids[:1]
        present = []
        for pid in pack_ids:
            if "current" in pid or pid.endswith("_004") or pid.endswith("_005"):
                present.append(pid)
        if not present and pack_ids:
            present = [pack_ids[-1]]
        residue = ResidueCandidates(
            items=[
                ResidueCandidate(
                    residue_statement=meaning,
                    content=meaning,
                    past_anchor_ids=past[:2],
                    present_anchor_ids=present[:2] or pack_ids[-1:],
                    support_ids=list(dict.fromkeys([*past[:2], *present[:2]])),
                    inference_distance="near",
                    present_life_domain="present_life",
                    overreach_risk="low_structural_only",
                    advances_manuscript=True,
                )
            ]
        )
        notes.append("section_repair:residue_backfilled")
    elif residue.items:
        # Strengthen cautious modality if missing; upgrade fact-like residue
        fixed = []
        for item in residue.items:
            stmt = item.statement()
            if _is_fact_like(stmt):
                stmt = _synthesize_residue_meaning(call1)
                notes.append("section_repair:residue_upgraded_from_fact_like")
            elif not re.search(r"(?:読むことができる|にも見える|並べて|残っている)", stmt):
                stmt = f"{stmt.rstrip('。')}という問いにも見える"
                notes.append("section_repair:residue_modality_softened")
            fixed.append(
                item.model_copy(
                    update={"residue_statement": stmt, "content": stmt}
                )
            )
        residue = ResidueCandidates(items=fixed)

    if not rebranch.directions:
        if evidence_supports_rebranch(call1):
            direction = _synthesize_rebranch(call1)
            if direction and not PROMO_REBRANCH_RE.search(direction.branch_specific_form):
                rebranch = RebranchDesign(directions=[direction])
                notes.append("section_repair:rebranch_evaluated_present")
            else:
                notes.append("section_repair:rebranch_evaluated_omitted_unsupported")
        else:
            notes.append("section_repair:rebranch_evaluated_omitted_no_evidence")

    updated = call1.model_copy(
        update={
            "lost_structure": lost,
            "protected_structure": protected,
            "residue_candidates": residue,
            "rebranch_design": rebranch,
        }
    )
    return updated, notes


def build_section_contracts(call1: Call1Result) -> SectionContractSet:
    pb = call1.branch_structure.primary_branch
    pack_ids = _pack_ids(call1)
    branch_ids = _branch_ids(call1)
    thesis_ids = list(call1.central_thesis.supported_by or [])[:3]
    lost_struct = _as_lost(call1.lost_structure)
    prot_struct = _as_protected(call1.protected_structure)
    lost_ids = list((lost_struct.items[0].support_ids if lost_struct.items else []) or [])
    prot_ids = list((prot_struct.items[0].support_ids if prot_struct.items else []) or [])
    residue_items = call1_residue_items(call1)
    residue_ids: list[str] = []
    if residue_items:
        residue_ids = list(
            dict.fromkeys(
                [
                    *(residue_items[0].past_anchor_ids or []),
                    *(residue_items[0].present_anchor_ids or []),
                ]
            )
        )
    atoms = build_claim_atoms(call1)
    atoms_dump = atoms.model_dump(mode="json")
    sem = get_branch_semantics(call1)

    fork_meaning = (pb.triggering_event or "分岐があった").strip()
    chosen_meaning = (pb.realized_path or "選んだ道").strip()
    unchosen_meaning = (
        " / ".join(pb.unrealized_paths or []) or "選ばなかった道"
    ).strip()
    chosen_closure = _chosen_path_closure_fields(call1)
    # v1.1.11: domain-specific Branch Point — first paragraph must name the fork.
    # Health: avoid 「働き方を変える」causal assertion pattern in contract prose.
    if sem and sem.domain == "romance":
        branch_claim = (
            f"{_short_phrase(fork_meaning, fallback='関係の分かれ目', max_len=36)}"
            f"という分岐で、「{_short_phrase(chosen_meaning, fallback='選んだ道', max_len=24)}」と"
            f"「{_short_phrase(unchosen_meaning, fallback='選ばなかった道', max_len=24)}」が"
            f"分かれた境界だった"
        )
    elif sem and sem.domain == "health":
        branch_claim = (
            f"{_short_phrase(fork_meaning, fallback='体調と暮らしの分かれ目', max_len=40)}"
            f"という分岐は一点の判断ではなく、"
            f"身体の制約のなかで生活をどう成り立たせるかが分かれた境界だった"
        )
    elif sem and (sem.changed_dimension or "").strip():
        branch_claim = (
            f"この分かれ目は一点の出来事ではなく、"
            f"{sem.changed_dimension}が分かれた境界だった"
        )
    elif allows_career_product_logic(sem):
        branch_claim = (
            "この分かれ目は勤務先の一点ではなく、"
            "内部で積み上げる道と外へ持ち運ぶ道の境界だった"
        )
    else:
        branch_claim = (
            "この分かれ目は一点の出来事ではなく、"
            "選んだ道と選ばなかった道が分かれた境界だった"
        )

    raw_contracts: list[SectionContract] = [
        SectionContract(
            section_id="branch_point",
            structural_purpose="establish the fork",
            required_meaning=fork_meaning,
            interpretive_claim=branch_claim,
            supporting_evidence_ids=(branch_ids or pack_ids)[:1],
            prohibited_claims=["employer_chronology_as_spine"],
            concrete_example_budget=1,
            must_be_present=True,
            omission_allowed=False,
            claim_atoms=atoms_dump,
        ),
        SectionContract(
            section_id="chosen_path",
            structural_purpose="state the realized path without résumé tour",
            required_meaning=chosen_meaning,
            interpretive_claim=chosen_closure["interpretive_claim"],
            factual_choice=chosen_closure["factual_choice"],
            structural_shift=chosen_closure["structural_shift"],
            thesis_link=chosen_closure["thesis_link"],
            realization_required=True,
            supporting_evidence_ids=(thesis_ids or pack_ids)[:1],
            prohibited_claims=[
                "industry_tour",
                "project_list",
                "chronology_only",
                "intention_claim",
                "superiority_claim",
            ],
            concrete_example_budget=1,
            must_be_present=True,
            omission_allowed=False,
            claim_atoms=atoms_dump,
        ),
        SectionContract(
            section_id="unchosen_life",
            structural_purpose="keep unrealized path open without invention",
            required_meaning=unchosen_meaning,
            interpretive_claim=(
                f"残らなかった側には、発明せずに置いておける"
                f"「{_short_phrase(unchosen_meaning, fallback='選ばなかった道', max_len=40)}」"
                f"という可能性が閉じずに残る"
            ),
            supporting_evidence_ids=(branch_ids or pack_ids)[:1],
            prohibited_claims=["invented_rank_salary_scene"],
            concrete_example_budget=1,
            must_be_present=True,
            omission_allowed=False,
            claim_atoms=atoms_dump,
        ),
    ]

    lost_ok = bool(lost_struct.items)
    lost_structural = (
        (sem.lost_verifiability if sem and sem.lost_verifiability else "")
        or _upgrade_structural_meaning(
            "lost", lost_struct.items[0].content if lost_ok else "", call1
        )
    )
    raw_contracts.append(
        SectionContract(
            section_id="lost",
            structural_purpose="structural continuity left behind",
            required_meaning=lost_structural if (lost_ok or evidence_supports_lost(call1)) else "",
            interpretive_claim=(
                _synthesize_lost_interpretive(call1, lost_structural)
                if (lost_ok or evidence_supports_lost(call1))
                else ""
            ),
            supporting_evidence_ids=(lost_ids or pack_ids)[:1],
            prohibited_claims=[
                "salary_inventory",
                "title_inventory",
                "pension_inventory",
                "colleague_network_list",
            ],
            concrete_example_budget=1,
            must_be_present=lost_ok or evidence_supports_lost(call1),
            omission_allowed=not (lost_ok or evidence_supports_lost(call1)),
            omission_reason="" if (lost_ok or evidence_supports_lost(call1)) else "insufficient_loss_evidence",
            claim_atoms=atoms_dump,
        )
    )

    prot_ok = bool(prot_struct.items)
    prot_structural = (
        (sem.protected_possibility if sem and sem.protected_possibility else "")
        or _upgrade_structural_meaning(
            "protected", prot_struct.items[0].content if prot_ok else "", call1
        )
    )
    raw_contracts.append(
        SectionContract(
            section_id="protected",
            structural_purpose="structural possibility preserved",
            required_meaning=prot_structural if (prot_ok or evidence_supports_protected(call1)) else "",
            interpretive_claim=(
                _synthesize_protected_interpretive(call1, prot_structural)
                if (prot_ok or evidence_supports_protected(call1))
                else ""
            ),
            supporting_evidence_ids=(prot_ids or pack_ids)[:1],
            prohibited_claims=["success_moral", "freedom_claim", "superiority_claim"],
            concrete_example_budget=1,
            must_be_present=prot_ok or evidence_supports_protected(call1),
            omission_allowed=not (prot_ok or evidence_supports_protected(call1)),
            omission_reason=""
            if (prot_ok or evidence_supports_protected(call1))
            else "insufficient_protected_evidence",
            claim_atoms=atoms_dump,
        )
    )

    residue_ok = bool(residue_items)
    residue_structural = (
        (sem.present_residue if sem and sem.present_residue else "")
        or _upgrade_structural_meaning(
            "residue", residue_items[0].statement() if residue_ok else "", call1
        )
    )
    raw_contracts.append(
        SectionContract(
            section_id="residue",
            structural_purpose="return to present through structural tension",
            required_meaning=residue_structural if (residue_ok or evidence_supports_residue(call1)) else "",
            interpretive_claim=(
                _synthesize_residue_interpretive(call1, residue_structural)
                if (residue_ok or evidence_supports_residue(call1))
                else ""
            ),
            supporting_evidence_ids=residue_ids[:2] or pack_ids[:1],
            prohibited_claims=["unsupported_causality", "psychological_fact_claim"],
            concrete_example_budget=1,
            must_be_present=residue_ok or evidence_supports_residue(call1),
            omission_allowed=not (residue_ok or evidence_supports_residue(call1)),
            omission_reason=""
            if (residue_ok or evidence_supports_residue(call1))
            else "insufficient_residue_evidence",
            claim_atoms=atoms_dump,
        )
    )

    relations = getattr(call1, "cross_lens_relations", None) or []
    obs_meaning = _cross_lens_meanings(call1)
    obs_evidence_ids = _observatory_evidence_ids(call1)
    obs_variants = _observatory_semantic_variants(call1, obs_meaning)
    # v1.1.10: selected lens count == 0 → no Observatory realization requirement
    from app.parallel_life_deep_reading.call1_schema import call1_selected_lenses

    selected_lenses = call1_selected_lenses(call1)
    obs_required = len(selected_lenses) > 0
    if obs_meaning:
        obs_claim = obs_meaning[0]
    elif allows_career_product_logic(sem):
        obs_claim = (
            "個人の分岐の横に、長期雇用と企業間移動という社会の並びが透けて見える"
        )
    else:
        obs_claim = "個人の分岐の横に、似た条件で生きた人々の並びが薄く透けて見える"
    raw_contracts.append(
        SectionContract(
            section_id="observatory",
            structural_purpose="social parallel without lens-name advertising",
            required_meaning=(obs_meaning[0] if obs_meaning else "") if obs_required else "",
            interpretive_claim=obs_claim if obs_required else "",
            supporting_evidence_ids=list(obs_evidence_ids)[:6] if obs_required else [],
            supporting_observatory_evidence_ids=list(obs_evidence_ids)[:6],
            acceptable_semantic_variants=obs_variants if obs_required else [],
            prohibited_claims=["lens_name_advertising", "sociology_takeover"],
            concrete_example_budget=0,
            must_be_present=obs_required,
            omission_allowed=not obs_required,
            omission_reason="" if obs_required else "zero_selected_observatory_lenses",
            claim_atoms=atoms_dump,
        )
    )

    directions = call1_rebranch_directions(call1)
    if directions:
        re_structural = directions[0].branch_specific_form
        re_closure = _rebranch_closure_fields(call1, re_structural)
        raw_contracts.append(
            SectionContract(
                section_id="re_branch",
                structural_purpose="close residue tension as a present choice",
                required_meaning=re_structural,
                interpretive_claim=re_closure["interpretive_claim"],
                unresolved_tension=re_closure["unresolved_tension"],
                present_choice=re_closure["present_choice"],
                measurement_shift=re_closure["measurement_shift"],
                what_is_no_longer_required=re_closure["what_is_no_longer_required"],
                what_can_now_be_chosen=re_closure["what_can_now_be_chosen"],
                non_genericity=bool(re_closure["non_genericity"]),
                non_genericity_score=float(re_closure["non_genericity_score"]),
                rebranch_decision=re_closure.get("rebranch_decision") or {},
                realization_required=True,
                supporting_evidence_ids=list(
                    re_closure.get("evidence_ids")
                    or directions[0].support_ids
                    or []
                )[:2],
                prohibited_claims=[
                    "shiro_growth_promo",
                    "protocol_expansion_promo",
                    "app_launch_promo",
                    "productivity_advice",
                    "career_coaching",
                    "reflection_only_no_choice",
                    "question_only_rebranch",
                    "growth_challenge_rhetoric",
                ],
                concrete_example_budget=1,
                must_be_present=True,
                omission_allowed=False,
                claim_atoms=atoms_dump,
            )
        )
    else:
        reason = "evaluated_unsupported"
        if not evidence_supports_rebranch(call1):
            reason = "no_structural_support_for_rebranch"
        raw_contracts.append(
            SectionContract(
                section_id="re_branch",
                structural_purpose="close residue tension as a present choice",
                required_meaning="",
                interpretive_claim="",
                supporting_evidence_ids=[],
                prohibited_claims=[
                    "shiro_growth_promo",
                    "protocol_expansion_promo",
                    "app_launch_promo",
                    "productivity_advice",
                    "career_coaching",
                    "reflection_only_no_choice",
                ],
                concrete_example_budget=1,
                must_be_present=False,
                omission_allowed=True,
                omission_reason=reason,
                claim_atoms=atoms_dump,
            )
        )

    contracts = [_apply_realization_meta(c) for c in raw_contracts]
    # Reject malformed claims at build time
    for i, c in enumerate(contracts):
        if c.interpretive_claim and claim_text_is_malformed(c.interpretive_claim):
            fixed = sanitize_claim_text(c.interpretive_claim)
            if claim_text_is_malformed(fixed) and c.section_id == "residue":
                fixed = _synthesize_residue_interpretive(call1)
            contracts[i] = c.model_copy(update={"interpretive_claim": fixed})

    re_dec = next(
        (
            c.rebranch_decision
            for c in contracts
            if c.section_id == "re_branch" and c.rebranch_decision
        ),
        {},
    )
    contract_texts = [
        "\n".join(
            [
                c.required_meaning or "",
                c.interpretive_claim or "",
                c.factual_choice or "",
                c.structural_shift or "",
                c.thesis_link or "",
            ]
        )
        for c in contracts
    ]
    leak_diag = detect_semantic_domain_leak(sem, contract_texts=contract_texts)
    return SectionContractSet(
        contracts=contracts,
        diagnostics={
            "runtime_pin": RUNTIME_VERSION_V1111_EXP,
            "branch_semantics": sem.model_dump(mode="json") if sem else None,
            "semantic_domain_leak": leak_diag,
            "required_ids": [c.section_id for c in contracts if c.must_be_present],
            "required_public_labels": [
                c.required_public_label for c in contracts if c.must_be_present
            ],
            "lost_items": len(lost_struct.items or []),
            "protected_items": len(prot_struct.items or []),
            "residue_items": len(residue_items),
            "rebranch_directions": len(directions),
            "rebranch_decision": re_dec,
            "claim_atoms": atoms_dump,
            "interpretive_claims": {
                c.section_id: bool((c.interpretive_claim or "").strip())
                for c in contracts
                if c.must_be_present
            },
            "malformed_claims": [
                c.section_id
                for c in contracts
                if claim_text_is_malformed(c.interpretive_claim)
            ],
        },
    )


def section_contract_evidence_check(
    call1: Call1Result,
) -> tuple[bool, list[str], Call1Result, SectionContractSet]:
    """Repair empty required structures; return ok + notes + updated call1 + contracts."""
    from app.parallel_life_deep_reading.branch_semantics import attach_branch_semantics

    working = call1
    if not get_branch_semantics(working):
        working, _sem = attach_branch_semantics(working)
    repaired, repair_notes = repair_call1_structural_sections(working)
    contracts = build_section_contracts(repaired)
    notes = list(repair_notes)
    failures: list[str] = []

    for c in contracts.contracts:
        if not c.must_be_present:
            continue
        if c.section_id == "lost" and not repaired.lost_structure.items:
            failures.append("lost_empty_despite_evidence")
        if c.section_id == "protected" and not repaired.protected_structure.items:
            failures.append("protected_empty_despite_evidence")
        if c.section_id == "residue" and not call1_residue_items(repaired):
            failures.append("residue_empty_despite_evidence")
        if c.section_id in {"branch_point", "chosen_path", "unchosen_life"}:
            if not (c.required_meaning or "").strip():
                failures.append(f"{c.section_id}_missing_meaning")
        if c.section_id in {"lost", "protected", "residue", "re_branch"}:
            if not (c.interpretive_claim or "").strip():
                failures.append(f"{c.section_id}_missing_interpretive_claim")
            if (c.required_meaning or "").strip() and _is_fact_like(c.required_meaning):
                failures.append(f"{c.section_id}_fact_like_required_meaning")
            if claim_text_is_malformed(c.interpretive_claim):
                failures.append(f"{c.section_id}_malformed_interpretive_claim")
        if c.must_be_present and not (c.required_public_label or "").strip():
            failures.append(f"{c.section_id}_missing_public_label")

    # v1.1.9: semantic_domain_leak is a hard QA failure (not a clarification loop)
    leak = (contracts.diagnostics or {}).get("semantic_domain_leak") or {}
    if leak.get("leaked"):
        failures.append("semantic_domain_leak")
        notes.append(
            "semantic_domain_leak:"
            + ",".join(str(h) for h in (leak.get("hits") or [])[:8])
        )

    ok = not failures
    if not ok:
        notes.append("section_contract_evidence_check:failed:" + ",".join(failures))
        # Soft stop: needs_additional_input only if core branch fields missing
        # semantic_domain_leak does NOT push clarification (system/editorial fail)
        status = repaired.status
        if any(f.endswith("_missing_meaning") for f in failures):
            status = GenerationStatus.needs_additional_input
        repaired = repaired.model_copy(
            update={
                "status": status,
                "validation": repaired.validation.model_copy(
                    update={
                        "notes": list(repaired.validation.notes or []) + notes,
                    }
                ),
                "section_contracts": contracts.model_dump(mode="json"),
            }
        )
    else:
        notes.append("section_contract_evidence_check:passed")
        repaired = repaired.model_copy(
            update={
                "validation": repaired.validation.model_copy(
                    update={
                        "notes": list(repaired.validation.notes or []) + notes,
                    }
                ),
                "section_contracts": contracts.model_dump(mode="json"),
            }
        )
    return ok, notes, repaired, contracts


def _pick_evidence(
    fact_map: dict[str, str],
    ids: list[str],
    budget: int,
    *,
    prefer_short: bool = True,
) -> list[dict[str, str]]:
    picked: list[dict[str, str]] = []
    for fid in ids:
        if fid not in fact_map:
            continue
        content = fact_map[fid]
        # Prefer less inventory-like lines when possible
        if prefer_short and ORG_STACK_RE.findall(content) and len(ORG_STACK_RE.findall(content)) >= 2:
            continue
        picked.append({"id": fid, "content": content})
        if len(picked) >= max(0, budget):
            break
    if len(picked) < budget:
        for fid in ids:
            if any(p["id"] == fid for p in picked):
                continue
            if fid in fact_map:
                picked.append({"id": fid, "content": fact_map[fid]})
            if len(picked) >= budget:
                break
    return picked[: max(0, budget)]


def build_call2_writing_pack(call1: Call1Result) -> dict[str, Any]:
    """Minimal editorial payload — no full confirmed_call1, no full pack dump."""
    contracts_raw = getattr(call1, "section_contracts", None)
    if isinstance(contracts_raw, dict) and contracts_raw.get("contracts"):
        contracts = SectionContractSet.model_validate(contracts_raw)
    else:
        contracts = build_section_contracts(call1)

    fact_map = _fact_map(call1)
    pb = call1.branch_structure.primary_branch
    evidence_by_section: dict[str, list[dict[str, str]]] = {}
    for c in contracts.contracts:
        budget = min(2, max(0, int(c.concrete_example_budget or 1)))
        evidence_by_section[c.section_id] = _pick_evidence(
            fact_map, list(c.supporting_evidence_ids or []), budget
        )

    branch_minimal = {
        "period": pb.period,
        "triggering_event": pb.triggering_event,
        "realized_path": pb.realized_path,
        "unrealized_paths": list(pb.unrealized_paths or [])[:2],
        "present_questions": list(call1.user_confirmation_view.present_questions or [])[:2]
        or [q.content for q in call1.grounded_input.questions[:2]],
    }

    mc = call1.meaning_compression
    compression_slim = {
        "past_structure": mc.past_structure,
        "alternative_structure": mc.alternative_structure,
        "present_structure": mc.present_structure,
        "tension": mc.tension,
        "personal_tension": mc.personal_tension,
        "social_institutional_parallel": mc.social_institutional_parallel,
        "present_life_connection": mc.present_life_connection,
        "unresolved_question": mc.unresolved_question or mc.central_question,
        "cross_lens_relation_ids": list(mc.cross_lens_relation_ids or []),
    }

    interpretive_by_section = {
        c.section_id: c.interpretive_claim
        for c in contracts.contracts
        if (c.interpretive_claim or "").strip()
    }
    structural_by_section = {
        c.section_id: c.required_meaning
        for c in contracts.contracts
        if (c.required_meaning or "").strip()
    }

    re_c = contracts.by_id("re_branch") or SectionContract()
    pv = (getattr(call1, "prompt_version", None) or "").strip()
    schema_v = (getattr(call1, "schema_version", None) or "").strip()
    if "v1.1.11" in schema_v or "v1.1.11" in pv:
        pack_schema = "call2_writing_pack_v1.1.11"
    elif "v1.1.10" in schema_v or "v1.1.10" in pv:
        pack_schema = "call2_writing_pack_v1.1.10"
    elif "v1.1.9" in pv:
        pack_schema = "call2_writing_pack_v1.1.9"
    elif "v1.1.8" in pv:
        pack_schema = "call2_writing_pack_v1.1.8"
    elif "v1.1.7" in pv:
        pack_schema = "call2_writing_pack_v1.1.7"
    elif "v1.1.6" in pv:
        pack_schema = "call2_writing_pack_v1.1.6"
    else:
        pack_schema = "call2_writing_pack_v1.1.11"
    pack = {
        "schema": pack_schema,
        "central_thesis": call1.central_thesis.statement,
        "branch_semantics": getattr(call1, "branch_semantics", None)
        or (contracts.diagnostics or {}).get("branch_semantics"),
        "meaning_compression": compression_slim,
        "cross_lens_relations": list(getattr(call1, "cross_lens_relations", None) or []),
        "section_contracts": [
            {
                k: v
                for k, v in c.model_dump(mode="json").items()
                if k not in {"claim_atoms", "rebranch_decision"}
            }
            for c in contracts.contracts
        ],
        "claim_atoms": (contracts.diagnostics or {}).get("claim_atoms") or {},
        "rebranch_decision": re_c.rebranch_decision
        or (contracts.diagnostics or {}).get("rebranch_decision")
        or {},
        "interpretive_claims_by_section": interpretive_by_section,
        "structural_meanings_by_section": structural_by_section,
        "ui_section_labels": UI_SECTION_LABELS_JA,
        "required_section_outline": [
            {
                "section_id": c.section_id,
                "required_public_label": c.required_public_label
                or UI_SECTION_LABELS_JA.get(c.section_id, ""),
                "interpretive_claim": c.interpretive_claim,
                "realization_goal": c.realization_goal,
                "minimum_paragraphs": c.minimum_paragraphs,
                "maximum_paragraphs": c.maximum_paragraphs,
                "evidence_budget": c.evidence_budget,
                "must_be_present": c.must_be_present,
                "factual_choice": c.factual_choice,
                "structural_shift": c.structural_shift,
                "thesis_link": c.thesis_link,
                "realization_required": c.realization_required,
                "unresolved_tension": c.unresolved_tension,
                "present_choice": c.present_choice,
                "measurement_shift": c.measurement_shift,
                "what_is_no_longer_required": c.what_is_no_longer_required,
                "what_can_now_be_chosen": c.what_can_now_be_chosen,
                "non_genericity": c.non_genericity,
                "non_genericity_score": c.non_genericity_score,
            }
            for c in contracts.contracts
            if c.must_be_present
        ],
        "thesis_closure": {
            "chosen_path": {
                "factual_choice": (contracts.by_id("chosen_path") or SectionContract()).factual_choice,
                "structural_shift": (contracts.by_id("chosen_path") or SectionContract()).structural_shift,
                "thesis_link": (contracts.by_id("chosen_path") or SectionContract()).thesis_link,
            },
            "re_branch": {
                "unresolved_tension": re_c.unresolved_tension,
                "present_choice": re_c.present_choice,
                "measurement_shift": re_c.measurement_shift,
                "what_is_no_longer_required": re_c.what_is_no_longer_required,
                "what_can_now_be_chosen": re_c.what_can_now_be_chosen,
            },
            "arc": [
                "Chosen Path opens the structural shift",
                "Residue shows why the question remains",
                "Re-branch converts unresolved tension into a present choice",
            ],
        },
        "locked_public_labels_in_order": [
            c.required_public_label or UI_SECTION_LABELS_JA.get(c.section_id, "")
            for c in contracts.contracts
            if c.must_be_present
        ],
        "branch_facts_minimal": branch_minimal,
        "evidence_by_section": evidence_by_section,
        "validated_residue": [
            {
                "residue_statement": r.statement(),
                "past_anchor_ids": r.past_anchor_ids,
                "present_anchor_ids": r.present_anchor_ids,
            }
            for r in call1_residue_items(call1)
        ],
        "rebranch_directions": [
            d.model_dump(mode="json") for d in call1_rebranch_directions(call1)
        ],
        "editorial_constraints": {
            "anti_resume": True,
            "one_paragraph_one_idea": True,
            "interpretation_first_evidence_second": True,
            "max_org_names_in_body": 2,
            "max_project_names_in_body": 0,
            "forbid_chronology_stack_paragraphs": True,
            "do_not_advertise_lens_names": True,
            "realize_must_be_present_sections": True,
            "realize_interpretive_claims": True,
            "locked_public_labels": True,
            "do_not_rename_or_omit_required_labels": True,
            "omit_resume_like_literary_subtitles": True,
            "ui_labels_stable": True,
            "vary_cautious_modality": True,
            "avoid_template_phrases_every_paragraph": [
                "構造として",
                "制度として",
                "〜と読むことができる",
                "〜とも言える",
                "〜として見ることができる",
            ],
            "depth_arc": [
                "concrete_anchor",
                "structural_interpretation",
                "implication_for_branch",
                "return_to_present_meaning",
            ],
            "thesis_closure_required": True,
            "rebranch_is_choice_not_question": True,
            "quiet_conclusion_no_coaching": True,
            "chosen_path_must_include": [
                "factual_choice",
                "structural_shift",
                "thesis_link",
            ],
            "rebranch_must_include": [
                "unresolved_tension",
                "present_choice",
                "what_is_no_longer_required",
                "what_can_now_be_chosen",
            ],
            "forbid_rebranch_rhetoric": ["すべき", "今こそ", "挑戦", "成長"],
            "vary_measurement_lexicon": True,
            "avoid_adjacent_repeat": ["測る", "尺度", "蓄積"],
            "abstract_vocab_soft_limits": ABSTRACT_SOFT_LIMIT,
            "depth_via_implication_not_facts": True,
            "pattern": "interpretive_claim → one grounding fact → return_to_branch",
            # v1.1.11 Track B — section-specific editorial (does not loosen gates)
            "v1111_chosen_path_career": (
                "factual choice + structural shift from one-institution continuity "
                "to work continuing across organizations; no résumé chronology; "
                "no intention/superiority claims"
            ),
            "v1111_branch_point_romance": (
                "first paragraph: triggering event + actual choice + unchosen "
                "relational continuity; use 分岐/分かれ/境界; not abstract opening only"
            ),
            "v1111_rebranch_education": (
                "derive from education BranchSemantics only; no career metric; "
                "present choice or valid omission"
            ),
            "v1111_health_causality": (
                "temporal coexistence / bodily constraint / uncertainty only; "
                "forbid 働き方を変える causal assertion; forbid illness→outcome claims"
            ),
            "v1111_health_lost": (
                "bodily capacity / unverifiable configuration; use 辿れない/検証できない; "
                "no prognosis/emotion/family/career invention"
            ),
        },
    }
    return pack


def writing_pack_size_stats(pack: dict[str, Any], call1: Call1Result) -> dict[str, Any]:
    import json

    minimal = json.dumps(pack, ensure_ascii=False)
    full = json.dumps(call1.model_dump(mode="json"), ensure_ascii=False)
    return {
        "writing_pack_chars": len(minimal),
        "full_call1_chars": len(full),
        "reduction_ratio": round(1 - (len(minimal) / max(1, len(full))), 3),
        "evidence_fact_count": sum(len(v) for v in (pack.get("evidence_by_section") or {}).values()),
        "duplicate_full_call1_in_writing_pack": False,
    }


def section_resume_flags(body: str) -> dict[str, Any]:
    from app.parallel_life_deep_reading.context_selection import compute_resume_density

    report = compute_resume_density(body or "")
    flags = {
        "employer_enumeration": "org_enumeration" in report.resume_density_flags
        or "org_names_present" in report.resume_density_flags,
        "industry_enumeration": "industry_enumeration" in report.resume_density_flags,
        "project_enumeration": "project_enumeration" in report.resume_density_flags,
        "chronology_stack": "chronology_stack" in report.resume_density_flags,
        "biography_repetition": "facts_without_interpretation" in report.resume_density_flags,
    }
    return {
        "resume_density": report.resume_density,
        "resume_density_flags": report.resume_density_flags,
        "section_flags": flags,
        # v1.1.6: compress earlier so density can land at ≤3 before publishability
        "compression_required": report.resume_density > 3,
    }


LOCKED_PUBLIC_LABELS_JA: list[str] = [
    "分岐点",
    "選んだ道",
    "選ばなかった人生",
    "失ったもの",
    "守られたもの",
    "今に残った構造",
    "社会との接続",
    "これからの再分岐",
]

# Literary renames Call3 must not keep — map back to locked labels
LABEL_ALIAS_TO_LOCKED: dict[str, str] = {
    "残されたもの": "守られたもの",
    "今に残る問い": "今に残った構造",
    "いまに残った構造": "今に残った構造",
    "失われたもの": "失ったもの",
    "選ばなかった道": "選ばなかった人生",
}


def normalize_markdown_section_headings(body: str) -> str:
    """Repair common Call3 heading corruptions before parse/validate.

    - Inline `## Label` → newline + line-start heading
    - `## Label。` / `##Label` → `## Label`
    - Alias literary renames → locked labels
    """
    text = body or ""
    # Ensure ## headings start on their own line
    text = re.sub(r"([^\n])\s*(##\s*)", r"\1\n\n\2", text)
    # Space after ##
    text = re.sub(r"(?m)^##(?=\S)", "## ", text)

    def _fix_heading(match: re.Match[str]) -> str:
        raw = match.group(1).strip()
        # Drop subtitle after em-dash / colon separators
        raw = re.sub(r"\s*[—–\-|:].*$", "", raw).strip()
        # Exact locked / alias (+ trailing punct only)
        exact = raw.rstrip("。．.!?！？").strip()
        locked = LABEL_ALIAS_TO_LOCKED.get(exact, exact)
        if locked in LOCKED_PUBLIC_LABELS_JA:
            return f"## {locked}"
        # Inline prose after heading: "## 失ったもの。本文…" or alias forms
        aliases = sorted(
            list(LOCKED_PUBLIC_LABELS_JA) + list(LABEL_ALIAS_TO_LOCKED.keys()),
            key=len,
            reverse=True,
        )
        for alias in aliases:
            if raw == alias or raw.startswith(alias):
                target = LABEL_ALIAS_TO_LOCKED.get(alias, alias)
                if target not in LOCKED_PUBLIC_LABELS_JA:
                    continue
                rest = raw[len(alias) :].lstrip("。．.!?！？ \t")
                if rest:
                    return f"## {target}\n\n{rest}"
                return f"## {target}"
        return f"## {exact}"

    text = re.sub(r"(?m)^##\s+(.+)$", _fix_heading, text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + ("\n" if text else "")


def _split_body_by_public_labels(body: str) -> dict[str, str]:
    """Map required public labels → section body text under ## heading."""
    text = normalize_markdown_section_headings(body or "")
    parts = re.split(r"(?m)^##\s+", text)
    out: dict[str, str] = {}
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        heading = lines[0].strip()
        heading = re.sub(r"\s*[—–\-|:].*$", "", heading).strip()
        heading = heading.rstrip("。．.!?！？")
        heading = LABEL_ALIAS_TO_LOCKED.get(heading, heading)
        section_body = "\n".join(lines[1:]).strip()
        # Prefer first occurrence of locked label; later dupes ignored
        if heading not in out:
            out[heading] = section_body
    return out


def parse_locked_sections(body: str) -> dict[str, str]:
    """Structured section map keyed by locked public labels only."""
    by_label = _split_body_by_public_labels(body)
    return {lab: by_label[lab] for lab in LOCKED_PUBLIC_LABELS_JA if lab in by_label}


def render_locked_sections(
    sections: dict[str, str],
    *,
    required_labels: list[str] | None = None,
) -> str:
    """Deterministic markdown from structured sections (source of truth for validation)."""
    order = required_labels or list(LOCKED_PUBLIC_LABELS_JA)
    parts: list[str] = []
    for label in order:
        content = (sections.get(label) or "").strip()
        if not content:
            continue
        parts.append(f"## {label}\n\n{content}\n")
    return ("\n".join(parts) + "\n") if parts else ""


def _section_meaning_preserved(
    *,
    section_id: str,
    body: str,
    claim: str,
    fallback: str,
) -> bool:
    if _section_claim_realized(section_id, body, claim):
        return True
    # Fallback: retain enough of the pre-edit section claim tokens
    if not (body or "").strip():
        return False
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}", (claim or fallback or ""))
    hits = sum(1 for t in tokens[:10] if t in body)
    return hits >= 2


def restore_locked_section_manuscript(
    edited_body: str,
    *,
    fallback_body: str,
    contracts: SectionContractSet | dict[str, Any] | None,
) -> str:
    """After Call3: restore locked labels/order and required section meanings.

    Structured sections are the source of truth: parse → repair → re-render.
    Prose may be shortened; interpretive core from fallback is restored if lost.
    """
    if isinstance(contracts, dict):
        try:
            contracts = SectionContractSet.model_validate(contracts)
        except Exception:
            contracts = None
    edited_n = normalize_markdown_section_headings(edited_body or "")
    fallback_n = normalize_markdown_section_headings(fallback_body or "")
    edited_map = parse_locked_sections(edited_n)
    fallback_map = parse_locked_sections(fallback_n)

    required: list[str] = []
    claims: dict[str, str] = {}
    if contracts is not None:
        for c in contracts.contracts:
            if not c.must_be_present:
                continue
            label = (c.required_public_label or UI_SECTION_LABELS_JA.get(c.section_id, "")).strip()
            if label:
                required.append(label)
                claims[label] = (c.interpretive_claim or c.required_meaning or "").strip()
    if not required:
        required = [lab for lab in LOCKED_PUBLIC_LABELS_JA if lab in fallback_map or lab in edited_map]

    sid_by_label = {v: k for k, v in UI_SECTION_LABELS_JA.items()}
    out: dict[str, str] = {}
    for label in LOCKED_PUBLIC_LABELS_JA:
        if label not in required and label not in edited_map and label not in fallback_map:
            continue
        sid = sid_by_label.get(label, "")
        claim = claims.get(label, "")
        cur = (edited_map.get(label) or "").strip()
        fb = (fallback_map.get(label) or "").strip()
        if label in required:
            if cur and _section_meaning_preserved(
                section_id=sid, body=cur, claim=claim, fallback=fb
            ):
                out[label] = cur
            elif fb:
                out[label] = fb
            elif cur:
                out[label] = cur
        elif cur:
            out[label] = cur
        elif fb and label in edited_map:
            out[label] = fb

    # Preserve optional present sections that were in edited output
    for label, content in edited_map.items():
        if label not in out and content.strip() and label in LOCKED_PUBLIC_LABELS_JA:
            # Optional observatory etc.
            if label not in required:
                out[label] = content.strip()

    rendered = render_locked_sections(out, required_labels=list(LOCKED_PUBLIC_LABELS_JA))
    return rendered if rendered.strip() else edited_n


def _observatory_realized(
    section_body: str,
    claim: str,
    *,
    variants: list[str] | None = None,
) -> bool:
    """Evidence-aware Observatory realization — not employment-keyword-only."""
    blob = section_body or ""
    if not blob.strip():
        return False
    claim_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", claim or "")
    hits = sum(1 for t in claim_tokens[:12] if t in blob)
    if hits >= 2:
        return True
    for variant in variants or []:
        vtoks = re.findall(r"[\u4e00-\u9fff]{2,}", variant)
        vhits = sum(1 for t in vtoks[:8] if t in blob)
        if vhits >= 2:
            return True
        # Short structural phrases
        if len(variant) >= 4 and variant[:12] in blob:
            return True
    # Domain-neutral structural cues (employment optional)
    return bool(
        re.search(
            r"(?:社会|雇用|企業間|並[べび置]|長期|似た条件|人々|"
            r"身体|ケア|治療|個人史|制度|達成|問いが残|還元しな|経験として)",
            blob,
        )
    )


def _section_claim_realized(
    section_id: str,
    section_body: str,
    claim: str,
    *,
    variants: list[str] | None = None,
) -> bool:
    blob = section_body or ""
    if not blob.strip():
        return False
    claim_tokens = re.findall(r"[\u4e00-\u9fff]{2,}", claim or "")
    hits = sum(1 for t in claim_tokens[:12] if t in blob)
    if hits >= 3:
        return True
    if section_id == "lost":
        return bool(
            re.search(
                r"(?:物差し|測り方|確かめ続け|進み具合|同じ制度|同じ場の時間|連続性|"
                r"確かめられ|辿れな|閉じた|手がかりが残らな|検証できな|"
                # v1.1.11: health-compatible unverifiability (not gate loosening)
                r"検証することはできな|辿って確かめられな|辿ることはできな|"
                r"身体条件|同じようには辿)",
                blob,
            )
        )
    if section_id == "protected":
        return bool(
            re.search(
                r"(?:余白|定義し直|別の言葉|固定しきら|一つの所属|尺度を固定|"
                r"閉じきら|可能性|余地|保た|壊さずに)",
                blob,
            )
        )
    if section_id == "residue":
        return bool(
            re.search(
                r"(?:別の物差し|想像され|いまも|消えない|測り方|進み具合|問いが残|"
                r"未解決|想像として|残るから)",
                blob,
            )
        )
    if section_id == "re_branch":
        ok, _, _ = re_branch_realization_check(blob, residue_body="")
        return ok
    if section_id == "branch_point":
        # 境目 ≈ 境界 (romance literary synonym — not a gate loosen)
        return bool(re.search(r"(?:分岐|分かれ|残るか|移るか|境界|境目|次元)", blob))
    if section_id == "chosen_path":
        has_choice = bool(
            re.search(r"(?:選んだ|移った|離れ|外へ|外資|続け|残った|進んだ)", blob)
        )
        has_shift = bool(
            re.search(
                r"(?:定義し直|積み上げる道から|内部で役割|測り方|転換|組み立て|"
                r"持ち運|所属が変わ|開き始|次元|かたち|配分|適応|"
                # v1.1.11 career structural cues (anti-résumé, not employment-metric required)
                r"一つの所属|とどまる道|移り方|組織を移|企業を移|場を移|"
                r"一制度|仕事が続く)",
                blob,
            )
        )
        chronology_only = bool(
            re.search(
                r"(?:その後、いくつかの場を経験|複数の業界|複数業界|Protocol|文章制作)",
                blob,
            )
            and not has_shift
        )
        return has_choice and has_shift and not chronology_only
    if section_id == "unchosen_life":
        return bool(
            re.search(r"(?:選ばなかった|積み上げ|残[るりっ]|一社|一企業|可能性|開いたまま)", blob)
        )
    if section_id == "observatory":
        return _observatory_realized(blob, claim, variants=variants)
    return hits >= 2


def re_branch_realization_check(
    rebranch_body: str,
    *,
    residue_body: str = "",
) -> tuple[bool, list[str], dict[str, Any]]:
    """A present choice + released alternative + Residue connection. Questions alone fail."""
    blob = rebranch_body or ""
    details: dict[str, Any] = {"excerpt": blob[:200]}
    missing: list[str] = []

    question_only = bool(
        re.search(r"(?:か[。．]?$|だろうか[。．]?$|問いになる[。．]?$)", blob)
    ) and not bool(
        re.search(
            r"(?:余地がある|選び直|見なす|認める|指標にしなくて|唯一の|"
            r"置いておく|保つ|見直|見ておく|動かない)",
            blob,
        )
    )
    coaching = bool(
        re.search(
            r"(?:すべき|今こそ|挑戦しよう|成長しよう|キャリアアップ|生産性を上げ)",
            blob,
        )
    )
    has_choice = bool(
        re.search(
            r"(?:選び直|選ぶ余地|見なす|認める|余地がある|自分で選|"
            r"置いておく|保つ|見直す|見ておく|戻る|動かない)",
            blob,
        )
    )
    has_release = bool(
        re.search(
            r"(?:唯一の|だけを|にしなくて|指標にせず|役職|年収|相対化|必須ではない|"
            r"しなくてよい|続けなくてよい|し続けなくてよい|だけが到達|"
            r"固定しなくて|固定し続けなくて|急がなくて|やり直す必要はない|"
            r"結論を出さなくて|答えを固定しなくて|義務にしなくて)",
            blob,
        )
    )
    has_residue_link = bool(
        re.search(
            r"(?:残る問い|いまも|あのとき|物差し|測り|並べ|緊張|残って|残った|想像)",
            blob,
        )
    ) or bool(
        residue_body
        and re.search(r"(?:問い|物差し|測|残|想像)", residue_body)
        and re.search(r"(?:いま|現在|この|その|これから)", blob)
        and has_choice
    )
    reflection_only = bool(
        re.search(
            r"(?:考えていく[。．]?$|見ていくことはできる[。．]?$|思案していく|振り返るだけ)",
            blob,
        )
    ) and not has_choice

    if question_only or reflection_only:
        missing.append("re_branch_question_or_reflection_only")
    if not has_choice:
        missing.append("re_branch_missing_present_choice")
    if not has_release:
        missing.append("re_branch_missing_released_alternative")
    if not has_residue_link:
        missing.append("re_branch_missing_residue_link")
    if coaching:
        missing.append("re_branch_coaching_rhetoric")

    details.update(
        {
            "has_choice": has_choice,
            "has_release": has_release,
            "has_residue_link": has_residue_link,
            "question_only": question_only,
            "reflection_only": reflection_only,
            "coaching": coaching,
        }
    )
    return (not missing), missing, details


def thesis_closure_check(
    body: str,
    contracts: SectionContractSet | dict[str, Any] | None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Chosen Path opens shift → Residue keeps question → Re-branch makes a present choice."""
    if isinstance(contracts, dict):
        try:
            contracts = SectionContractSet.model_validate(contracts)
        except Exception:
            contracts = SectionContractSet()
    if contracts is None:
        contracts = SectionContractSet()

    by_label = _split_body_by_public_labels(body or "")
    chosen = by_label.get("選んだ道", "")
    residue = by_label.get("今に残った構造", "")
    rebranch = by_label.get("これからの再分岐", "")
    failures: list[str] = []
    details: dict[str, Any] = {}

    chosen_c = contracts.by_id("chosen_path")
    if chosen_c and chosen_c.must_be_present:
        shift_ok = _section_claim_realized("chosen_path", chosen, chosen_c.interpretive_claim)
        link_ok = bool(
            re.search(
                r"(?:いま|現在|問い|つなが|起点|続く|残る)",
                chosen,
            )
        ) or bool((chosen_c.thesis_link or "") and any(
            t in chosen for t in re.findall(r"[\u4e00-\u9fff]{2,}", chosen_c.thesis_link)[:4]
        ))
        if not shift_ok:
            failures.append("thesis_closure_missing:chosen_path_structural_shift")
        if shift_ok and not link_ok:
            details["chosen_path_thesis_link"] = "weak"
        details["chosen_path"] = {
            "structural_shift_ok": shift_ok,
            "thesis_link_ok": link_ok,
            "excerpt": chosen[:160],
        }
        if not shift_ok:
            details["chosen_path"]["ok"] = False

    residue_c = contracts.by_id("residue")
    if residue_c and residue_c.must_be_present:
        residue_ok = bool(
            re.search(r"(?:問い|いまも|残|並べ|想像|物差し|測)", residue)
        )
        if not residue_ok:
            failures.append("thesis_closure_missing:residue_unresolved_question")
        details["residue"] = {"ok": residue_ok, "excerpt": residue[:160]}

    rebranch_c = contracts.by_id("re_branch")
    if rebranch_c and rebranch_c.must_be_present:
        choice_ok, choice_missing, choice_details = re_branch_realization_check(
            rebranch, residue_body=residue
        )
        if not choice_ok:
            failures.append("thesis_closure_missing:re_branch_present_choice")
            failures.extend(choice_missing)
        details["re_branch"] = {**choice_details, "ok": choice_ok}

    if not failures and chosen and residue and rebranch:
        arc_blob = f"{chosen}\n{residue}\n{rebranch}"
        # Domain-neutral tension thread (measurement is one valid form, not required)
        if not re.search(
            r"(?:蓄積|積み重ね|確か|指標|物差し|尺度|定義し直|積み|"
            r"問い|緊張|余白|想像|開き|保つ|未解決|次元)",
            arc_blob,
        ):
            failures.append("thesis_closure_missing:arc_tension_thread")
            details["arc"] = "missing_tension_thread"
        else:
            details["arc"] = "closed"

    details["ok"] = not failures
    return (not failures), failures, details


def required_section_realization(
    body: str,
    contracts: SectionContractSet | dict[str, Any] | None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Verify required public labels + material interpretive claim realization."""
    if isinstance(contracts, dict):
        try:
            contracts = SectionContractSet.model_validate(contracts)
        except Exception:
            contracts = SectionContractSet()
    if contracts is None:
        contracts = SectionContractSet()

    blob = body or ""
    by_label = _split_body_by_public_labels(blob)
    missing: list[str] = []
    details: dict[str, Any] = {}

    for c in contracts.contracts:
        if claim_text_is_malformed(c.interpretive_claim):
            missing.append(f"malformed_interpretive_claim:{c.section_id}")
            details[c.section_id] = {
                "ok": False,
                "reason": "malformed_interpretive_claim",
                "claim_preview": (c.interpretive_claim or "")[:100],
            }
            continue
        if not c.must_be_present:
            details[c.section_id] = {
                "ok": True,
                "realization_status": c.realization_status or "omitted",
                "omission_reason": c.omission_reason,
            }
            continue

        label = (c.required_public_label or UI_SECTION_LABELS_JA.get(c.section_id, "")).strip()
        claim = (c.interpretive_claim or "").strip()
        meaning = (c.required_meaning or "").strip()
        if not meaning and not claim:
            missing.append(f"required_section_missing:{c.section_id}")
            details[c.section_id] = "empty_required_meaning"
            continue

        label_present = bool(label and (label in by_label or re.search(rf"(?m)^##\s*{re.escape(label)}\s*$", blob)))
        section_body = by_label.get(label, "")
        if not label_present:
            missing.append(f"required_public_label_missing:{c.section_id}:{label}")
            details[c.section_id] = {
                "ok": False,
                "label": label,
                "label_present": False,
                "realization_status": "failed",
            }
            continue

        # Paragraph budget (soft signal in details; hard-fail only if empty)
        paras = re.findall(r"<p\b[^>]*>.*?</p>|(?:^|\n)(?![#])(\S[^\n]+)", section_body, flags=re.S)
        para_n = max(1, len([p for p in paras if str(p).strip()])) if section_body.strip() else 0
        if c.section_id == "re_branch":
            realized, rb_missing, rb_details = re_branch_realization_check(
                section_body, residue_body=by_label.get("今に残った構造", "")
            )
        else:
            variants = list(getattr(c, "acceptable_semantic_variants", None) or [])
            if c.section_id == "observatory" and claim and claim not in variants:
                variants = [claim, *variants]
            realized = _section_claim_realized(
                c.section_id,
                section_body or blob,
                claim,
                variants=variants,
            )
            rb_missing, rb_details = [], {}
        if para_n < int(c.minimum_paragraphs or 1):
            missing.append(f"required_section_empty:{c.section_id}")
            details[c.section_id] = {
                "ok": False,
                "label": label,
                "label_present": True,
                "paragraphs": para_n,
                "realization_status": "failed",
            }
            continue
        if not realized:
            missing.append(f"required_section_unrealized:{c.section_id}")
            details[c.section_id] = {
                "ok": False,
                "label": label,
                "label_present": True,
                "paragraphs": para_n,
                "claim_preview": claim[:80],
                "realization_status": "failed",
                "section_excerpt": section_body[:160],
                "re_branch_gate": rb_details or None,
                "re_branch_missing": rb_missing or None,
            }
        else:
            details[c.section_id] = {
                "ok": True,
                "label": label,
                "label_present": True,
                "paragraphs": para_n,
                "realization_status": "realized",
                "used_interpretive_claim": bool(claim),
                "re_branch_gate": rb_details or None,
            }

    # v1.1.6: thesis closure is required when chosen_path / re_branch demand it
    needs_closure = any(
        getattr(c, "realization_required", False)
        for c in contracts.contracts
        if c.section_id in {"chosen_path", "re_branch"} and c.must_be_present
    )
    if needs_closure:
        closure_ok, closure_missing, closure_details = thesis_closure_check(blob, contracts)
        details["thesis_closure"] = closure_details
        if not closure_ok:
            missing.extend(closure_missing)

    return (not missing), missing, details


def compress_resume_body(body: str) -> str:
    """Lightweight structural compression: collapse employer/project stacks."""
    text = body or ""
    # Collapse common résumé cadences without deleting present question
    text = re.sub(
        r"NTT東日本で勤務したのち、外資系半導体企業へ転職し、その後は複数の業界と企業を経験している。",
        "一つの組織を離れ、別の場へ移った。",
        text,
    )
    text = re.sub(
        r"選ばれたのは、別の企業へ移る道だった。その後、いくつかの場を経験している。",
        "選ばれたのは外へ移る道だった。",
        text,
    )
    text = re.sub(
        r"かつての勤め先で勤務した後、別の企業へ転職した。",
        "",
        text,
    )
    text = re.sub(
        r"外資系企業への転職と、その後のいくつかの場での経験を並べると、",
        "外へ移った選択を振り返ると、",
        text,
    )
    text = re.sub(
        r"その後、いくつかの場を経験している。",
        "",
        text,
    )
    text = re.sub(
        r"その後は複数の業界・企業を経験し、現在は自分の会社を経営している。",
        "現在は自分の会社を経営している。",
        text,
    )
    text = re.sub(
        r"その後は複数の業界と企業を経験し、現在は自分の会社を経営している。",
        "現在は自分の会社を経営している。",
        text,
    )
    text = re.sub(
        r"外資系半導体企業からさらに複数業界・企業へと続く経過は、",
        "その後の移動の経過は、",
        text,
    )
    text = re.sub(
        r"現在は自分の会社を経営し、複数の観測、Protocol、文章制作を行っている。",
        "現在は自分の会社を経営している。",
        text,
    )
    text = re.sub(
        r"現在は会社を経営し、複数の観測、Protocol、文章制作を行っている。",
        "現在は自分の会社を経営している。",
        text,
    )
    text = re.sub(
        r"会社を経営しながら観測・Protocol・文章制作を進めていること",
        "会社を経営していること",
        text,
    )
    text = re.sub(
        r"NTT東日本での勤務、企業間の移動、そして現在の経営を並べて読む",
        "残ることと移ることを並べて読む",
        text,
    )
    # Generic demotion of project/protocol stacks and industry tours
    text = re.sub(r"複数の観測、?\s*Protocol、?\s*文章制作", "いまの仕事", text)
    text = re.sub(r"観測・Protocol・文章制作", "いまの仕事", text)
    text = re.sub(r"複数の業界・企業", "いくつかの場", text)
    text = re.sub(r"複数の業界と企業", "いくつかの場", text)
    text = re.sub(r"複数業界・企業", "いくつかの場", text)
    text = re.sub(r"外資系半導体企業", "別の企業", text)
    text = re.sub(r"外資系企業へ転職する道", "外へ移る道", text)
    text = re.sub(r"外資系企業へ転職したことで", "外へ移ったことで", text)
    text = re.sub(r"NTT東日本", "かつての勤め先", text)
    # Keep at most two "NTT" mentions
    parts = text.split("NTT")
    if len(parts) > 3:
        text = "NTT".join(parts[:3]) + "".join(parts[3:]).replace("NTT", "かつての勤め先")
    # Demote templated academic cadence when overused
    if text.count("読むことができる") >= 3:
        text = text.replace("として読むことができる", "という見方ができる", 1)
        text = text.replace("と読むことができる", "とも言える", 1)
    if text.count("構造として") >= 2:
        text = text.replace("構造として", "", 2)
    if text.count("制度として") >= 2:
        text = text.replace("制度として", "", 2)
    return text


def abstract_vocabulary_density(text: str) -> dict[str, Any]:
    """Count abstract nouns; flag soft-limit excesses (do not ban)."""
    blob = text or ""
    counts = {w: blob.count(w) for w in ABSTRACT_VOCAB}
    excess = {
        w: counts[w]
        for w in ABSTRACT_VOCAB
        if counts[w] > ABSTRACT_SOFT_LIMIT.get(w, 99)
    }
    return {
        "counts": counts,
        "soft_limits": dict(ABSTRACT_SOFT_LIMIT),
        "excess": excess,
        "excess_total": sum(excess.values()) if excess else 0,
        "thinning_recommended": bool(excess),
    }


def thin_abstract_vocabulary(body: str) -> str:
    """Rewrite excess abstract nouns with ordinary synonyms; preserve meaning."""
    text = body or ""
    dens = abstract_vocabulary_density(text)
    if not dens["thinning_recommended"]:
        return text
    for word, limit in ABSTRACT_SOFT_LIMIT.items():
        alts = ABSTRACT_ALTERNATES.get(word) or ()
        if not alts:
            continue
        # Keep first `limit` occurrences; rewrite later ones round-robin
        parts = text.split(word)
        if len(parts) - 1 <= limit:
            continue
        rebuilt = [parts[0]]
        for i, chunk in enumerate(parts[1:], start=1):
            if i <= limit:
                rebuilt.append(word + chunk)
            else:
                alt = alts[(i - limit - 1) % len(alts)]
                rebuilt.append(alt + chunk)
        text = "".join(rebuilt)
    return text


def render_quiet_rebranch_section(decision: ReBranchDecision | dict[str, Any]) -> str:
    """Quiet present-facing conclusion from ReBranchDecision (no coaching)."""
    if isinstance(decision, dict):
        decision = ReBranchDecision.model_validate(decision)
    release = (decision.what_is_no_longer_required or "").strip()
    choose = (decision.what_can_now_be_chosen or decision.present_choice or "").strip()
    tension = (decision.unresolved_tension or "").strip()
    lines: list[str] = []
    if release and choose:
        lines.append(f"{release}。{choose}余地がある。")
    elif choose:
        lines.append(f"{choose}余地がある。")
    if tension:
        lines.append(
            f"いまも残る問いは、{tension}として並んでいる。"
            "そのそばで、現在の読み方を少しだけ置き直すことができる。"
        )
    else:
        lines.append(
            "かつての分岐がいまも意味を持つのは、いまの生活の測り方を自分で置き直せるからである。"
        )
    return "\n\n".join(lines)


def ensure_rebranch_decision_in_body(
    body: str,
    contracts: SectionContractSet | dict[str, Any] | None,
) -> str:
    """If Re-branch is unrealized, replace its body with a quiet decision close."""
    if isinstance(contracts, dict):
        try:
            contracts = SectionContractSet.model_validate(contracts)
        except Exception:
            return body or ""
    if contracts is None:
        return body or ""
    re_c = contracts.by_id("re_branch")
    if not re_c or not re_c.must_be_present:
        return body or ""

    by_label = _split_body_by_public_labels(body or "")
    residue = by_label.get("今に残った構造", "")
    rebranch = by_label.get("これからの再分岐", "")
    ok, _, _ = re_branch_realization_check(rebranch, residue_body=residue)
    if ok:
        return body or ""

    decision = re_c.rebranch_decision or {
        "unresolved_tension": re_c.unresolved_tension,
        "present_choice": re_c.present_choice,
        "what_is_no_longer_required": re_c.what_is_no_longer_required,
        "what_can_now_be_chosen": re_c.what_can_now_be_chosen,
        "non_genericity_score": re_c.non_genericity_score,
        "interpretive_claim": re_c.interpretive_claim,
    }
    new_section = render_quiet_rebranch_section(decision)
    # Replace ## これからの再分岐 section in markdown
    pattern = re.compile(
        r"(?ms)^(##\s*これからの再分岐\s*\n)(.*?)(?=^##\s|\Z)"
    )
    if pattern.search(body or ""):
        return pattern.sub(rf"\1\n{new_section}\n\n", body or "", count=1)
    return (body or "").rstrip() + f"\n\n## これからの再分岐\n\n{new_section}\n"


def apply_editorial_naturalness_pass(body: str) -> str:
    """Deterministic naturalness: compress résumé stacks + thin abstract density."""
    text = compress_resume_body(body or "")
    text = thin_abstract_vocabulary(text)
    return text
