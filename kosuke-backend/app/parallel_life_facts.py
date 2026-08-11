"""Explicit fact extraction and polarity protection for Parallel Life.

Heuristic templates historically assumed a rejection / not-chosen polarity
(e.g. education = failed first-choice university). When the user writes
「第一志望の早稲田大学第一文学部に受かった」, that assumption inverted the
source fact. This module extracts only explicit facts, records provenance,
and rejects generated text that contradicts them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.models import ParallelLifeClarifications, ParallelLifeResult

Provenance = Literal["explicit_user_input", "clarification_answer", "inferred"]
EducationPolarity = Literal["admitted", "rejected", "unknown"]
PlacePolarity = Literal["stayed", "left", "unknown"]
WorkPolarity = Literal["resigned", "stayed", "unknown"]
MarriagePolarity = Literal["married", "not_married", "unknown"]


@dataclass(frozen=True)
class FactItem:
    text: str
    provenance: Provenance


@dataclass
class ParallelLifeFacts:
    age: str | None = None
    explicit_events: list[FactItem] = field(default_factory=list)
    chosen_path: FactItem | None = None
    unchosen_path: FactItem | None = None
    locations: list[FactItem] = field(default_factory=list)
    institutions: list[FactItem] = field(default_factory=list)
    people_or_relationships: list[FactItem] = field(default_factory=list)
    constraints: list[FactItem] = field(default_factory=list)
    unresolved_question: FactItem | None = None
    education_polarity: EducationPolarity = "unknown"
    place_polarity: PlacePolarity = "unknown"
    work_polarity: WorkPolarity = "unknown"
    marriage_polarity: MarriagePolarity = "unknown"

    @property
    def polarity_known(self) -> bool:
        return any(
            p != "unknown"
            for p in (
                self.education_polarity,
                self.place_polarity,
                self.work_polarity,
                self.marriage_polarity,
            )
        )

    def explicit_texts(self) -> list[str]:
        """Texts that may be treated as factual (never inferred)."""
        items: list[FactItem] = []
        items.extend(self.explicit_events)
        if self.chosen_path:
            items.append(self.chosen_path)
        if self.unchosen_path:
            items.append(self.unchosen_path)
        items.extend(self.locations)
        items.extend(self.institutions)
        items.extend(self.people_or_relationships)
        items.extend(self.constraints)
        if self.unresolved_question:
            items.append(self.unresolved_question)
        return [i.text for i in items if i.provenance != "inferred"]

    def primary_institution(self) -> str | None:
        for item in self.institutions:
            if item.provenance != "inferred":
                return item.text
        return None


# --- Extraction helpers -------------------------------------------------------

_JA_INSTITUTION_RE = __import__("re").compile(
    r"([\u4e00-\u9fffA-Za-z0-9]{2,20}(?:大学|高校|専門学校|学院))"
    r"(?:の)?([\u4e00-\u9fffA-Za-z0-9]{0,20}(?:学部|学科|専攻))?"
)
_EN_UNIVERSITY_RE = __import__("re").compile(
    r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}\s+(?:University|College|School))\b"
)
_JA_LOCATION_RE = __import__("re").compile(
    r"(東京|京都|大阪|名古屋|福岡|札幌|横浜|神戸|仙台|広島|沖縄|海外|地元|故郷|"
    r"アメリカ|米国|イギリス|英国|フランス|ドイツ|中国|韓国|台湾)"
)
_EN_LOCATION_RE = __import__("re").compile(
    r"\b(Tokyo|Kyoto|Osaka|Nagoya|Fukuoka|Sapporo|Yokohama|abroad|overseas|"
    r"hometown|America|the US|Britain|France|Germany|China|Korea|Taiwan)\b",
    __import__("re").IGNORECASE,
)

_JA_ADMITTED = ("受かった", "受かり", "合格した", "合格し", "合格する", "合格して", "入学した", "進学した")
_JA_REJECTED = ("落ちた", "落ちて", "不合格", "不合格だった", "届かなかった", "落とした")
_EN_ADMITTED = (
    "got in",
    "got accepted",
    "was accepted",
    "accepted to",
    "accepted into",
    "admitted to",
    "admitted into",
    "passed the exam",
    "enrolled at",
    "enrolled in",
)
_EN_REJECTED = (
    "rejected",
    "did not get in",
    "didn't get in",
    "failed the exam",
    "was not accepted",
    "wasn't accepted",
    "turned down by",
)

_JA_STAYED = ("に残った", "へ残った", "残留した", "留まった", "とどまった", "日本に残った", "東京に残った")
_JA_LEFT = (
    "を離れた",
    "へ帰った",
    "に帰った",
    "出て行っ",
    "引っ越した",
    "移住した",
    "海外へ行った",
    "海外に行った",
    "田舎へ帰",
    "地元へ帰",
    "故郷へ帰",
)
_EN_STAYED = ("stayed in", "stayed at", "remained in", "did not leave", "didn't leave")
_EN_LEFT = ("left ", "moved away", "moved back", "moved to", "relocated", "went abroad", "returned home")

_JA_RESIGNED = ("を辞めた", "をやめた", "退職した", "退職し", "会社を出")
_JA_WORK_STAYED = ("会社に残った", "会社に残って", "仕事を続け", "勤め続け", "働き続け")
_EN_RESIGNED = ("quit", "resigned", "left the company", "left my job", "stopped working")
_EN_WORK_STAYED = ("stayed at the company", "stayed in the job", "kept the job", "remained employed")

_JA_MARRIED = ("結婚した", "結婚して", "結婚する")
_JA_NOT_MARRIED = ("結婚しなかった", "結婚しなかった", "結婚せず", "未婚のまま")
_EN_MARRIED = ("got married", "married ", "we married")
_EN_NOT_MARRIED = ("did not marry", "didn't marry", "never married", "stayed unmarried")


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(p.lower() in lowered for p in phrases)


def _first_hit(text: str, phrases: tuple[str, ...]) -> str | None:
    lowered = text.lower()
    for p in phrases:
        if p.lower() in lowered:
            return p
    return None


# Counterfactual / hypothetical clauses must not set polarity
# (e.g. 「あのまま東京に残っていたら」 is not evidence of staying).
_JA_COUNTERFACTUAL_RE = __import__("re").compile(
    r"[^。．\n]*?(?:たら|たなら|であれば|だったら|ていれば|ていたら|していれば)[^。．\n]*[。．\n]?"
)
_EN_COUNTERFACTUAL_RE = __import__("re").compile(
    r"(?i)(?:if\s+i\s+had|if\s+i'd|had\s+i\s+|would\s+have|might\s+have|could\s+have|"
    r"what\s+if|wonder\s+what\s+if)[^.!?\n]*[.!?\n]?"
)


def _factual_surface(text: str, *, ja: bool) -> str:
    """Remove counterfactual clauses before polarity detection."""
    if not text:
        return ""
    cleaned = text
    pattern = _JA_COUNTERFACTUAL_RE if ja else _EN_COUNTERFACTUAL_RE
    cleaned = pattern.sub("。", cleaned)
    return cleaned


def extract_parallel_life_facts(
    source_text: str,
    clarifications: ParallelLifeClarifications | None = None,
    *,
    ja: bool,
) -> ParallelLifeFacts:
    """Extract a structured fact layer. Only explicit_user_input and
    clarification_answer may later be treated as factual; inferred is for
    soft hints and must never overwrite explicit polarity."""
    clar = clarifications or ParallelLifeClarifications()
    text = (source_text or "").strip()
    facts = ParallelLifeFacts()

    if clar.age and clar.age.strip():
        facts.age = clar.age.strip()
        facts.explicit_events.append(
            FactItem(text=f"age:{clar.age.strip()}", provenance="clarification_answer")
        )

    # Institutions / named entities
    if ja:
        for match in _JA_INSTITUTION_RE.finditer(text):
            school = match.group(1)
            faculty = match.group(2) or ""
            facts.institutions.append(FactItem(school, "explicit_user_input"))
            if faculty:
                facts.institutions.append(FactItem(faculty, "explicit_user_input"))
    else:
        for match in _EN_UNIVERSITY_RE.finditer(text):
            facts.institutions.append(FactItem(match.group(1), "explicit_user_input"))

    # Locations
    loc_re = _JA_LOCATION_RE if ja else _EN_LOCATION_RE
    for match in loc_re.finditer(text):
        loc = match.group(1)
        if not any(existing.text == loc for existing in facts.locations):
            facts.locations.append(FactItem(loc, "explicit_user_input"))

    # Clarification-derived chosen / unchosen / constraints
    if clar.chosen_path and clar.chosen_path.strip():
        facts.chosen_path = FactItem(clar.chosen_path.strip(), "clarification_answer")
    if clar.unchosen_path and clar.unchosen_path.strip():
        facts.unchosen_path = FactItem(clar.unchosen_path.strip(), "clarification_answer")
    if clar.constraints and clar.constraints.strip():
        facts.constraints.append(FactItem(clar.constraints.strip(), "clarification_answer"))
    if clar.what_remains and clar.what_remains.strip():
        facts.unresolved_question = FactItem(clar.what_remains.strip(), "clarification_answer")

    # Polarity — prefer explicit source text; clarifications may reinforce
    # but never overwrite an opposite explicit polarity. Counterfactual
    # clauses ("残っていたら", "if I had stayed") are stripped first.
    combined = text
    if clar.chosen_path:
        combined = f"{combined}\n{clar.chosen_path}"
    factual = _factual_surface(combined, ja=ja)

    facts.education_polarity = _detect_education_polarity(factual, ja)
    facts.place_polarity = _detect_place_polarity(factual, ja)
    facts.work_polarity = _detect_work_polarity(factual, ja)
    facts.marriage_polarity = _detect_marriage_polarity(factual, ja)

    # Explicit event phrases (for provenance + contradiction checks).
    # Use the factual surface so counterfactuals are not recorded as events.
    if ja:
        hit = _first_hit(factual, _JA_ADMITTED + _JA_REJECTED)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
        hit = _first_hit(factual, _JA_STAYED + _JA_LEFT)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
        hit = _first_hit(factual, _JA_RESIGNED + _JA_WORK_STAYED)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
        hit = _first_hit(factual, _JA_MARRIED + _JA_NOT_MARRIED)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
    else:
        hit = _first_hit(factual, _EN_ADMITTED + _EN_REJECTED)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
        hit = _first_hit(factual, _EN_STAYED + _EN_LEFT)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
        hit = _first_hit(factual, _EN_RESIGNED + _EN_WORK_STAYED)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))
        hit = _first_hit(factual, _EN_MARRIED + _EN_NOT_MARRIED)
        if hit:
            facts.explicit_events.append(FactItem(hit, "explicit_user_input"))

    # If admission is explicit and no chosen_path clarification, treat the
    # named institution (or "進学") as the chosen path — never invent a
    # rejection path as chosen.
    if facts.chosen_path is None and facts.education_polarity == "admitted":
        inst = facts.primary_institution()
        label = inst if inst else ("進学" if ja else "that admission")
        facts.chosen_path = FactItem(label, "explicit_user_input")
    if facts.chosen_path is None and facts.education_polarity == "rejected":
        facts.unchosen_path = facts.unchosen_path or FactItem(
            facts.primary_institution() or ("第一志望" if ja else "the first-choice school"),
            "inferred",
        )

    return facts


def _detect_education_polarity(text: str, ja: bool) -> EducationPolarity:
    if ja:
        admitted = _contains_any(text, _JA_ADMITTED)
        rejected = _contains_any(text, _JA_REJECTED)
    else:
        admitted = _contains_any(text, _EN_ADMITTED)
        rejected = _contains_any(text, _EN_REJECTED)
    if admitted and not rejected:
        return "admitted"
    if rejected and not admitted:
        return "rejected"
    return "unknown"


def _detect_place_polarity(text: str, ja: bool) -> PlacePolarity:
    if ja:
        stayed = _contains_any(text, _JA_STAYED)
        left = _contains_any(text, _JA_LEFT)
    else:
        stayed = _contains_any(text, _EN_STAYED)
        left = _contains_any(text, _EN_LEFT)
    if stayed and not left:
        return "stayed"
    if left and not stayed:
        return "left"
    return "unknown"


def _detect_work_polarity(text: str, ja: bool) -> WorkPolarity:
    if ja:
        resigned = _contains_any(text, _JA_RESIGNED)
        stayed = _contains_any(text, _JA_WORK_STAYED)
    else:
        resigned = _contains_any(text, _EN_RESIGNED)
        stayed = _contains_any(text, _EN_WORK_STAYED)
    if resigned and not stayed:
        return "resigned"
    if stayed and not resigned:
        return "stayed"
    return "unknown"


def _detect_marriage_polarity(text: str, ja: bool) -> MarriagePolarity:
    if ja:
        married = _contains_any(text, _JA_MARRIED) and not _contains_any(text, _JA_NOT_MARRIED)
        not_married = _contains_any(text, _JA_NOT_MARRIED)
    else:
        married = _contains_any(text, _EN_MARRIED) and not _contains_any(text, _EN_NOT_MARRIED)
        not_married = _contains_any(text, _EN_NOT_MARRIED)
    if married and not not_married:
        return "married"
    if not_married and not married:
        return "not_married"
    return "unknown"


# --- Contradiction detection --------------------------------------------------
#
# Each rule: if the source has `source_markers`, the generated corpus must not
# contain any of `forbidden_markers`.

@dataclass(frozen=True)
class _PolarityRule:
    name: str
    source_markers: tuple[str, ...]
    forbidden_markers: tuple[str, ...]


_JA_POLARITY_RULES: tuple[_PolarityRule, ...] = (
    _PolarityRule(
        "education_admitted",
        ("受かった", "受かり", "合格した", "合格し", "入学した"),
        (
            "落ちた",
            "落ちて",
            "不合格",
            "届かなかった",
            "別の大学へ進",
            "別の大学に進",
            "進学先を離れ",
            "進学先をあきら",
            "進学先を手放",
            "戻らなかった進学",
            "選ばなかった進学",
            "第一志望に賭け続ける",
            "未確定の進学先",
        ),
    ),
    _PolarityRule(
        "education_rejected",
        ("落ちた", "落ちて", "不合格", "届かなかった"),
        ("受かった", "合格した", "第一志望に進学した", "志望校に入学した"),
    ),
    _PolarityRule(
        "place_stayed",
        ("に残った", "へ残った", "留まった", "とどまった"),
        # Assertive past/opposite claims only — not hypothetical 「離れる道」.
        ("を離れた", "へ帰った", "に帰った", "引っ越した", "移住した", "出て行った"),
    ),
    _PolarityRule(
        "place_left",
        ("を離れた", "へ帰った", "に帰った", "引っ越した", "移住した", "田舎へ帰", "地元へ帰"),
        ("に残った", "に留まった", "にとどまった", "残ることだった"),
    ),
    _PolarityRule(
        "work_resigned",
        ("を辞めた", "をやめた", "退職した"),
        ("会社に残った", "仕事を続けた", "勤め続けた", "働き続けた", "続けた仕事", "残ることだった"),
    ),
    _PolarityRule(
        "work_stayed",
        ("会社に残", "仕事を続け", "勤め続け", "働き続け"),
        (
            "会社を辞めた",
            "仕事をやめた",
            "退職した",
            "戻らなかった仕事",
            "選ばなかった仕事",
            "続けなかった仕事",
            "仕事を手放した",
            "仕事をあきらめた",
            "離れることだった",
        ),
    ),
    _PolarityRule(
        "marriage_yes",
        ("結婚した",),
        (
            "結婚しなかった",
            "結婚せず",
            "未婚のまま",
            "戻らなかった恋愛",
            "選ばなかった恋愛",
            "続けなかった恋愛",
            "結婚を手放",
            "結婚をあきら",
        ),
    ),
    _PolarityRule(
        "marriage_no",
        ("結婚しなかった", "結婚せず"),
        ("結婚した日", "結婚してから", "配偶者と", "選んだ結婚"),
    ),
)

_EN_POLARITY_RULES: tuple[_PolarityRule, ...] = (
    _PolarityRule(
        "education_admitted",
        ("got in", "got accepted", "was accepted", "accepted to", "accepted into", "admitted to", "enrolled"),
        (
            "rejected",
            "did not get in",
            "didn't get in",
            "failed the exam",
            "was not accepted",
            "went to another university",
            "another university",
            "left the school",
            "gave up on the school",
            "not returned to",
            "not choosing the university",
        ),
    ),
    _PolarityRule(
        "education_rejected",
        ("rejected", "did not get in", "didn't get in", "failed the exam", "was not accepted"),
        ("got in", "was accepted", "admitted to", "enrolled at the first-choice"),
    ),
    _PolarityRule(
        "place_stayed",
        ("stayed in", "stayed at", "remained in", "did not leave", "didn't leave"),
        ("left tokyo", "left japan", "moved away", "relocated away"),
    ),
    _PolarityRule(
        "place_left",
        ("left ", "moved away", "moved to", "relocated"),
        ("stayed in tokyo", "stayed in japan", "remained in tokyo"),
    ),
    _PolarityRule(
        "work_resigned",
        ("quit", "resigned", "left the company", "left my job"),
        ("stayed at the company", "kept the job", "remained employed", "continued at the company"),
    ),
    _PolarityRule(
        "work_stayed",
        ("stayed at the company", "kept the job", "remained employed", "stayed in the job"),
        ("quit the company", "resigned", "left the company"),
    ),
    _PolarityRule(
        "marriage_yes",
        ("got married", "we married"),
        ("did not marry", "didn't marry", "never married", "stayed unmarried"),
    ),
    _PolarityRule(
        "marriage_no",
        ("did not marry", "didn't marry", "never married"),
        ("got married", "after marriage", "spouse"),
    ),
)


def _result_corpus(result: ParallelLifeResult) -> str:
    parts = [
        result.title,
        result.subtitle,
        result.branch_point,
        result.chosen_path,
        result.unchosen_life,
        result.residue,
        result.cross_lens_synthesis,
        result.closing,
        *result.lost,
        *result.protected,
        *result.rebranch,
        *(layer.body for layer in result.observatory_layers),
        *(layer.title for layer in result.observatory_layers),
    ]
    return "\n".join(p for p in parts if p)


def validate_factual_consistency(
    source_text: str,
    result: ParallelLifeResult,
    facts: ParallelLifeFacts | None = None,
    *,
    ja: bool,
) -> None:
    """Raise ValueError if generated text inverts an explicit source fact."""
    source = _factual_surface(source_text or "", ja=ja)
    corpus = _result_corpus(result)
    probe_source = source.lower()
    probe_corpus = corpus.lower() if not ja else corpus

    rules = _JA_POLARITY_RULES if ja else _EN_POLARITY_RULES
    for rule in rules:
        if not any(m.lower() in probe_source for m in rule.source_markers):
            continue
        for bad in rule.forbidden_markers:
            needle = bad.lower() if not ja else bad
            hay = probe_corpus
            if needle in hay:
                raise ValueError(
                    f"Factual polarity inversion ({rule.name}): "
                    f"source implies {rule.source_markers[0]!r} but output contains {bad!r}"
                )

    # Named institutions must not be replaced by a contradictory generic
    # "another university / 別の大学" claim when admission is explicit.
    facts = facts or extract_parallel_life_facts(source_text, ja=ja)
    if facts.education_polarity == "admitted":
        if ja and ("別の大学" in corpus or "他の大学へ" in corpus or "他大学へ" in corpus):
            raise ValueError(
                "Factual contradiction: admission to a named/first-choice school "
                "must not be narrated as going to another university"
            )
        if not ja and ("another university" in probe_corpus or "a different university" in probe_corpus):
            raise ValueError(
                "Factual contradiction: admission must not be narrated as "
                "attending another university"
            )


def facts_prompt_block(facts: ParallelLifeFacts, *, ja: bool) -> str:
    """Serialize explicit facts for the LLM system/user prompt."""
    lines: list[str] = []
    if ja:
        lines.append("【明示された事実】（これらを反転・否定してはならない）")
        if facts.education_polarity == "admitted":
            lines.append("- 進学 polarity: 合格 / 受かった（不合格・落ちた・別の大学へ進んだと書いてはならない）")
        elif facts.education_polarity == "rejected":
            lines.append("- 進学 polarity: 不合格 / 落ちた（合格した・入学したと書いてはならない）")
        if facts.place_polarity == "stayed":
            lines.append("- 場所 polarity: 残った（離れたと書いてはならない）")
        elif facts.place_polarity == "left":
            lines.append("- 場所 polarity: 離れた（残ったと書いてはならない）")
        if facts.work_polarity == "resigned":
            lines.append("- 仕事 polarity: 辞めた（続けたと書いてはならない）")
        elif facts.work_polarity == "stayed":
            lines.append("- 仕事 polarity: 残った / 続けた（辞めたと書いてはならない）")
        if facts.marriage_polarity == "married":
            lines.append("- 結婚 polarity: 結婚した（しなかったと書いてはならない）")
        elif facts.marriage_polarity == "not_married":
            lines.append("- 結婚 polarity: 結婚しなかった（したと書いてはならない）")
        for inst in facts.institutions:
            if inst.provenance != "inferred":
                lines.append(f"- 固有名: {inst.text}（意味を変えてはならない。省略は可）")
        for loc in facts.locations:
            if loc.provenance != "inferred":
                lines.append(f"- 場所名: {loc.text}")
        if facts.chosen_path and facts.chosen_path.provenance != "inferred":
            lines.append(f"- 選んだ道: {facts.chosen_path.text}")
        if facts.unchosen_path and facts.unchosen_path.provenance != "inferred":
            lines.append(f"- 選ばなかった道: {facts.unchosen_path.text}")
        if not facts.polarity_known:
            lines.append(
                "- polarity が不明な場合は具体的な方向を推測しない。"
                "「その時、進学をめぐる大きな分岐があった。」のような中立表現を使う。"
            )
    else:
        lines.append("[Explicit facts] (do not invert or contradict these)")
        if facts.education_polarity == "admitted":
            lines.append("- education polarity: admitted / got in (do not write rejection or another university)")
        elif facts.education_polarity == "rejected":
            lines.append("- education polarity: rejected (do not write admission to that school)")
        if facts.place_polarity == "stayed":
            lines.append("- place polarity: stayed (do not write left)")
        elif facts.place_polarity == "left":
            lines.append("- place polarity: left (do not write stayed)")
        if facts.work_polarity == "resigned":
            lines.append("- work polarity: resigned (do not write stayed in the job)")
        elif facts.work_polarity == "stayed":
            lines.append("- work polarity: stayed (do not write resigned)")
        if facts.marriage_polarity == "married":
            lines.append("- marriage polarity: married (do not write did not marry)")
        elif facts.marriage_polarity == "not_married":
            lines.append("- marriage polarity: did not marry (do not write got married)")
        for inst in facts.institutions:
            if inst.provenance != "inferred":
                lines.append(f"- named institution: {inst.text} (may omit; must not alter meaning)")
        for loc in facts.locations:
            if loc.provenance != "inferred":
                lines.append(f"- location: {loc.text}")
        if facts.chosen_path and facts.chosen_path.provenance != "inferred":
            lines.append(f"- chosen path: {facts.chosen_path.text}")
        if facts.unchosen_path and facts.unchosen_path.provenance != "inferred":
            lines.append(f"- unchosen path: {facts.unchosen_path.text}")
        if not facts.polarity_known:
            lines.append(
                "- If polarity is unclear, do not invent a direction. "
                "Use neutral language such as: "
                "'At that time there was a major branch around education.'"
            )
    return "\n".join(lines)
