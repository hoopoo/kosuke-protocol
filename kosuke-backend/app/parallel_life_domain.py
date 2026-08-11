"""Primary-event lock and domain consistency for Parallel Life.

Fact priority (highest first):
1. explicit primary event
2. explicit chosen path
3. explicit unchosen path
4. explicit present question
5. explicit current-life context
6. inferred themes
7. Observatory Lenses
8. seed corpus

Lower layers must never replace higher-priority facts or seize the title.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.models import (
    EditorialContext,
    ParallelLifeClarifications,
    ParallelLifeResult,
)

PrimaryBranchDomain = Literal[
    "family-formation",
    "relationship",
    "education",
    "work",
    "place-migration",
    "creativity",
    "body-health",
    "care-family",
    "business",
    "trust-boundary",
    "other",
]

ChildPolarity = Literal["had_child", "no_child", "unknown"]

# Terms that indicate thematic takeover when they dominate a family case.
_CREATIVITY_DOMINANCE_JA = (
    "創作",
    "小説",
    "執筆",
    "作品をつ",
    "作家",
    "制作",
    "書く習慣",
    "再開する時間",
)
_CREATIVITY_DOMINANCE_EN = (
    "creative work",
    "writing career",
    "artistic practice",
    "resume writing",
    "making works",
    "creative routine",
)

_FAMILY_DOMINANCE_JA = (
    "不妊",
    "授かった",
    "産まれ",
    "出産",
    "息子",
    "娘",
    "子ども",
    "子供",
    "二人目",
    "家族",
    "三人",
    "親",
)
_FAMILY_DOMINANCE_EN = (
    "fertility",
    "child",
    "son",
    "daughter",
    "parent",
    "family",
    "second child",
    "born",
)


class GroundedPrimaryBranch(BaseModel):
    """Mandatory grounded reading of the branch — never from seed/examples."""

    age: str | None = None
    primary_event: str
    chosen_path: str | None = None
    unchosen_path: str | None = None
    secondary_branches: list[str] = Field(default_factory=list)
    present_question: str | None = None
    primary_domain: PrimaryBranchDomain = "other"
    secondary_tags: list[str] = Field(default_factory=list)
    explicit_entities: list[str] = Field(default_factory=list)
    explicit_facts: list[str] = Field(default_factory=list)
    inferred_themes: list[str] = Field(default_factory=list)
    child_polarity: ChildPolarity = "unknown"


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _age_from(text: str, clar: ParallelLifeClarifications) -> str | None:
    if clar.age:
        m = re.search(r"\d{1,3}", clar.age)
        return m.group(0) if m else clar.age.strip() or None
    m = re.search(r"(\d{1,2})\s*歳", text)
    return m.group(1) if m else None


def detect_child_polarity(text: str, clar: ParallelLifeClarifications, *, ja: bool) -> ChildPolarity:
    blob = " ".join(
        [
            text,
            clar.chosen_path or "",
            clar.unchosen_path or "",
        ]
    )
    if ja:
        had = any(
            k in blob
            for k in (
                "授かった",
                "産まれた",
                "生まれた",
                "出産した",
                "息子が",
                "娘が",
                "子どもを持っ",
                "子供を持っ",
                "三人で暮ら",
                "三人家族",
            )
        )
        # Counterfactual / unchosen only — do not treat as had_child
        no = any(
            k in blob
            for k in (
                "子どもを持たない",
                "子供を持たない",
                "持たない人生",
                "子どもは持たず",
            )
        )
        if had and not (no and "授かった" not in blob and "産まれ" not in blob and "生まれ" not in blob):
            return "had_child"
        if no and not had:
            return "no_child"
        return "unknown"
    low = blob.lower()
    if any(k in low for k in ("was born", "had a child", "had a son", "had a daughter", "became a parent")):
        return "had_child"
    if any(k in low for k in ("without children", "no children", "childless", "did not have a child")):
        return "no_child"
    return "unknown"


def classify_primary_domain(
    source_text: str,
    clar: ParallelLifeClarifications,
    editorial: EditorialContext | None = None,
    *,
    ja: bool,
) -> tuple[PrimaryBranchDomain, list[str]]:
    """Classify from explicit user text only — never from UI copy or seeds."""
    # IMPORTANT: do not include editorial *questions*; only answered fields.
    parts = [
        source_text,
        clar.chosen_path or "",
        clar.unchosen_path or "",
        clar.what_remains or "",
    ]
    if editorial:
        for field in (
            editorial.life_before,
            editorial.changes_after,
            editorial.later_branches,
            editorial.current_life_context,
            editorial.present_influence,
            editorial.meaning_of_unchosen_life,
        ):
            if field:
                parts.append(field)
    blob = " ".join(parts)
    tags: list[str] = []

    fertility = any(k in blob for k in ("不妊", "治療を経", "fertility", "treatment"))
    childbirth = any(
        k in blob for k in ("授かった", "産まれ", "生まれた", "出産", "born", "gave birth")
    )
    parenthood = any(k in blob for k in ("息子", "娘", "三人", "親子", "son", "daughter", "parent"))
    second = any(k in blob for k in ("二人目", "2人目", "第二子", "second child", "another child"))

    if fertility or childbirth or (parenthood and any(k in blob for k in ("子ども", "子供", "child"))):
        if fertility:
            tags.append("fertility-treatment")
        if childbirth or parenthood:
            tags.append("parenthood")
        if second:
            tags.append("second-child")
        tags.extend(["intimacy", "body", "family-continuity"])
        return "family-formation", tags

    if any(k in blob for k in ("介護", "caregiving", "care for")):
        return "care-family", ["care"]

    if any(k in blob for k in ("結婚", "彼氏", "彼女", "恋愛", "交際", "marry", "relationship", "boyfriend", "girlfriend")):
        return "relationship", ["intimacy"]

    if any(k in blob for k in ("大学", "受験", "進学", "合格", "university", "college", "exam")):
        return "education", ["education-employment"]

    # Creativity only if the explicit EVENT is about creative work — not UI wording.
    creative_event = any(
        k in blob
        for k in (
            "創作を",
            "小説を",
            "音楽を",
            "絵を",
            "作家",
            "執筆",
            "creative practice",
            "stopped writing",
            "left writing",
            "abandoned art",
        )
    )
    if creative_event:
        return "creativity", ["creativity"]

    if any(k in blob for k in ("会社", "仕事", "就職", "転職", "退職", "経営", "job", "career", "resign", "company")):
        if any(k in blob for k in ("経営", "自社", "own company", "self-employ")):
            return "business", ["work"]
        return "work", ["work"]

    if any(k in blob for k in ("東京", "海外", "地元", "移住", "abroad", "hometown", "moved")):
        return "place-migration", ["city"]

    if any(k in blob for k in ("病気", "身体", "治療", "health", "illness", "body")):
        # Avoid stealing fertility-treatment already classified above
        return "body-health", ["body"]

    return "other", []


def extract_primary_event(
    source_text: str,
    clar: ParallelLifeClarifications,
    *,
    ja: bool,
    domain: PrimaryBranchDomain,
) -> str:
    """Extract primary_event from explicit input only."""
    text = source_text
    if domain == "family-formation":
        if ja:
            if "不妊" in text and ("授かった" in text or "産まれ" in text or "生まれ" in text):
                return "不妊治療を経て子どもを授かった"
            if "授かった" in text:
                return "子どもを授かった"
            if "産まれ" in text or "生まれた" in text:
                return "子どもが生まれた"
            if clar.chosen_path and any(k in clar.chosen_path for k in ("息子", "娘", "三人", "家族")):
                return _clean(clar.chosen_path)
            return "家族形成をめぐる分岐"
        if "fertility" in text.lower() or "treatment" in text.lower():
            return "having a child after fertility treatment"
        return "becoming a parent"
    if clar.chosen_path:
        return _clean(clar.chosen_path)
    # First sentence of source as last resort — still explicit user text
    first = re.split(r"[。\n.]", text)[0].strip()
    return first[:80] if first else ("人生の大きな分岐" if ja else "a major life branch")


def extract_grounded_primary_branch(
    source_text: str,
    clar: ParallelLifeClarifications,
    editorial: EditorialContext | None = None,
    *,
    ja: bool,
) -> GroundedPrimaryBranch:
    domain, tags = classify_primary_domain(source_text, clar, editorial, ja=ja)
    child_pol = detect_child_polarity(source_text, clar, ja=ja)
    primary_event = extract_primary_event(source_text, clar, ja=ja, domain=domain)

    secondary: list[str] = []
    blob = source_text + " " + (clar.what_remains or "")
    if editorial and editorial.later_branches:
        secondary.append(_clean(editorial.later_branches))
    if any(k in blob for k in ("二人目", "2人目", "第二子", "second child")):
        secondary.append(
            "二人目の子どもを持つかどうかという、その後に生まれた分岐"
            if ja
            else "whether to have a second child"
        )

    present = None
    if clar.what_remains:
        present = _clean(clar.what_remains)
    elif any(k in blob for k in ("二人目", "second child")):
        present = (
            "二人目がいたらどうだったかという問い"
            if ja
            else "what if there had been a second child"
        )

    entities: list[str] = []
    for ent in ("妻", "夫", "息子", "娘", "嫁", "spouse", "son", "daughter"):
        if ent in source_text or (clar.chosen_path and ent in clar.chosen_path):
            entities.append(ent)

    facts: list[str] = [primary_event]
    if clar.chosen_path:
        facts.append(_clean(clar.chosen_path))
    if clar.unchosen_path:
        facts.append(_clean(clar.unchosen_path))

    # Inferred themes are secondary — never include creativity unless domain is creativity
    themes: list[str] = list(tags)
    if domain == "creativity":
        themes.append("creativity")

    return GroundedPrimaryBranch(
        age=_age_from(source_text, clar),
        primary_event=primary_event,
        chosen_path=_clean(clar.chosen_path) if clar.chosen_path else None,
        unchosen_path=_clean(clar.unchosen_path) if clar.unchosen_path else None,
        secondary_branches=secondary,
        present_question=present,
        primary_domain=domain,
        secondary_tags=tags,
        explicit_entities=entities,
        explicit_facts=facts,
        inferred_themes=themes,
        child_polarity=child_pol,
    )


def _section_blob(result: ParallelLifeResult) -> str:
    return " ".join(
        [
            result.title,
            result.subtitle,
            result.branch_point,
            result.chosen_path,
            result.unchosen_life,
            result.residue,
            result.closing,
            result.cross_lens_synthesis,
            *result.lost,
            *result.protected,
            *result.rebranch,
            *(layer.body for layer in result.observatory_layers),
        ]
    )


def _count_hits(text: str, needles: tuple[str, ...]) -> int:
    return sum(1 for n in needles if n in text)


def domain_consistency_issues(
    result: ParallelLifeResult,
    grounded: GroundedPrimaryBranch,
    *,
    ja: bool,
) -> list[str]:
    """Return human-readable issues if the result drifts from primary_domain."""
    issues: list[str] = []
    blob = _section_blob(result)
    title = result.title or ""

    if grounded.primary_domain == "family-formation":
        creat = _CREATIVITY_DOMINANCE_JA if ja else _CREATIVITY_DOMINANCE_EN
        family = _FAMILY_DOMINANCE_JA if ja else _FAMILY_DOMINANCE_EN
        creat_hits = _count_hits(blob, creat)
        family_hits = _count_hits(blob, family)
        title_creat = _count_hits(title, creat)
        if title_creat > 0:
            issues.append(f"title_creativity_takeover:{title}")
        if creat_hits >= 3 and creat_hits > family_hits:
            issues.append(f"creativity_dominates_sections:{creat_hits}>{family_hits}")
        if family_hits == 0:
            issues.append("missing_family_formation_markers")
        # Rejection titles that invert had_child
        if grounded.child_polarity == "had_child":
            bad_title = any(
                k in title
                for k in (
                    "離れた",
                    "残らなかった",
                    "選ばなかった",
                    "続けなかった",
                    "Not Chosen",
                    "Leaving",
                )
            )
            if bad_title and not any(k in title for k in ("二人目", "その先", "授かった", "三人", "息子", "隣")):
                issues.append(f"had_child_rejection_title:{title}")

    if grounded.primary_domain == "creativity":
        family = _FAMILY_DOMINANCE_JA if ja else _FAMILY_DOMINANCE_EN
        creat = _CREATIVITY_DOMINANCE_JA if ja else _CREATIVITY_DOMINANCE_EN
        if _count_hits(blob, family) >= 4 and _count_hits(blob, creat) <= 1:
            if not any(k in grounded.primary_event for k in ("不妊", "授かった", "child", "fertility")):
                issues.append("family_dominates_creativity_case")

    if grounded.primary_domain == "education":
        if any(k in title for k in ("不妊", "授かった", "創作に残ら")):
            issues.append(f"education_title_crossover:{title}")

    return issues


def validate_domain_consistency(
    result: ParallelLifeResult,
    grounded: GroundedPrimaryBranch,
    *,
    ja: bool,
) -> None:
    issues = domain_consistency_issues(result, grounded, ja=ja)
    if issues:
        raise ValueError("domain_consistency_failed:" + ",".join(issues))


def family_formation_title(grounded: GroundedPrimaryBranch, *, ja: bool, seed: int = 0) -> tuple[str, str]:
    """Domain-locked titles for family-formation — never rejection-of-parenthood frames."""
    age = grounded.age
    age_label = f"{age}歳" if age and ja else (age or "")
    if ja:
        pool = [
            ("子どもを授かった、その先", "叶った願いのそばに、まだ開いている分岐がある。"),
            ("三人になった年" if not age_label else f"三人になった{age_label}", "実現した家族の隣に、次の問いが残っている。"),
            ("授かったあとに残った問い", "かなった願いの隣に、家族の形をめぐる問いがある。"),
            ("息子が生まれたあとに開いた分岐", "一次の分岐のあとで、別の分岐が見えてきた。"),
        ]
        if grounded.child_polarity != "had_child":
            pool = [
                ("家族をめぐる分岐", "選んだ道と選ばなかった道が、同じ生活のなかで並んでいる。"),
            ] + pool
        title, subtitle = pool[seed % len(pool)]
        return title, subtitle
    pool = [
        ("After Receiving a Child", "Beside a wish fulfilled, another branch remains open."),
        ("The Family of Three", "What was realized quietly brought the next question."),
        ("The Branch That Opened After Birth", "A later question became visible only afterward."),
    ]
    return pool[seed % len(pool)]


# Map primary_domain → heuristic topic category used by existing pools
DOMAIN_TO_TOPIC_CATEGORY: dict[str, str] = {
    "family-formation": "family_formation",
    "relationship": "relationship",
    "education": "education",
    "work": "work",
    "place-migration": "place",
    "creativity": "creativity",
    "body-health": "default",
    "care-family": "care",
    "business": "work",
    "trust-boundary": "default",
    "other": "default",
}


# Seed domains allowed per primary domain (creativity seeds blocked for family)
ALLOWED_SEED_DOMAINS: dict[str, set[str]] = {
    "family-formation": {
        "timing",
        "unchosen-path",
        "constraint",
        "continuity",
        "care",
        "possibility",
        "intimacy",
        "stability",
        "historical-conditions",
        "recovery-vs-reversal",
        "belonging",
        "work",
    },
    "creativity": {
        "timing",
        "unchosen-path",
        "unrealized-creativity",
        "possibility",
        "recovery-vs-reversal",
        "autonomy",
        "constraint",
    },
    "education": {
        "timing",
        "unchosen-path",
        "constraint",
        "possibility",
        "historical-conditions",
        "belonging",
        "work",
    },
    "work": {"timing", "unchosen-path", "constraint", "stability", "work", "possibility"},
    "place-migration": {"timing", "migration", "return", "belonging", "possibility"},
    "relationship": {"timing", "intimacy", "autonomy", "unchosen-path", "possibility"},
}


def seed_domains_for(primary_domain: str) -> set[str] | None:
    return ALLOWED_SEED_DOMAINS.get(primary_domain)
