"""Deep Reading v1.0.1 release-blocker gates (runtime-only).

Fixes Public QA blockers:
- Case 09 material contradiction
- Case 08 unrealized-path modality
- Case 10 vague / non-branch
- Case 06 sensitive-domain causal thesis
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.parallel_life_deep_reading.models import (
    Call1Result,
    GenerationStatus,
    ValidationCategory,
)

# ---------------------------------------------------------------------------
# Case 09 — material contradiction
# ---------------------------------------------------------------------------

POLARITY_PAIRS: list[tuple[str, str]] = [
    ("落ちた", "入社した"),
    ("不合格", "合格"),
    ("辞退した", "入学した"),
    ("断った", "受けた"),
    ("やめた", "続けた"),
    ("行かなかった", "行った"),
    ("離婚した", "結婚生活を続けた"),
]

_ENTITY_STOP = {
    "こと",
    "もの",
    "ため",
    "とき",
    "時期",
    "現在",
    "いま",
    "今日",
    "自分",
    "生活",
    "人生",
    "実際",
    "結局",
    "その後",
    "以前",
    "以上",
    "以下",
    "場合",
    "選択",
    "道",
}


@dataclass
class MaterialContradiction:
    pole_a: str
    pole_b: str
    context_a: str
    context_b: str
    shared_entities: list[str] = field(default_factory=list)

    def describe(self) -> str:
        ent = (
            "・".join(self.shared_entities[:3])
            if self.shared_entities
            else "同じ対象"
        )
        return (
            f"矛盾: 「{self.pole_a}」と「{self.pole_b}」が"
            f"「{ent}」について同時に入力されています"
        )


def _entities(text: str) -> set[str]:
    toks = set(re.findall(r"[\u4e00-\u9fff]{2,}", text or ""))
    return {t for t in toks if t not in _ENTITY_STOP and len(t) >= 2}


def _windows_for_marker(blob: str, marker: str, radius: int = 18) -> list[str]:
    out: list[str] = []
    start = 0
    while True:
        i = blob.find(marker, start)
        if i < 0:
            break
        out.append(blob[max(0, i - radius) : i + len(marker) + radius])
        start = i + len(marker)
    return out


def collect_contradiction_corpus(call1: Call1Result, source_text: str = "") -> str:
    parts: list[str] = [source_text or ""]
    pb = call1.branch_structure.primary_branch
    parts.extend(
        [
            pb.period or "",
            pb.triggering_event or "",
            pb.realized_path or "",
            " ".join(pb.unrealized_paths or []),
            call1.user_confirmation_view.triggering_event or "",
            call1.user_confirmation_view.chosen_path or "",
            call1.user_confirmation_view.unchosen_path or "",
        ]
    )
    for f in call1.grounded_input.facts:
        parts.append(f.content or "")
    return "\n".join(p for p in parts if p)


def detect_material_contradictions(
    call1: Call1Result,
    *,
    source_text: str = "",
) -> list[MaterialContradiction]:
    blob = collect_contradiction_corpus(call1, source_text)
    if not blob.strip():
        return []
    found: list[MaterialContradiction] = []
    seen: set[tuple[str, str]] = set()
    for neg, pos in POLARITY_PAIRS:
        if neg not in blob or pos not in blob:
            continue
        # Prefer longer negative first so 不合格 vs 合格 is not double-counted oddly
        neg_wins = _windows_for_marker(blob, neg)
        pos_wins = _windows_for_marker(blob, pos)
        if not neg_wins or not pos_wins:
            continue
        best_shared: set[str] = set()
        best_a = neg_wins[0]
        best_b = pos_wins[0]
        for a in neg_wins:
            ea = _entities(a)
            for b in pos_wins:
                eb = _entities(b)
                shared = ea & eb
                if len(shared) > len(best_shared):
                    best_shared = shared
                    best_a, best_b = a, b
        pb = call1.branch_structure.primary_branch
        pair_text = f"{pb.triggering_event}\n{pb.realized_path}"
        primary_pair = neg in pair_text and pos in pair_text
        if not best_shared and not primary_pair:
            if "第一志望" in blob and neg in blob and pos in blob:
                best_shared = {"第一志望"}
            else:
                continue
        key = (neg, pos)
        if key in seen:
            continue
        seen.add(key)
        found.append(
            MaterialContradiction(
                pole_a=neg,
                pole_b=pos,
                context_a=best_a.strip(),
                context_b=best_b.strip(),
                shared_entities=sorted(best_shared)[:6],
            )
        )
    return found


def contradiction_clarification(c: MaterialContradiction) -> str:
    ent = c.shared_entities[0] if c.shared_entities else "その対象"
    return (
        f"{ent}について、『{c.pole_a}』と『{c.pole_b}』の両方が入力されています。"
        f"実際にはどちらでしたか？"
    )


# ---------------------------------------------------------------------------
# Case 10 — vague / non-branch
# ---------------------------------------------------------------------------

VAGUE_PERIODS = {"特にない", "なし", "わからない", "いつかわからない", "不明", "とくにない"}
VAGUE_TRIGGERS = {
    "なんとなく",
    "特にない",
    "普通に",
    "流れで",
    "いろいろあった",
    "なんとなく今まで働いてきた",
}
VAGUE_CHOSEN = {"今の人生", "普通の人生", "この人生", "いまの人生"}
VAGUE_UNCHOSEN = {
    "自由な人生",
    "もっと自由な人生",
    "違う人生",
    "もっと良い人生",
    "別の人生",
    "より自由な人生",
}


@dataclass
class BranchConcretenessResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    clarification_questions: list[str] = field(default_factory=list)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip())


def assess_branch_concreteness(call1: Call1Result) -> BranchConcretenessResult:
    pb = call1.branch_structure.primary_branch
    period = _norm(pb.period or call1.user_confirmation_view.branch_period)
    trigger = _norm(
        pb.triggering_event or call1.user_confirmation_view.triggering_event
    )
    chosen = _norm(pb.realized_path or call1.user_confirmation_view.chosen_path)
    unchosen = _norm(
        (pb.unrealized_paths[0] if pb.unrealized_paths else "")
        or call1.user_confirmation_view.unchosen_path
    )

    reasons: list[str] = []
    if period in VAGUE_PERIODS:
        reasons.append("vague_period")
    if trigger in VAGUE_TRIGGERS or trigger.startswith("なんとなく") or trigger.startswith(
        "普通に"
    ):
        reasons.append("vague_trigger")
    if chosen in VAGUE_CHOSEN:
        reasons.append("vague_chosen")
    if unchosen in VAGUE_UNCHOSEN:
        reasons.append("vague_unchosen")

    vague_core = {"vague_period", "vague_trigger", "vague_chosen"}
    if len(vague_core & set(reasons)) >= 2 or (
        "vague_period" in reasons and "vague_trigger" in reasons
    ):
        return BranchConcretenessResult(
            ok=False,
            reasons=reasons,
            clarification_questions=[
                "『別の人生もあったのかな』と思うきっかけになった、具体的な出来事や時期はありますか？",
                "そのとき、実際に選べた別の道はありましたか？",
            ],
        )
    return BranchConcretenessResult(ok=True, reasons=reasons)


# ---------------------------------------------------------------------------
# Case 06 — sensitive-domain causal thesis
# ---------------------------------------------------------------------------

SENSITIVE_DOMAIN_KEYS = {
    "health",
    "body",
    "fertility",
    "pregnancy",
    "mental_health",
    "medical",
    "健康",
    "身体",
    "不妊",
    "妊娠",
    "医療",
}

SENSITIVE_CAUSAL_PATTERNS = [
    re.compile(r"ことで.{0,24}(楽|良く|よく|改善|回復|治|軽|ゆったり|ゆっくり)"),
    re.compile(r"ことにより.{0,24}(楽|良く|よく|改善|回復|治)"),
    re.compile(r"により.{0,24}(楽|良く|よく|改善|回復|治)"),
    re.compile(r"のおかげで"),
    re.compile(r"したため.{0,16}(現在|いま|今)"),
    # 「変えたことが、今の楽な働き方につながっている」
    re.compile(r"ことが[、,]?.{0,48}(楽|良く|よく|改善|回復|治)"),
    re.compile(r"(楽|良く|改善|回復).{0,24}(つなが|に繋が|につなが)"),
    re.compile(r"(つながっ|に繋がり|に繋が).{0,16}(楽|良く|改善|回復)"),
    re.compile(r"変えたことで"),
    re.compile(r"減らしたことで"),
    re.compile(r"変えたこと[はが]"),
    re.compile(r"減らしたこと[はが]"),
    # Unsupported evaluative completion in sensitive domains
    re.compile(r"(良い選択|よい選択|よかった|正解だった|うまくいった|正しい選択)"),
]


def sensitive_domains_of(call1: Call1Result) -> set[str]:
    domains: set[str] = set()
    for d in call1.grounded_input.sensitive_domains or []:
        domains.add(str(d).lower())
    for d in call1.sensitive_domain_analysis.domains or []:
        domains.add(str(d).lower())
    return domains


def is_sensitive_case(call1: Call1Result) -> bool:
    domains = sensitive_domains_of(call1)
    if domains & {k.lower() for k in SENSITIVE_DOMAIN_KEYS}:
        return True
    blob = collect_contradiction_corpus(call1)
    return bool(re.search(r"体調|病|治療|不妊|妊娠|メンタル|うつ", blob))


def user_explicitly_states_causality(source_text: str, thesis: str) -> bool:
    src = source_text or ""
    if not src:
        return False
    if not re.search(r"(ことで|により|のおかげで|したため|だから|ので)", src):
        return False
    affect_tokens = re.findall(r"(楽|改善|回復|良く|よくなっ)", thesis or "")
    return any(t in src for t in affect_tokens)


def sensitive_thesis_is_unsupported_causal(
    thesis: str,
    call1: Call1Result,
    *,
    source_text: str = "",
) -> bool:
    if not thesis or not is_sensitive_case(call1):
        return False
    if user_explicitly_states_causality(source_text, thesis):
        return False
    return any(p.search(thesis) for p in SENSITIVE_CAUSAL_PATTERNS)


def build_safe_sensitive_coexistence_thesis(call1: Call1Result) -> str:
    pb = call1.branch_structure.primary_branch
    chosen = (pb.realized_path or call1.user_confirmation_view.chosen_path or "").strip()
    present_facts = [
        f.content
        for f in call1.grounded_input.facts
        if any(x in f.content for x in ("今", "いま", "現在", "ゆっくり"))
    ]
    feelings = [f.content for f in call1.grounded_input.feelings if f.content]
    if not chosen and not present_facts and not feelings:
        return ""
    head = f"{chosen.rstrip('。')}現在" if chosen else "現在"
    mid = present_facts[0].rstrip("。") if present_facts else ""
    feel = feelings[0].rstrip("。") if feelings else ""
    if mid and feel and mid != feel:
        # Prefer 「…働いており、…感じている」
        if mid.endswith("いる"):
            mid_clause = mid[:-2] + "おり"
        else:
            mid_clause = mid
        return f"{head}、{mid_clause}、{feel}。"
    if mid:
        return f"{head}、{mid}。"
    if feel:
        return f"{head}、{feel}。"
    return ""


# ---------------------------------------------------------------------------
# Case 08 — unrealized-path modality
# ---------------------------------------------------------------------------

REALIZED_MODALITY_RES = [
    re.compile(r"ことがあった"),
    re.compile(r"経験があった"),
    re.compile(r"へ行った"),
    re.compile(r"に行った"),
    re.compile(r"で暮らした"),
    re.compile(r"を選んだ"),
    re.compile(r"に進んだ"),
    re.compile(r"へ進んだ"),
    re.compile(r"していた[。．]"),
]

ALLOWED_UNREALIZED_MARKERS = (
    "選ばなかった",
    "選んでいたら",
    "進んでいたら",
    "行っていたら",
    "可能性",
    "という道",
    "別の道",
    "問い",
    "と考えられる",
    "考えられる",
)


@dataclass
class UnrealizedModalityHit:
    excerpt: str
    unrealized_path: str
    modality_type: str = "realized_event_modality"

    def to_model_dict(self) -> dict[str, Any]:
        return {
            "excerpt": self.excerpt,
            "unrealized_path": self.unrealized_path,
            "modality_type": self.modality_type,
            "missing_support": "path_is_unrealized_or_counterfactual",
            "category": ValidationCategory.unsupported.value,
        }


def _path_cores(path: str) -> list[str]:
    p = (path or "").strip()
    if not p:
        return []
    cores = [p, re.sub(r"(こと|へ行く|に行く|する)$", "", p)]
    cores.extend(re.findall(r"[\u4e00-\u9fff]{2,}(?:大学|会社|仕事|写真|人生)?", p))
    out: list[str] = []
    for c in cores:
        c = c.strip()
        if len(c) >= 2 and c not in out:
            out.append(c)
    return out


def unrealized_paths_from_call1(call1: Call1Result) -> list[str]:
    paths: list[str] = []
    pb = call1.branch_structure.primary_branch
    paths.extend(pb.unrealized_paths or [])
    if call1.user_confirmation_view.unchosen_path:
        paths.append(call1.user_confirmation_view.unchosen_path)
    for b in list(call1.branch_structure.retrospective_counterfactuals or []) + list(
        call1.branch_structure.secondary_branches or []
    ):
        cls = getattr(b.classification, "value", b.classification)
        if cls == "retrospective_counterfactual" or b.must_not_be_treated_as_historical_choice:
            if b.description:
                paths.append(b.description)
            paths.extend(b.unrealized_paths or [])
        elif b.unrealized_paths:
            paths.extend(b.unrealized_paths)
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        p = (p or "").strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def detect_unrealized_path_modality_violations(
    body: str,
    call1: Call1Result,
) -> list[UnrealizedModalityHit]:
    if not body:
        return []
    hits: list[UnrealizedModalityHit] = []
    sentences = re.split(r"(?<=[。．\n])", body)
    paths = unrealized_paths_from_call1(call1)
    for sent in sentences:
        s = sent.strip()
        if len(s) < 4:
            continue
        has_allowed = any(m in s for m in ALLOWED_UNREALIZED_MARKERS)
        strong_realized = ("ことがあった" in s) or ("経験があった" in s)
        if has_allowed and not strong_realized:
            continue
        for path in paths:
            cores = [c for c in _path_cores(path) if len(c) >= 2]
            if not any(c in s for c in cores):
                continue
            for cre in REALIZED_MODALITY_RES:
                if not cre.search(s):
                    continue
                if (
                    re.search(r"(ていたら|なら).*(か|かな|だろう)", s)
                    and "ことがあった" not in s
                ):
                    continue
                # Avoid flagging realized chosen-path sentences that share a short token
                chosen = call1.branch_structure.primary_branch.realized_path or ""
                if chosen and chosen[:6] in s and path[:6] not in s and "ことがあった" not in s:
                    continue
                hits.append(
                    UnrealizedModalityHit(
                        excerpt=s[:160],
                        unrealized_path=path,
                        modality_type=cre.pattern,
                    )
                )
                break
    uniq: list[UnrealizedModalityHit] = []
    seen_ex: set[str] = set()
    for h in hits:
        if h.excerpt in seen_ex:
            continue
        seen_ex.add(h.excerpt)
        uniq.append(h)
    return uniq


def repair_unrealized_path_modality(body: str, call1: Call1Result) -> str:
    out = body
    for hit in detect_unrealized_path_modality_violations(out, call1):
        ex = hit.excerpt
        if ex not in out:
            continue
        repaired = ex
        repaired = re.sub(
            r"([^\s。．\n]{2,80}?)へ行くことがあった",
            r"\1へ進む道は選ばなかった",
            repaired,
        )
        repaired = re.sub(
            r"([^\s。．\n]{2,80}?)に行くことがあった",
            r"\1へ進む道は選ばなかった",
            repaired,
        )
        repaired = re.sub(
            r"([^\s。．\n]{2,80}?)することがあった",
            r"\1という道は選ばなかった",
            repaired,
        )
        repaired = re.sub(
            r"ことがあった。?",
            "道は選ばなかった。",
            repaired,
        )
        if repaired != ex:
            out = out.replace(ex, repaired)
    return out


def approval_blocked_reason(
    call1: Call1Result,
    *,
    source_text: str = "",
) -> str | None:
    """Return human-readable block reason if confirmation must not proceed."""
    contras = detect_material_contradictions(call1, source_text=source_text)
    if contras:
        return (
            "入力内容に矛盾があります。確認事項を直し、追加の質問に答えてから再度お進みください。"
        )
    concreteness = assess_branch_concreteness(call1)
    if not concreteness.ok:
        return (
            "分岐として読むための具体的な時期・出来事が足りません。"
            "追加の質問に答えてから再度お進みください。"
        )
    if call1.status in {
        GenerationStatus.needs_additional_input,
        GenerationStatus.structural_ambiguity,
    }:
        # Allow approve only when residue exists and no contradiction/vague — already handled
        notes = list(call1.validation.notes or [])
        if any(n.startswith("material_contradiction") for n in notes):
            return "入力内容に矛盾があります。修正してから再度お進みください。"
        if any(n.startswith("vague_branch") for n in notes):
            return "分岐の具体情報が不足しています。追加の質問に答えてください。"
    return None
