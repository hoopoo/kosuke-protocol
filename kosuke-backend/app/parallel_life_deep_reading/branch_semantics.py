"""BranchSemantics — domain-neutral pre-thesis layer (v1.1.8–v1.1.9-exp).

v1.1.9: BranchSemantics is authoritative for downstream editorial logic.
Background employment Context Pack facts must not rewrite non-career domains.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.parallel_life_deep_reading.models import Call1Result

CALL_1_PROMPT_VERSION_V118 = "parallel-life-call-1-v1.1.8-exp"
RUNTIME_VERSION_V118_EXP = "parallel-life-runtime-v1.1.8-exp"
CALL_2_PROMPT_VERSION_V118 = "parallel-life-call-2-v1.1.8-exp"
CALL_3_PROMPT_VERSION_V118 = "parallel-life-call-3-v1.1.8-exp"

CALL_1_PROMPT_VERSION_V119 = "parallel-life-call-1-v1.1.9-exp"
RUNTIME_VERSION_V119_EXP = "parallel-life-runtime-v1.1.9-exp"
CALL_2_PROMPT_VERSION_V119 = "parallel-life-call-2-v1.1.9-exp"
CALL_3_PROMPT_VERSION_V119 = "parallel-life-call-3-v1.1.9-exp"

# v1.1.10: deterministic realization / parser / clarification→draft (Call1 pin unchanged)
CALL_1_PROMPT_VERSION_V1110 = "parallel-life-call-1-v1.1.9-exp"
RUNTIME_VERSION_V1110_EXP = "parallel-life-runtime-v1.1.10-exp"
CALL_2_PROMPT_VERSION_V1110 = "parallel-life-call-2-v1.1.10-exp"
CALL_3_PROMPT_VERSION_V1110 = "parallel-life-call-3-v1.1.10-exp"

# v1.1.11 → v1.1.0-rc1 freeze pins (editorial behavior unchanged; drop -exp label)
CALL_1_PROMPT_VERSION_V1111 = "parallel-life-call-1-v1.1.9"
RUNTIME_VERSION_V1111_EXP = "parallel-life-runtime-v1.1.11"
CALL_2_PROMPT_VERSION_V1111 = "parallel-life-call-2-v1.1.11"
CALL_3_PROMPT_VERSION_V1111 = "parallel-life-call-3-v1.1.11"
# Aliases for RC freeze docs / imports
CALL_1_PROMPT_VERSION_V110_RC1 = CALL_1_PROMPT_VERSION_V1111
RUNTIME_VERSION_V110_RC1 = RUNTIME_VERSION_V1111_EXP
CALL_2_PROMPT_VERSION_V110_RC1 = CALL_2_PROMPT_VERSION_V1111
CALL_3_PROMPT_VERSION_V110_RC1 = CALL_3_PROMPT_VERSION_V1111

NON_CAREER_DOMAINS = frozenset(
    {
        "education",
        "romance",
        "family",
        "health",
        "creative",
        "trust",
        "caregiving",
        "place",
    }
)
EMPLOYMENT_DIMENSION_RE = re.compile(
    r"(?:制度的な所属|移動の仕方|雇用|キャリア|企業間|一社内|勤務先)"
)

BranchDomain = Literal[
    "career",
    "education",
    "romance",
    "family",
    "health",
    "entrepreneurship",
    "creative",
    "trust",
    "caregiving",
    "place",
    "mixed",
    "unknown",
]

RebranchMode = Literal[
    "choose",
    "preserve",
    "reconsider",
    "revisit",
    "leave_unresolved",
    "not_act",
    "observe",
    "redefine",
]

CAREER_TEMPLATE_LEAK_RE = re.compile(
    r"(?:役職や年収|仕事を定義し直|所属が変わるたびに自分の仕事|"
    r"持ち運ぶ蓄積|一制度のなかで進み具合|"
    r"長期の積み重ねとして認める|"
    r"勤務先の一点ではなく|"
    r"内部で積み上げる道と外へ持ち運ぶ)"
)

EXPLICIT_EMPLOYMENT_RE = re.compile(
    r"(?:転職|退職|勤務|就職|一社|一企業|企業間|長期雇用|外資|"
    r"社内|役職|年収|給与|キャリア|NTT|雇用|会社員|正社員|"
    r"役割を積み|企業へ移|企業に残)"
)

# Generic stay/leave alone must NOT imply employment
GENERIC_STAY_LEAVE_RE = re.compile(r"(?:残[るりっ]|移[るりっ]|離[れれ])")


class BranchSemantics(BaseModel):
    """Internal structural reading of the branch — before thesis / SectionContracts."""

    domain: str = "unknown"
    changed_dimension: str = ""
    chosen_structure: str = ""
    unchosen_structure: str = ""
    central_tension: str = ""
    lost_verifiability: str = ""
    protected_possibility: str = ""
    present_residue: str = ""
    possible_rebranch_modes: list[str] = Field(default_factory=list)
    sensitive_boundaries: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    diagnostics: dict[str, Any] = Field(default_factory=dict)


def _short(text: str, *, max_len: int = 48, fallback: str = "") -> str:
    t = re.sub(r"\s+", "", (text or "").strip())
    if not t:
        return fallback
    if len(t) > max_len:
        t = t[:max_len].rstrip("、・ ")
    return t


def _corpus(call1: Call1Result, pack_text: str = "") -> str:
    pb = call1.branch_structure.primary_branch
    parts = [
        pb.triggering_event or "",
        pb.realized_path or "",
        " ".join(pb.unrealized_paths or []),
        " ".join(call1.grounded_input.current_context or []),
        " ".join(q.content or "" for q in call1.grounded_input.questions or []),
        " ".join(f.content or "" for f in call1.grounded_input.facts or []),
        pack_text or "",
        call1.meaning_compression.unresolved_question or "",
        call1.meaning_compression.central_question or "",
        call1.central_thesis.statement or "",
    ]
    return "\n".join(parts)


def _pack_text(pack: Any | None) -> str:
    if pack is None:
        return ""
    items = getattr(pack, "items", None) or []
    chunks: list[str] = []
    for i in items:
        if getattr(i, "approved", True) is False:
            continue
        chunks.append(getattr(i, "content", "") or "")
        cat = getattr(i, "category", None)
        if cat is not None:
            chunks.append(str(getattr(cat, "value", cat)))
    return "\n".join(chunks)


def _evidence_ids(call1: Call1Result) -> list[str]:
    ids: list[str] = list(
        call1.branch_structure.primary_branch.supporting_fact_ids or []
    )
    for f in call1.grounded_input.facts or []:
        if f.id and f.id not in ids:
            ids.append(f.id)
    for q in call1.grounded_input.questions or []:
        if q.id and q.id not in ids:
            ids.append(q.id)
    return ids[:12]


def _branch_blob(call1: Call1Result) -> str:
    pb = call1.branch_structure.primary_branch
    return "\n".join(
        [
            pb.triggering_event or "",
            pb.realized_path or "",
            " ".join(pb.unrealized_paths or []),
            " ".join(q.content or "" for q in call1.grounded_input.questions or []),
            " ".join(call1.grounded_input.current_context or []),
        ]
    )


def _score_domain(
    branch_blob: str, pack_blob: str = ""
) -> tuple[str, float, list[str]]:
    """Return (domain, confidence, reasons). Branch text outranks pack background."""
    scores: dict[str, float] = {}
    reasons: list[str] = []

    def bump(domain: str, w: float, reason: str) -> None:
        scores[domain] = scores.get(domain, 0.0) + w
        reasons.append(f"{domain}:{reason}")

    blob = branch_blob or ""
    pack = pack_blob or ""

    if re.search(r"(?:不妊|二人目|授かり|妊娠|体外受精|三人家族|息子|娘)", blob):
        bump("family", 3.2, "fertility_or_child")
    elif re.search(r"(?:治療を続)", blob) and re.search(
        r"(?:不妊|二人目|授かり|妊娠|家族|子ども)", blob
    ):
        bump("family", 2.5, "fertility_treatment")
    if re.search(r"(?:家族|妻|夫|子ども|育児)", blob):
        bump("family", 1.5, "family_words")
    if re.search(r"(?:別れ|恋愛|交際|結婚|離婚|パートナー|恋人|独身)", blob):
        bump("romance", 2.8, "relationship")
    if re.search(r"(?:大学|進学|受験|学部|卒業|キャンパス)", blob):
        bump("education", 3.0, "education")
    if re.search(r"(?:病|入院|体調|がん|手術|リハビリ|過労|身体)", blob):
        bump("health", 2.8, "body_health")
    if re.search(r"(?:介護|看[護守])", blob):
        bump("caregiving", 2.5, "care")
    if re.search(r"(?:創作|小説|芸術|音楽|表現|絵を描|執筆|副業として続)", blob):
        bump("creative", 3.0, "creative")
    if re.search(r"(?:起業|自分の会社|経営|独立)", blob) and not re.search(
        r"(?:NTT|転職|外資|一企業)", blob
    ):
        bump("entrepreneurship", 2.2, "ownership")
    if re.search(r"(?:都会|地方|地元に残|転居|移住)", blob) and not EXPLICIT_EMPLOYMENT_RE.search(
        blob
    ):
        bump("place", 2.2, "place")
    if re.search(r"(?:信頼|裏切|約束)", blob):
        bump("trust", 1.5, "trust")

    # Branch-level employment only (not pack background)
    if EXPLICIT_EMPLOYMENT_RE.search(blob) and re.search(
        r"(?:転職|退職|NTT|外資|一企業|企業間|長期雇用|役職|年収|起業|会社を辞)", blob
    ):
        bump("career", 2.8, "branch_employment")
    elif re.search(r"(?:会社員|勤務|就職)", blob) and not re.search(
        r"(?:創作|小説|表現|大学|進学|別れ|不妊|体調|地元)", blob
    ):
        bump("career", 2.0, "branch_job_language")

    # Pack employment is background only — weak signal, must not dominate
    if re.search(r"(?:category:career_history|category:current_work)", pack) or EXPLICIT_EMPLOYMENT_RE.search(
        pack
    ):
        bump("career", 0.8, "background_employment_context")
        reasons.append("background_employment_context:pack")

    if not scores:
        return "unknown", 0.25, ["no_domain_signal"]

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_d, top_s = ranked[0]
    # Prefer clear non-career branch domain over weak pack-driven career
    if top_d in NON_CAREER_DOMAINS:
        conf = min(0.95, 0.4 + top_s / 6.0)
        return top_d, conf, reasons
    if (
        len(ranked) > 1
        and ranked[1][0] in NON_CAREER_DOMAINS
        and ranked[1][1] >= top_s * 0.75
        and top_d == "career"
        and any("background_employment" in r for r in reasons)
    ):
        # Pack career must not override education/creative/etc.
        return ranked[1][0], min(0.9, 0.4 + ranked[1][1] / 6.0), reasons + [
            "authority:non_career_branch_over_pack"
        ]
    if len(ranked) > 1 and ranked[1][1] >= top_s * 0.9 and ranked[1][0] != "career":
        # True mixed only when two strong branch domains compete
        if ranked[0][0] != "career" and ranked[1][0] != "career":
            return "mixed", min(0.85, (top_s + ranked[1][1]) / 8.0), reasons
    conf = min(0.95, 0.35 + top_s / 6.0)
    return top_d, conf, reasons


def allows_career_product_logic(sem: BranchSemantics | None) -> bool:
    """Career templates (redefine work / salary / accumulation) only when domain allows."""
    if sem is None:
        return False
    domain = (sem.domain or "unknown").strip()
    dim = sem.changed_dimension or ""
    if domain in NON_CAREER_DOMAINS:
        return False
    if domain == "mixed" and not EMPLOYMENT_DIMENSION_RE.search(dim):
        return False
    if domain in {"career", "entrepreneurship"}:
        return True
    if domain == "mixed" and EMPLOYMENT_DIMENSION_RE.search(dim):
        return bool((sem.diagnostics or {}).get("branch_employment_evidence"))
    return False


def has_background_employment_context(sem: BranchSemantics | None) -> bool:
    if not sem:
        return False
    return bool((sem.diagnostics or {}).get("background_employment_context"))


def _present_question(call1: Call1Result) -> str:
    mc = call1.meaning_compression
    q = (
        (mc.unresolved_question or "").strip()
        or (mc.central_question or "").strip()
        or (
            (call1.user_confirmation_view.present_questions or [""])[0]
            if call1.user_confirmation_view
            else ""
        )
    )
    if not q and call1.grounded_input.questions:
        q = call1.grounded_input.questions[0].content or ""
    return _short(q, max_len=56, fallback="")


def _has_branch_employment_evidence(call1: Call1Result, branch_blob: str) -> bool:
    """Employment evidence on the branch itself (not pack background)."""
    pb = call1.branch_structure.primary_branch
    text = f"{branch_blob}\n{pb.triggering_event}\n{pb.realized_path}\n{' '.join(pb.unrealized_paths or [])}"
    return bool(
        re.search(
            r"(?:転職|退職|NTT|外資|一企業|企業間|長期雇用|役職|年収|起業|会社を辞|"
            r"役割を積み|企業へ移|企業に残)",
            text,
        )
    )


def _has_background_employment(call1: Call1Result, pack_blob: str) -> bool:
    if re.search(r"(?:category:career_history|category:current_work)", pack_blob or ""):
        return True
    for f in call1.grounded_input.facts or []:
        tags = " ".join(f.tags or [])
        src = f.source_field or ""
        if re.search(r"(?:career_history|current_work)", tags + " " + src):
            return True
    return bool(EXPLICIT_EMPLOYMENT_RE.search(pack_blob or ""))


def _changed_dimension(domain: str, blob: str, chosen: str, unchosen: str) -> str:
    # Evidence-first overrides by keyword, else domain hint
    if re.search(r"(?:不妊|二人目|授かり)", blob) or (
        re.search(r"治療", blob) and re.search(r"(?:不妊|二人目|家族|子ども)", blob)
    ):
        return "家族のかたち／身体と治療の選択"
    if re.search(r"(?:別れ|恋愛|結婚|パートナー)", blob):
        return "関係の継続／別れ"
    if re.search(r"(?:大学|進学|受験)", blob):
        return "教育の機会／制度上の進路"
    if re.search(r"(?:病|入院|体調|過労|治療)", blob):
        return "身体の制約／適応の仕方"
    if re.search(r"(?:創作|小説|表現|執筆)", blob):
        return "表現に割く時間／生計との配分"
    if re.search(r"(?:都会|地方|地元)", blob) and not EXPLICIT_EMPLOYMENT_RE.search(blob):
        return "暮らす場所／日常の所属"
    if re.search(r"(?:起業|自分の会社|経営)", blob) and not re.search(
        r"(?:NTT|転職|外資)", blob
    ):
        return "所有と安定／リスクへの露出"
    if EXPLICIT_EMPLOYMENT_RE.search(blob):
        return "制度的な所属／移動の仕方"
    # Domain fallbacks (short, structural — not thesis copy)
    fallbacks = {
        "career": "制度的な所属／移動の仕方",
        "family": "家族のかたち",
        "romance": "関係の継続",
        "education": "教育の機会／制度上の進路",
        "health": "身体の制約／適応",
        "entrepreneurship": "所有と安定",
        "creative": "表現と生計の配分",
        "caregiving": "ケアに割く時間と身体",
        "place": "暮らす場所",
        "trust": "信頼の置き方",
        "mixed": "複数の生活次元が同時に動いた分岐",
        "unknown": "選んだ道と選ばなかった道のあいだ",
    }
    if chosen or unchosen:
        return fallbacks.get(domain, fallbacks["unknown"])
    return fallbacks.get(domain, "")


def _lost_verifiability(
    *,
    domain: str,
    unchosen: str,
    employment: bool,
) -> str:
    u = _short(unchosen, max_len=40, fallback="選ばなかった道")
    if employment and domain in {"career", "entrepreneurship", "mixed"}:
        return (
            f"「{u}」を取らなかったことで、同じ制度の時間のなかで進度を確かめ続ける道が閉じたこと"
        )
    if domain == "family":
        return f"「{u}」側にあった家族のかたちを、いまから確かめる道が閉じたこと"
    if domain == "romance":
        return f"「{u}」として続いていた関係の生活を、いま知る手がかりが残らないこと"
    if domain == "education":
        return f"「{u}」を歩んだ場合の形成や自己像を、いま検証できないこと"
    if domain == "health":
        return f"「{u}」側で続いていた身体条件や働き方を、いま同じようには辿れないこと"
    if domain == "creative":
        return f"「{u}」として表現に割けていた時間や生活を、いま同じ連続では確かめられないこと"
    if domain == "place":
        return f"「{u}」側の暮らしの連続を、いま体験として辿れないこと"
    return f"「{u}」を選ばなかったことで、そこで何が続いていたかを確かめ続ける道が閉じたこと"


def _protected_possibility(
    *,
    domain: str,
    chosen: str,
    present: str,
    employment: bool,
) -> str:
    c = _short(chosen, max_len=36, fallback="選んだ道")
    p = _short(present, max_len=36, fallback="")
    if employment and domain in {"career", "entrepreneurship", "mixed"}:
        if re.search(r"(?:経営|自分の会社|定義)", f"{present}\n{chosen}"):
            return "一つの所属に人生の尺度を固定しきらず、仕事を別の言葉で置き直す余白"
        return f"「{c}」を取った側に残った、場を移しながら生活を組み立てる余白"
    if domain == "family":
        return (
            f"「{c}」を取った側に残った、いまの家族のかたちを壊さずに置く余白"
            + (f"（{p}）" if p else "")
        )
    if domain == "romance":
        return f"「{c}」を取った側に残った、一人の生活を閉じきらずに続ける余地"
    if domain == "education":
        return f"「{c}」を取った側に残った、別の形成経路を想像し続ける余地"
    if domain == "health":
        return f"「{c}」を取った側に残った、身体の制約のなかで生活を続ける余地"
    if domain == "creative":
        return f"「{c}」を取った側に残った、表現を未完のまま持ち続ける余地"
    if domain == "place":
        return f"「{c}」を取った側に残った、いまの場所での日常を続ける余地"
    return f"「{c}」を取った側に残った、まだ閉じきらない可能性"


def _present_residue(*, question: str, domain: str, tension: str) -> str:
    q = question or "あのとき別の道を選んでいたら"
    if re.search(r"(?:役職|年収|給与|肩書)", q) and domain in {
        "career",
        "entrepreneurship",
        "mixed",
    }:
        return (
            f"「{q}」という問いが残るのは、選ばなかった道が別の測り方として想像されるからかもしれない"
        )
    if domain == "family":
        return f"「{q}」がいまも残るのは、選ばなかった家族のかたちが想像として開いているからかもしれない"
    if domain == "romance":
        return f"「{q}」がいまも残るのは、関係の続き方についての未解決の想像が残るからかもしれない"
    if domain == "education":
        return f"「{q}」がいまも残るのは、別の進路が自己像の想像として残るからかもしれない"
    if domain == "health":
        return f"「{q}」がいまも残るのは、身体と生活の不確かさが問いとして残るからかもしれない"
    if domain == "creative":
        return f"「{q}」がいまも残るのは、未完の表現の可能性がいまも触れているからかもしれない"
    if tension:
        return f"「{q}」がいまも残るのは、{tension}が消えていないからかもしれない"
    return f"「{q}」がいまも残るのは、選ばなかった道が想像として開いているからかもしれない"


def _central_tension(*, domain: str, chosen: str, unchosen: str, employment: bool) -> str:
    c = _short(chosen, max_len=28, fallback="選んだ道")
    u = _short(unchosen, max_len=28, fallback="選ばなかった道")
    if employment and domain in {"career", "entrepreneurship", "mixed"}:
        return "一制度のなかで進み具合を測る物差しと、場を移しながら持ち運ぶ積み重ねのあいだ"
    if domain == "family":
        return f"「{c}」側の家族のかたちと、「{u}」側の未実現の家族想像のあいだ"
    if domain == "romance":
        return f"「{c}」側の単独の連続と、「{u}」側の関係の連続のあいだ"
    if domain == "education":
        return f"「{c}」側の進路上の自己と、「{u}」側の別の形成のあいだ"
    if domain == "health":
        return f"「{c}」側の適応した生活と、「{u}」側の別の身体条件の想像のあいだ"
    if domain == "creative":
        return f"「{c}」側の生計と表現の配分と、「{u}」側の未完の表現生活のあいだ"
    if domain == "place":
        return f"「{c}」側の場所での日常と、「{u}」側の別の暮らしの想像のあいだ"
    return f"「{c}」と「{u}」がいまも並んで残る緊張"


def _rebranch_modes(
    *,
    domain: str,
    question: str,
    employment: bool,
    vague: bool,
) -> list[str]:
    if vague:
        return ["leave_unresolved", "not_act", "observe"]
    modes: list[str] = []
    if employment and domain in {"career", "entrepreneurship", "mixed"} and re.search(
        r"(?:役職|年収|測|どこまで|蓄積)", question + domain
    ):
        modes.extend(["redefine", "choose", "reconsider"])
    elif domain == "family":
        modes.extend(["leave_unresolved", "preserve", "observe"])
    elif domain == "romance":
        modes.extend(["observe", "revisit", "leave_unresolved", "not_act"])
    elif domain == "education":
        modes.extend(["reconsider", "observe", "leave_unresolved"])
    elif domain == "health":
        modes.extend(["preserve", "observe", "not_act"])
    elif domain == "creative":
        modes.extend(["choose", "preserve", "revisit"])
    elif domain == "place":
        modes.extend(["preserve", "reconsider", "leave_unresolved"])
    elif domain == "entrepreneurship":
        modes.extend(["reconsider", "preserve", "choose"])
    else:
        modes.extend(["observe", "leave_unresolved", "reconsider"])
    # Deduplicate preserve order
    out: list[str] = []
    for m in modes:
        if m not in out:
            out.append(m)
    return out


def _sensitive_boundaries(domain: str, blob: str) -> list[str]:
    bounds: list[str] = []
    if re.search(r"(?:病|不妊|治療|身体|妊娠|授かり|入院|介護)", blob):
        bounds.append("no_unsupported_causality")
        bounds.append("no_medical_invention")
    if domain in {"family", "romance", "health", "caregiving"}:
        bounds.append("no_invented_affect")
    if domain == "family":
        bounds.append("no_family_outcome_invention")
    if domain == "romance":
        bounds.append("no_reunion_advice")
    return bounds


def build_branch_semantics(
    call1: Call1Result,
    *,
    pack: Any | None = None,
    pack_text: str = "",
) -> BranchSemantics:
    """Derive BranchSemantics from grounded evidence. Empty fields allowed."""
    pb = call1.branch_structure.primary_branch
    pack_blob = pack_text or _pack_text(pack)
    branch_blob = _branch_blob(call1)
    blob = _corpus(call1, pack_blob)
    domain, confidence, reasons = _score_domain(branch_blob, pack_blob)
    branch_employment = _has_branch_employment_evidence(call1, branch_blob)
    background_employment = _has_background_employment(call1, pack_blob)
    # Career product templates require branch-level employment + allowed domain
    employment_for_templates = branch_employment and domain in {
        "career",
        "entrepreneurship",
        "mixed",
    }
    if domain == "career" and not branch_employment:
        if re.search(r"(?:都会|地方|地元)", branch_blob):
            domain = "place"
            confidence = max(0.4, confidence - 0.15)
            reasons.append("career_demoted:no_branch_employment")
        elif domain in NON_CAREER_DOMAINS or re.search(
            r"(?:大学|創作|別れ|不妊|体調)", branch_blob
        ):
            pass
        elif not EXPLICIT_EMPLOYMENT_RE.search(branch_blob):
            domain = "unknown"
            reasons.append("career_demoted:weak_branch_evidence")

    chosen = _short(pb.realized_path or "", max_len=42, fallback="")
    unchosen = _short(
        " / ".join(pb.unrealized_paths or []), max_len=42, fallback=""
    )
    present = _short(
        " ".join(call1.grounded_input.current_context[:1])
        or (call1.meaning_compression.present_structure or ""),
        max_len=42,
        fallback="",
    )
    question = _present_question(call1)
    vague = (
        domain == "unknown"
        and not chosen
        and not unchosen
        and len(blob.strip()) < 40
    ) or bool(re.search(r"(?:よく覚えてい|はっきりしな|曖昧)", blob))

    changed = _changed_dimension(domain, branch_blob or blob, chosen, unchosen)
    # Non-career domains never receive career template strings
    use_emp = employment_for_templates and domain not in NON_CAREER_DOMAINS
    if domain in NON_CAREER_DOMAINS:
        use_emp = False
    tension = _central_tension(
        domain=domain, chosen=chosen, unchosen=unchosen, employment=use_emp
    )
    lost = _lost_verifiability(domain=domain, unchosen=unchosen, employment=use_emp)
    protected = _protected_possibility(
        domain=domain, chosen=chosen, present=present, employment=use_emp
    )
    residue = _present_residue(question=question, domain=domain, tension=tension)
    modes = _rebranch_modes(
        domain=domain, question=question, employment=use_emp, vague=vague
    )
    bounds = _sensitive_boundaries(domain, blob)

    if not chosen and not unchosen:
        lost = lost if unchosen else ""
        protected = protected if chosen else ""

    # Hard scrub career templates outside career-authoritative domains
    scrub_domain = domain if domain not in {"career", "entrepreneurship"} else domain
    if domain in NON_CAREER_DOMAINS or (
        domain == "mixed" and not EMPLOYMENT_DIMENSION_RE.search(changed)
    ):
        scrub_domain = domain if domain != "mixed" else "unknown"
        lost = _lost_verifiability(domain=scrub_domain, unchosen=unchosen, employment=False)
        protected = _protected_possibility(
            domain=scrub_domain, chosen=chosen, present=present, employment=False
        )
        tension = _central_tension(
            domain=scrub_domain, chosen=chosen, unchosen=unchosen, employment=False
        )
        residue = _present_residue(question=question, domain=scrub_domain, tension=tension)
        modes = _rebranch_modes(
            domain=scrub_domain, question=question, employment=False, vague=vague
        )

    sem = BranchSemantics(
        domain=domain,
        changed_dimension=changed,
        chosen_structure=chosen,
        unchosen_structure=unchosen,
        central_tension=tension,
        lost_verifiability=lost,
        protected_possibility=protected,
        present_residue=residue,
        possible_rebranch_modes=modes,
        sensitive_boundaries=bounds,
        evidence_ids=_evidence_ids(call1),
        confidence=confidence,
        diagnostics={
            "domain_reasons": reasons,
            "branch_employment_evidence": branch_employment,
            "background_employment_context": background_employment,
            "explicit_employment_evidence": branch_employment,  # compat: branch-only
            "allows_career_product_logic": False,  # filled below
            "vague": vague,
            "runtime_pin": RUNTIME_VERSION_V119_EXP,
        },
    )
    sem.diagnostics["allows_career_product_logic"] = allows_career_product_logic(sem)
    return sem


def detect_semantic_domain_leak(
    sem: BranchSemantics | None,
    *,
    contract_texts: list[str] | None = None,
) -> dict[str, Any]:
    """Flag career-specific language on non-career BranchSemantics domains."""
    texts = [t for t in (contract_texts or []) if (t or "").strip()]
    blob = "\n".join(texts)
    if not sem:
        return {"leaked": False, "hits": [], "domain": None}
    if allows_career_product_logic(sem):
        return {"leaked": False, "hits": [], "domain": sem.domain, "authority": "career_allowed"}
    hits = []
    for m in CAREER_TEMPLATE_LEAK_RE.finditer(blob):
        hits.append(m.group(0))
    # Also catch salary/accumulation fragments
    for pat in (r"役職や年収", r"長期の積み重ね", r"持ち運ぶ積み重ね", r"仕事を定義し直"):
        if re.search(pat, blob):
            hits.append(pat)
    hits = list(dict.fromkeys(hits))
    return {
        "leaked": bool(hits),
        "hits": hits,
        "domain": sem.domain,
        "changed_dimension": sem.changed_dimension,
        "authority": "non_career_guard",
    }


def get_branch_semantics(call1: Call1Result) -> BranchSemantics | None:
    raw = getattr(call1, "branch_semantics", None)
    if isinstance(raw, BranchSemantics):
        return raw
    if isinstance(raw, dict) and raw:
        try:
            return BranchSemantics.model_validate(raw)
        except Exception:
            return None
    return None


def attach_branch_semantics(
    call1: Call1Result,
    *,
    pack: Any | None = None,
) -> tuple[Call1Result, BranchSemantics]:
    sem = build_branch_semantics(call1, pack=pack)
    updated = call1.model_copy(update={"branch_semantics": sem.model_dump(mode="json")})
    return updated, sem


def career_template_leakage(text: str) -> bool:
    return bool(CAREER_TEMPLATE_LEAK_RE.search(text or ""))
