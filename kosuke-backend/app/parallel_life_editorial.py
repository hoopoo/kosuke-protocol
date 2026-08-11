"""Editorial Edition (depth=editorial) for Parallel Life.

This is a separate generation mode from Standard — not a longer template.
It extracts a multi-branch structure, grounds on explicit facts, and produces
a long-form editorial essay. Legacy depth value ``deep`` aliases to
``editorial``.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from app.models import (
    ClarificationQuestion,
    EditorialBranchStructure,
    EditorialContext,
    NormalizedEditorialContext,
    ObservatoryLayer,
    ParallelLifeClarifications,
    ParallelLifeEditorialRequest,
    ParallelLifeEditorialResponse,
    ParallelLifeResult,
)
from app.observatory_lenses import OBSERVATORY_LENSES, select_observatory_lenses
from app.parallel_life_editorial_normalize import (
    normalize_editorial_context,
    postprocess_editorial_result,
    standard_interpretation_summary,
)
from app.parallel_life_facts import (
    extract_parallel_life_facts,
    validate_factual_consistency,
)

_CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def normalize_depth(depth: str | None) -> str:
    """Map legacy ``deep`` to ``editorial``; unknown values become standard."""
    if not depth:
        return "standard"
    d = depth.lower().strip()
    if d in ("editorial", "deep"):
        return "editorial"
    if d == "standard":
        return "standard"
    return "standard"


def _is_ja(language: str, text: str = "") -> bool:
    if language and language.lower().startswith("ja"):
        return True
    return bool(_CJK_RE.search(text))


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


# --- Editorial clarification questions ---------------------------------------

_EDITORIAL_QUESTIONS_JA: list[tuple[str, str]] = [
    ("life_before", "その分岐の前、どんな生活をしていましたか。"),
    ("changes_after", "その選択によって、その後の生活はどう変わりましたか。"),
    ("unseen_conditions", "当時は見えていなかった条件がありますか。"),
    ("present_influence", "今の暮らしや仕事に、その選択の影響は残っていますか。"),
    ("meaning_of_unchosen_life", "選ばなかった人生に、何を託していると思いますか。"),
    ("later_branches", "その分岐のあとに、別の分岐が生まれましたか。"),
    ("current_life_context", "現在の家族、仕事、身体、場所とのつながりを教えてください。"),
    ("social_connection", "この経験を社会の変化と重ねるなら、何が関係していると思いますか。"),
]

_EDITORIAL_QUESTIONS_EN: list[tuple[str, str]] = [
    ("life_before", "What did daily life look like before this branch?"),
    ("changes_after", "How did life change after the choice you made?"),
    ("unseen_conditions", "Were there conditions you could not see clearly at the time?"),
    ("present_influence", "Does that choice still shape your present life or work?"),
    ("meaning_of_unchosen_life", "What do you think you place in the unchosen life now?"),
    ("later_branches", "Did another branch appear after this one?"),
    ("current_life_context", "Tell us about present family, work, body, or place."),
    ("social_connection", "If you place this experience against social change, what seems connected?"),
]


def _already_known_editorial_ids(
    source_text: str,
    clar: ParallelLifeClarifications,
    context: EditorialContext | None,
    answered_ids: list[str],
) -> set[str]:
    known = set(answered_ids)
    if clar.constraints:
        known.add("unseen_conditions")
    # what_remains answers "what remains now" — close enough to present_influence
    if clar.what_remains:
        known.add("present_influence")
    # Do not treat unchosen_path as an answer to meaning_of_unchosen_life;
    # naming the path is not the same as saying what it holds now.
    if any(k in source_text for k in ("その前", "以前は", "before that", "before the")):
        known.add("life_before")
    if context:
        for field in (
            "life_before",
            "changes_after",
            "unseen_conditions",
            "present_influence",
            "meaning_of_unchosen_life",
            "later_branches",
            "current_life_context",
            "social_connection",
        ):
            if getattr(context, field, None):
                known.add(field)
    return known


def generate_editorial_clarification_questions(
    source_text: str,
    language: str,
    clarifications: ParallelLifeClarifications | None = None,
    answered_editorial_ids: list[str] | None = None,
    editorial_context: EditorialContext | None = None,
) -> list[ClarificationQuestion]:
    """Up to 5 optional Editorial preparation questions, skipping known answers."""
    ja = _is_ja(language, source_text)
    pool = _EDITORIAL_QUESTIONS_JA if ja else _EDITORIAL_QUESTIONS_EN
    known = _already_known_editorial_ids(
        source_text,
        clarifications or ParallelLifeClarifications(),
        editorial_context,
        answered_editorial_ids or [],
    )
    # Prefer questions that deepen editorial reading for fertility / family /
    # work / place signals present in the source.
    preferred: list[str] = []
    text = source_text
    if any(k in text for k in ("子ども", "子供", "息子", "娘", "不妊", "治療", "child", "fertility")):
        preferred.extend(
            [
                "later_branches",
                "current_life_context",
                "present_influence",
                "meaning_of_unchosen_life",
                "changes_after",
            ]
        )
    if any(k in text for k in ("仕事", "会社", "創作", "job", "work", "creative")):
        preferred.extend(["present_influence", "current_life_context", "changes_after"])
    if any(k in text for k in ("東京", "海外", "地元", "Tokyo", "abroad")):
        preferred.extend(["life_before", "changes_after", "present_influence"])
    preferred.extend([qid for qid, _ in pool])

    seen: set[str] = set()
    ordered: list[str] = []
    for qid in preferred:
        if qid in known or qid in seen:
            continue
        seen.add(qid)
        ordered.append(qid)

    table = dict(pool)
    questions: list[ClarificationQuestion] = []
    for qid in ordered:
        if qid not in table:
            continue
        questions.append(ClarificationQuestion(id=qid, question=table[qid]))
        if len(questions) >= 5:
            break
    return questions


# --- Multi-branch structure extraction ---------------------------------------

def extract_editorial_branch_structure(
    source_text: str,
    clar: ParallelLifeClarifications,
    context: EditorialContext,
    *,
    ja: bool,
) -> EditorialBranchStructure:
    """Build an internal multi-branch reading before editorial prose generation."""
    facts = extract_parallel_life_facts(source_text, clar, ja=ja)
    text = source_text
    explicit = list(facts.explicit_texts())

    primary = ""
    realized: str | None = None
    secondary: list[str] = []
    present = ""
    life_ctx: list[str] = []
    themes: list[str] = []

    # Fertility / family pattern
    fertility = any(k in text for k in ("不妊", "治療", "授かった", "fertility", "treatment"))
    child_born = any(k in text for k in ("授かった", "息子", "娘", "子どもを", "子供を", "born", "son", "daughter"))
    second_child = any(k in text for k in ("二人目", "2人目", "第二子", "second child", "another child"))

    if fertility or (child_born and any(k in text for k in ("諦", "続け", "stop", "continue"))):
        primary = (
            "不妊治療を続けるか、諦めるかという分岐"
            if ja
            else "whether to continue or stop fertility treatment"
        )
        themes.append("fertility" if not ja else "不妊治療")
    elif facts.education_polarity != "unknown":
        primary = (
            "進学をめぐる分岐"
            if ja
            else "a branch around education"
        )
        themes.append("education")
    elif facts.place_polarity != "unknown":
        primary = "場所をめぐる分岐" if ja else "a branch around place"
        themes.append("place")
    elif facts.work_polarity != "unknown":
        primary = "仕事をめぐる分岐" if ja else "a branch around work"
        themes.append("work")
    elif facts.marriage_polarity != "unknown":
        primary = "結婚をめぐる分岐" if ja else "a branch around marriage"
        themes.append("marriage")
    else:
        primary = (
            _clean(clar.chosen_path)
            or ("人生の大きな分岐" if ja else "a major life branch")
        )

    if clar.chosen_path:
        realized = _clean(clar.chosen_path)
    elif child_born:
        if "息子" in text or "son" in text.lower():
            realized = "息子が生まれ、家族として暮らすことになった" if ja else "a son was born and family life began"
        else:
            realized = "子どもを授かり、家族の生活が始まった" if ja else "a child was born and family life began"
    elif facts.education_polarity == "admitted" and facts.primary_institution():
        realized = (
            f"{facts.primary_institution()}へ進んだ"
            if ja
            else f"entered {facts.primary_institution()}"
        )
    elif facts.place_polarity == "stayed":
        loc = facts.locations[0].text if facts.locations else ("その場所" if ja else "that place")
        realized = f"{loc}に残った" if ja else f"stayed in {loc}"
    elif facts.place_polarity == "left":
        loc = facts.locations[0].text if facts.locations else ("その場所" if ja else "that place")
        realized = f"{loc}を離れた" if ja else f"left {loc}"

    if second_child or (child_born and any(k in text for k in ("今も", "考える", "wonder", "still"))):
        secondary.append(
            "二人目の子どもを持つかどうかという、その後に生まれた分岐"
            if ja
            else "a later branch around whether to have a second child"
        )
        themes.append("second_child" if not ja else "二人目")

    if context.later_branches:
        secondary.append(_clean(context.later_branches))

    if clar.what_remains:
        present = _clean(clar.what_remains)
    elif second_child or child_born:
        present = (
            "家族の記憶、支え、連続性を、いまの家族のなかでどう残していくかという問い"
            if ja
            else "how to preserve family memory, support, and continuity in the life being lived now"
        )
    elif clar.unchosen_path:
        present = (
            f"選ばなかった道（{_clean(clar.unchosen_path)}）が今も残している問い"
            if ja
            else f"the question the unchosen path ({_clean(clar.unchosen_path)}) still leaves"
        )
    else:
        present = (
            "その分岐が今の生活に残している問い"
            if ja
            else "the question this branch still leaves in the present life"
        )

    # Short labels only — never store full editorial answer paragraphs here
    # (raw answers are normalized separately before prose generation).
    for cue, label_ja, label_en in (
        ("家族", "家族", "family"),
        ("妻", "配偶者・家族", "spouse and family"),
        ("嫁", "配偶者・家族", "spouse and family"),
        ("夫", "配偶者・家族", "spouse and family"),
        ("息子", "息子との生活", "life with a son"),
        ("娘", "娘との生活", "life with a daughter"),
        ("仕事", "仕事", "work"),
        ("経営", "自社経営", "self-employment"),
        ("会社", "仕事・会社", "work"),
        ("アパート", "住まい", "housing"),
        ("友人", "子どもの友人との交流", "child's friendships"),
        ("友達", "子どもの友人との交流", "child's friendships"),
    ):
        blob = text + " " + (context.current_life_context or "")
        if cue in blob:
            label = label_ja if ja else label_en
            if label not in life_ctx:
                life_ctx.append(label)

    if context.life_before:
        themes.append("life_before")
    if context.unseen_conditions or clar.constraints:
        themes.append("constraints")

    if not primary:
        primary = "人生の大きな分岐" if ja else "a major life branch"

    return EditorialBranchStructure(
        primary_branch=primary,
        realized_outcome=realized,
        secondary_branches=secondary,
        present_question=present,
        current_life_context=life_ctx[:8],
        explicit_facts=explicit[:12],
        inferred_themes=themes[:8],
    )


# --- Editorial heuristic generation ------------------------------------------

def _editorial_title(
    structure: EditorialBranchStructure,
    ja: bool,
    grounded=None,
) -> tuple[str, str]:
    from app.parallel_life_domain import family_formation_title

    if grounded is not None and grounded.primary_domain == "family-formation":
        return family_formation_title(grounded, ja=ja, seed=1)
    if ja:
        if any("二人目" in s for s in structure.secondary_branches) or "二人目" in structure.inferred_themes:
            return (
                "授かったあとに残った問い",
                "叶った願いのそばに、まだ開いている分岐がある。",
            )
        if structure.realized_outcome:
            return (
                "選んだあとに開いた分岐",
                "実現した人生が、次の問いを静かに連れてきた。",
            )
        return (
            "いまも残っている分岐",
            "選んだ道と選ばなかった道が、同じ生活のなかで並んでいる。",
        )
    if any("second" in s.lower() for s in structure.secondary_branches):
        return (
            "The Question That Remained After Receiving",
            "Beside a wish that was fulfilled, another branch is still open.",
        )
    if structure.realized_outcome:
        return (
            "The Branch That Opened After Choosing",
            "The life that was realized quietly brought the next question with it.",
        )
    return (
        "A Branch That Still Remains",
        "The chosen and unchosen paths sit beside each other in the life being lived.",
    )


def _interpret_chosen_path(
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    clar: ParallelLifeClarifications,
    ctx: EditorialContext,
    *,
    ja: bool,
) -> str:
    """Interpret present-life facts into Chosen Path prose — never paste raw answers."""
    signals = set(normalized.signals)
    chosen_stated = _clean(clar.chosen_path) if clar.chosen_path else structure.realized_outcome
    if ja:
        chosen = (
            f"実際に選ばれたのは、{chosen_stated or 'そのとき引き受けた生活'}だった。"
            " それは結果の宣言というより、時間、仕事、住まい、身体、家族、ケア、注意の配分を"
            "組み直すことでもあった。"
        )
        if "family_of_three" in signals or "has_son" in signals:
            chosen += (
                " いまの暮らしでは、妻と息子との三人の関係が、日々の中心になっている。"
                " 家族は名簿上の人数ではなく、誰の時間を優先し、どこに立つかを決める条件になった。"
            )
        if "self_employed" in signals and "owned_housing" in signals:
            chosen += (
                " 自分の会社を運営し、家族が無理なく過ごせる住まいを維持している現在は、"
                "仕事と住居を別々の選択としてではなく、一つの生活設計として組み立ててきた結果でもある。"
            )
        elif "self_employed" in signals:
            chosen += (
                " 仕事の側では、自らの会社を運営する形が、家族の時間と両立しうるリズムを支えている。"
            )
        elif "owned_housing" in signals:
            chosen += (
                " 住まいの側では、家族が続けていける場所を自分たちで維持することが、"
                "選んだ生活の具体的な輪郭になっている。"
            )
        if "child_friends_visit" in signals or "warm_home_feeling" in signals:
            chosen += (
                " 息子の友人たちが家を訪れるようになり、住まいは三人家族の内側だけに閉じない場所になっている。"
                " 子どもの成長とともに人の出入りや声が増え、かつて夫婦だけで過ごしていた時間とは異なる、"
                "開かれた家庭の空気が育っている。"
            )
        if ctx.changes_after and len(_clean(ctx.changes_after)) < 40:
            # Only weave short clarifications; never dump long raw answers
            chosen += " 選択のあとに起きた変化は、生活の輪郭を少しずつ書き換えていった。"
        chosen += (
            " 新しい役割は、ときに新しい観察点をつくる。"
            "親として立つ位置が変わると、教育や社会の見え方も静かに変わる。"
            " 選んだ人生は正しさの証明ではなく、いまも更新され続けている生活の側にある。"
        )
        return chosen
    chosen = (
        f"What was chosen was {chosen_stated or 'the life taken on at the time'}. "
        "It reorganized time, work, place, body, family, care, and attention."
    )
    if "family_of_three" in signals:
        chosen += " The life now centers on a household of three — spouse and son — not as a headcount but as a daily allocation of care."
    if "self_employed" in signals and "owned_housing" in signals:
        chosen += (
            " Running a company and maintaining a home the family can live in are not separate choices; "
            "they form one design for continuity."
        )
    if "child_friends_visit" in signals:
        chosen += (
            " As the child's friends begin to visit, the home opens beyond the nuclear family — "
            "a warmer, more social household than the couple's earlier years."
        )
    chosen += " A new role can become a new point of observation. The chosen life is not proof of correctness; it is the side still being lived."
    return chosen


def _interpret_residue(
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    *,
    ja: bool,
) -> str:
    signals = set(normalized.signals)
    if ja:
        residue = (
            f"この分岐がいまも戻ってくるのは、{structure.present_question}が閉じきっていないからだ。"
            " それは単純な後悔でも、単純な感謝でもない。"
        )
        if "second_child_question" in signals:
            residue += (
                " 二人目という想像は、いまの三人家族を否定するためではなく、"
                "叶った願いのそばになお開いている可能性として残っている。"
            )
        if "child_friends_visit" in signals or "warm_home_feeling" in signals:
            residue += (
                " 同時に、息子の友人たちが行き来する家には、兄弟の有無だけでは測れない家族の厚みが育っている。"
                " 家庭らしいと感じる時間は、未決の問いと並んで、すでに始まっている。"
            )
        if "self_employed" in signals or "owned_housing" in signals:
            residue += (
                " 仕事と住まいを自分たちで組み立てている現在は、"
                "二人目を持たなかったことで守られた余白とも、父親になったあとに築いた生活基盤とも読める。"
            )
        residue += (
            " 分岐は過去の出来事であるだけでなく、いま何を残し、何を支え、何を記録しようとするかという、"
            "現在の姿勢そのものにもなっている。"
            " 未決の可能性は消えないが、すでに始まった関係を守る責任も、同じ場所にいる。"
        )
        return residue
    residue = (
        f"The branch still returns because {structure.present_question} has not fully closed. "
        "It is neither simple regret nor simple gratitude. "
    )
    if "second_child_question" in signals:
        residue += (
            "The imagined second child remains as an open possibility beside a wish already fulfilled — "
            "not as a verdict against the present family. "
        )
    if "child_friends_visit" in signals:
        residue += (
            "At the same time, a home visited by the child's friends has grown a thickness of family life "
            "that sibling count alone cannot measure. "
        )
    if "self_employed" in signals or "owned_housing" in signals:
        residue += (
            "Work and housing assembled by one's own hands can be read both as room protected by not "
            "pursuing another child, and as the foundation built after becoming a parent. "
        )
    residue += (
        "The branch is not only a past event; it has become part of how the present person "
        "protects, records, and continues."
    )
    return residue


def _interpret_closing(
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    *,
    ja: bool,
) -> str:
    signals = set(normalized.signals)
    if ja:
        closing = (
            f"いまここにあるのは、{structure.realized_outcome or '実際に選ばれた生活'}である。"
            " 選ばなかった可能性を消す必要はない。かといって、いまの関係や日々を、"
            "完成しなかった別人生の影で測る必要もない。"
        )
        closing += (
            f"\n\n{structure.present_question}は、感謝と未決の可能性を同時に抱えたまま、"
            "現在の家族、仕事、場所のなかで引き受けられていく。"
            " 想像上の別人生と、いま隣にいる人は、同じ秤に載せなくてよい。"
        )
        if "family_of_three" in signals or "has_son" in signals:
            closing += (
                "\n\n残るのは、妻と息子とともにある日々であり、"
                "そのなかで育っている家庭の時間である。"
            )
        else:
            closing += "\n\n残るのは、いま立っている生活の側である。"
        closing += (
            "\n\n閉じるべきなのは分岐そのものではなく、どちらか一方だけが正しかったという読み方のほうかもしれない。"
        )
        return closing
    closing = (
        f"What is here now is {structure.realized_outcome or 'the life that was actually chosen'}. "
        "There is no need to erase the unchosen possibility, and no need to measure present relationships "
        "only against an unfinished alternative."
    )
    closing += (
        f"\n\n{structure.present_question} can be held with gratitude and unresolved possibility together. "
        "An imagined alternative and the people beside you now need not share one scale."
    )
    if "family_of_three" in signals:
        closing += "\n\nWhat remains is the life shared with spouse and son, and the household time growing there."
    closing += (
        "\n\nWhat may need closing is not the branch itself, "
        "but the habit of deciding which life alone was correct."
    )
    return closing


def _heuristic_editorial_result(
    request: ParallelLifeEditorialRequest,
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    grounded,
    *,
    ja: bool,
) -> ParallelLifeResult:
    from app.parallel_life_domain import validate_domain_consistency

    clar = request.clarifications
    ctx = request.editorial_context
    facts = extract_parallel_life_facts(request.source_text, clar, ja=ja)
    title, subtitle = _editorial_title(structure, ja, grounded=grounded)

    # Hard lock: never allow creativity takeover of family-formation titles
    if grounded.primary_domain == "family-formation" and any(
        k in title for k in ("創作", "執筆", "小説", "Creative", "Writing")
    ):
        title, subtitle = _editorial_title(structure, ja, grounded=grounded)
    # Theme text for lens selection: signals + short facts only (no raw paragraphs)
    context_blob = " ".join(
        normalized.present_life_facts
        + normalized.current_roles
        + normalized.current_conditions
        + normalized.signals
    )

    # Branch Point
    if ja:
        branch = (
            f"この読みの中心にあるのは、{structure.primary_branch}である。"
            " それは一瞬の決断というより、前後の生活が押し出し、また引き受け直してきた分岐だった。"
        )
        if ctx.life_before:
            branch += (
                " 分岐の前には、のちに選ばれる条件をすでに準備していた生活があった。"
                " 望んでいたことと、すでに始まっていた制約が、同じ場所に置かれていた。"
            )
        else:
            branch += (
                " 分岐の前の生活は、いま振り返ると、のちに選ばれる条件を静かに準備していたように見える。"
                " 何を守り、何を先送りし、何をまだ言葉にしていなかったのかが、その手前にあった。"
            )
        if structure.realized_outcome:
            branch += (
                f" 実際に起こったのは、{structure.realized_outcome}という結果だった。"
                " 実現した願いは、しばしば終点ではなく、生活の配分を組み替える始まりになる。"
            )
        if structure.secondary_branches:
            branch += (
                " しかしその結果は閉じた結論ではなく、"
                f"{structure.secondary_branches[0]}が、あとから見えてきた。"
                " 一次の分岐が終わったあとにしか現れない問いもある。"
            )
            if len(structure.secondary_branches) > 1:
                branch += f" さらに、{structure.secondary_branches[1]}も、同じ時間のなかで重なっていた。"
        branch += (
            f" いま残っているのは、{structure.present_question}である。"
            " 分岐は過去の一点に固定されず、現在の生活のなかで、別の形を取り直して戻ってくる。"
        )
        if ctx.unseen_conditions or clar.constraints:
            branch += " 当時は十分に見えていなかった条件も、選択の手前で生活の幅を決めていた。"
        if ctx.social_connection:
            branch += " 社会の変化と重ねると、この分岐は私的な決断だけには見えなくなる。"
    else:
        branch = (
            f"At the center of this reading is {structure.primary_branch}. "
            "It was less a single instant than a branch pressed forward by the life before it, "
            "and taken up again afterward."
        )
        if ctx.life_before:
            branch += (
                " Before the branch, desire and constraint were already sitting in the same room."
            )
        else:
            branch += (
                " Looking back, the life before the branch seems to have prepared the conditions "
                "that would later be chosen — what was already protected, deferred, or still unnamed."
            )
        if structure.realized_outcome:
            branch += (
                f" What actually followed was {structure.realized_outcome}. "
                "A fulfilled wish is often not an ending but a reorganization of daily life."
            )
        if structure.secondary_branches:
            branch += (
                f" That outcome was not a closed conclusion; {structure.secondary_branches[0]} "
                "became visible later. Some questions appear only after the first branch has been lived."
            )
        branch += (
            f" What remains now is {structure.present_question}. "
            "The branch is not fixed to a past date; it returns inside the present life in another form."
        )
        if ctx.social_connection:
            branch += " Placed against social change, this branch no longer looks purely private."

    chosen = _interpret_chosen_path(structure, normalized, clar, ctx, ja=ja)

    # Unchosen Life — may include more than one (interpreted, not inventory)
    unchosen_parts: list[str] = []
    if clar.unchosen_path:
        unchosen_parts.append(_clean(clar.unchosen_path))
    for sec in structure.secondary_branches:
        unchosen_parts.append(sec)
    seen_u: set[str] = set()
    uniq_u: list[str] = []
    for u in unchosen_parts:
        if u and u not in seen_u:
            seen_u.add(u)
            uniq_u.append(u)
    if not uniq_u:
        uniq_u = ["進まなかった側の道" if ja else "the path not taken"]

    if ja:
        unchosen = (
            "選ばなかった人生は、一つのぼんやりした「もしも」にまとめてはいけない。"
            " 分岐が複数あるとき、それぞれが別の得と負担を抱えている。"
        )
        for i, u in enumerate(uniq_u[:2]):
            if i == 0:
                unchosen += f" まずそこにあるのは、{u}である。"
            else:
                unchosen += f" それとは別に、{u}も、同じ生活のなかで開いている。"
            unchosen += (
                " そこには得られていたかもしれない自由や余白もあるが、"
                "別の種類の負担や不確かさもあったはずで、完成した幸福な別人生として扱うことはできない。"
            )
        if "second_child_question" in normalized.signals:
            unchosen += (
                " 二人目をめぐる想像は、諦めた治療の延長でも、いまの息子の否定でもなく、"
                "叶った願いの外に残ったもう一つの家族の形として残っている。"
            )
        elif ctx.meaning_of_unchosen_life:
            unchosen += (
                " いまその道に託しているものがあるとすれば、実現しなかった速度や形へのまなざしに近い。"
                " 託しているものと、実際に起きていたであろう生活とは、必ずしも同じではない。"
            )
        else:
            unchosen += (
                " いまその道が象徴しているのは、実現しなかった可能性そのものだけでなく、"
                "現在の生活が引き受けなかった速度や形へのまなざしでもある。"
            )
    else:
        unchosen = (
            "The unchosen life should not be collapsed into one vague 'what if'. "
            "When more than one branch is present, each carries its own gains and burdens."
        )
        for i, u in enumerate(uniq_u[:2]):
            if i == 0:
                unchosen += f" First there is {u}."
            else:
                unchosen += f" Separately, {u} also remains open inside the same life."
            unchosen += (
                " There may have been gains, but also other burdens and uncertainties — "
                "it cannot be treated as a finished happier life."
            )
        if "second_child_question" in normalized.signals:
            unchosen += (
                " The imagined second child is neither a continuation of abandoned treatment "
                "nor a rejection of the son who is here; it remains another possible family form."
            )

    # Lost / Protected — distinct logics, editorial item counts 4–5
    if ja:
        lost = [
            "その選択の前に持っていた時間の使い方",
            "別の家族の形として想像されていた可能性",
            "身軽に動けていたころの生活のリズム",
            "実現しなかった側に残る、まだ名づけにくい余白",
        ]
        if any("二人目" in s for s in structure.secondary_branches) or "second_child_question" in normalized.signals:
            lost[1] = "二人目の子どもを持つという、まだ確定していない可能性"
        protected = [
            "いま一緒に暮らしている人との連続性",
            "身体や心への過度な負担を増やし続けない余地",
            "生活を支える時間とお金の配分",
            "すでに始まった家族の日々を大切にできること",
        ]
        if "owned_housing" in normalized.signals or "self_employed" in normalized.signals:
            protected.append("家族の生活を支える仕事と住まいの余白")
        if ctx.unseen_conditions:
            protected.append("当時は意識していなかったが、あとから守られていた条件")
    else:
        lost = [
            "a way of using time that belonged to the life before the choice",
            "a family form that remained only as a possibility",
            "the lighter rhythm of days that could still move freely",
            "an unnamed margin left on the side that was not realized",
        ]
        protected = [
            "continuity with the people lived with now",
            "room not to keep increasing bodily or psychological burden",
            "a workable distribution of time and money",
            "the ability to care for the family days already begun",
        ]
        if "owned_housing" in normalized.signals or "self_employed" in normalized.signals:
            protected.append("room in work and housing that sustains family life")

    lost = lost[:5]
    protected = protected[:5]

    residue = _interpret_residue(structure, normalized, ja=ja)

    theme_text = " ".join(
        [
            structure.primary_branch,
            structure.present_question,
            " ".join(structure.secondary_branches),
            " ".join(structure.inferred_themes),
            context_blob,
            "family intimacy body work education book protocol",
        ]
    )
    lens_ids = select_observatory_lenses(theme_text, context_blob, "editorial")
    if any(
        t in structure.inferred_themes or t in normalized.signals
        for t in ("fertility", "不妊治療", "二人目", "second_child", "fertility_path", "second_child_question")
    ):
        preferred = ["intimacy", "body", "book", "protocol-publishing", "education-employment"]
        merged: list[str] = []
        for lid in preferred + lens_ids:
            if lid in OBSERVATORY_LENSES and lid not in merged:
                merged.append(lid)
            if len(merged) >= 4:
                break
        lens_ids = merged

    layers = [_editorial_lens_body(lid, structure, normalized, ja) for lid in lens_ids]

    if ja:
        synthesis = (
            "個人の分岐として見えるものは、親密さ、身体、物語、そして同じ条件のもとで問いを共有できる記録の形が重なる場所でも起きていた。"
            f" {structure.primary_branch}は私的な決断であると同時に、"
            "医療、家族、労働、時間の配分といった条件のなかで形づくられていた。"
            f" いま問われているのは、{structure.present_question}であり、"
            "それは過去の正誤よりも、現在の生活をどう続け、何を残すかに関わっている。"
        )
        if "child_friends_visit" in normalized.signals:
            synthesis += (
                " 子どもの友人が行き来する家は、親密さの私的な核が、社会的な関係の入口にもなっていることを示している。"
            )
    else:
        synthesis = (
            "What looks like a private branch also formed where intimacy, the body, narrative form, "
            "and the possibility of shared records overlapped. "
            f"{structure.primary_branch} was a personal decision and also a decision shaped by "
            "medicine, family, work, and the distribution of time. "
            f"What is asked now is {structure.present_question}."
        )

    rebranch = _editorial_rebranch(structure, normalized, ja=ja)
    closing = _interpret_closing(structure, normalized, ja=ja)

    result = ParallelLifeResult(
        title=title,
        subtitle=subtitle,
        branch_point=branch,
        chosen_path=chosen,
        unchosen_life=unchosen,
        lost=lost,
        protected=protected,
        residue=residue,
        observatory_layers=layers,
        cross_lens_synthesis=synthesis,
        rebranch=rebranch,
        closing=closing,
        generation_mode="heuristic",
        language="ja" if ja else "en",
        depth="editorial",
    )
    validate_factual_consistency(request.source_text, result, facts, ja=ja)
    result = postprocess_editorial_result(result, normalized, ja=ja)
    validate_domain_consistency(result, grounded, ja=ja)
    return result


def _editorial_lens_body(
    lens_id: str,
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    ja: bool,
) -> ObservatoryLayer:
    lens = OBSERVATORY_LENSES[lens_id]
    detail = structure.realized_outcome or structure.primary_branch
    present = structure.present_question
    signals = set(normalized.signals)
    if ja:
        intimacy_extra = (
            " 子どもの友人が家を訪れるようになると、親密さは夫婦と親子の内側だけに閉じず、"
            "家が社会的な関係の入口にもなる。"
            if "child_friends_visit" in signals
            else ""
        )
        bodies = {
            "intimacy": (
                f"{detail}という具体的な経験は、親密さの形を組み替えた。"
                f" 二人の関係、親子の関係、支え合う人数の変化は、{present}と結びついている。"
                " 親密さは感情だけでなく、誰と日々を分担するか、誰のケアを引き受けるかという制度的な条件でもある。"
                f"{intimacy_extra}"
                " この分岐が残したのは、愛の有無ではなく、親密さの配置そのものだった。"
            ),
            "body": (
                f"身体は、この分岐の条件そのものだった。"
                f" 治療、回復、疲労、年齢の感覚は、{detail}の背後で生活を形づくっていた。"
                " 守られたもののなかには、身体への負担を無限に増やさない判断も含まれている。"
                " 身体の限界は、しばしば選択の正しさとは別の層で、生活の輪郭を決めていた。"
            ),
            "book": (
                f"この分岐の文学的な中心は、叶った願いのそばに、まだ開いている問いがあることだ。"
                f" {detail}が実現したあとも、{present}は消えず、物語の緊張として残る。"
                " 視点は、選んだ側の生活に立ちつつ、実現しなかった側を完全には閉じない位置にある。"
                " 繰り返される像があるとすれば、完成した家族の輪郭と、そのすぐ外に残る空白である。"
                " 形としては、断定しない長めの私的記録、あるいは閉じない章がふさわしい。"
            ),
            "protocol-publishing": (
                f"個人の経験を、同じ問いに立つ人の記録へ開くなら、"
                f"比較の軸は「何を選んだか」よりも「その後にどんな分岐が生まれたか」「いま何が残っているか」になる。"
                " 他人に聞ける問いは、たとえば分岐の前の生活、実現したあとで見えた次の分岐、現在の責任の形である。"
                " 固有名や他人を特定する情報は私的なまま残し、構造だけを共有可能なプロトコルにできる。"
                " 複数の匿名記録が並ぶとき、個人の後悔ではなく、社会的なパターンが浮かび上がることがある。"
            ),
            "education-employment": (
                f"家族やケアの形が変わると、教育と就労の条件も見え方が変わる。"
                f" {present}は、個人の迷いに見えるが、制度が家族に割り当てる時間と責任の問題でもある。"
                " 子どもや家族の将来を考えるとき、教育と雇用は遠い制度ではなく、日常の観察点になる。"
            ),
            "work": (
                f"仕事の継続や中断は、{detail}と無関係ではなかった。"
                " 収入、時間、役割の安定は、選んだ生活を支える条件であると同時に、別の道を遠ざける条件でもあった。"
                f" {present}は、仕事のペースと家族の時間のあいだで、いまも形を変えて残っている。"
            ),
            "city": (
                f"住む場所は、{detail}の背景で、誰とどれだけ近く暮らせるかを決めていた。"
                f" {present}は、場所の選択と家族の連続性が重なる地点でもある。"
                " 住まなかった街は、未完の可能性としてではなく、いまの場所をどう生きるかの対照として残ることがある。"
            ),
            "market-signals": (
                f"生活を成り立たせる費用、医療、時間の価格は、{structure.primary_branch}を私的な決断だけに見えなくする。"
                " 市場の条件は、しばしば選択の手前で選択肢の幅を決めていた。"
                " いま残る問いは、価格表の問題というより、何に費用と時間を割り当ててきたかの履歴でもある。"
            ),
        }
        body = bodies.get(
            lens_id,
            f"{detail}をめぐる経験は、{lens.name_en}の条件と無関係ではなかった。"
            f" {present}は、その接点に残っている。"
            " 個人の物語は、ここで社会的な条件の読みへと開かれるが、物語そのものを飲み込みはしない。",
        )
        descriptor = lens.descriptor_ja
    else:
        bodies = {
            "intimacy": (
                f"The concrete experience of {detail} reorganized the form of intimacy. "
                f"Changes in partnership, parenthood, and who shares the days connect to {present}. "
                "Intimacy is not only feeling; it is also the institutional condition of who carries daily life. "
                "What the branch left was less the presence or absence of love than a rearrangement of intimacy itself."
            ),
            "body": (
                f"The body was itself a condition of this branch. "
                f"Treatment, recovery, fatigue, and the sense of age shaped life behind {detail}. "
                "Among what was protected may be the refusal to keep increasing bodily burden without end. "
                "Bodily limits often drew the outline of a life on a layer separate from verdicts of correctness."
            ),
            "book": (
                f"The literary center is a fulfilled wish beside a question that remains open. "
                f"After {detail}, {present} did not disappear; it remains as narrative tension. "
                "The point of view stands inside the chosen life without fully closing the unrealized side. "
                "If there is a recurring image, it is the outline of a realized family beside a blank that stays near it. "
                "A fitting form may be a long private record that refuses a final verdict, or a chapter that does not close."
            ),
            "protocol-publishing": (
                "If this experience is opened as a reusable protocol for others with similar questions, "
                "the comparison axes matter more than the private plot: what was chosen, what branch "
                "appeared afterward, and what remains now. "
                "Questions that can be asked of others include life before the branch, later branches "
                "visible only after the outcome, and the shape of present responsibility. "
                "Identifying details stay private; structure can be shared. "
                "When anonymous records sit side by side, a social pattern may appear where private regret once stood alone."
            ),
            "education-employment": (
                f"When the form of family and care changes, education and employment conditions change their appearance too. "
                f"{present} looks personal, but it is also about the time and responsibility institutions assign to families."
            ),
            "work": (
                f"Continuing or interrupting work was not unrelated to {detail}. "
                "Income, time, and role stability supported the chosen life and also moved other paths farther away."
            ),
            "city": (
                f"Place decided, behind {detail}, how near one could live to whom. "
                f"{present} sits where place and family continuity overlap."
            ),
            "market-signals": (
                f"The price of living, medicine, and time keeps {structure.primary_branch} from looking purely private. "
                "Market conditions often set the width of the options before the choice was named."
            ),
        }
        body = bodies.get(
            lens_id,
            f"The experience around {detail} was not separate from the conditions named by {lens.name_en}. "
            f"{present} remains at that intersection. "
            "The personal narrative opens into social reading here without being swallowed by it.",
        )
        descriptor = lens.descriptor_en

    return ObservatoryLayer(
        id=lens_id,
        title=lens.name_en,
        descriptor=descriptor,
        body=body,
    )


def _editorial_rebranch(
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    *,
    ja: bool,
) -> list[str]:
    items: list[str] = []
    signals = set(normalized.signals)
    family = bool(
        signals & {"family_of_three", "has_son", "warm_home_feeling", "child_friends_visit"}
    ) or any(k in " ".join(structure.current_life_context) for k in ("家族", "息子", "family"))
    work = "self_employed" in signals or any(
        k in " ".join(structure.current_life_context) for k in ("仕事", "会社", "work")
    )

    if ja:
        if family:
            items.append(
                "いまの家族のなかで残したい記憶を、短い記録や写真、言葉として一つ残す。"
                f"（{structure.present_question}に応える小さな実践として）"
            )
            if "child_friends_visit" in signals:
                items.append(
                    "息子の友人が行き来する関係を、兄弟の代わりではなく、いまの家が開いている支えの輪として大切にする。"
                )
            else:
                items.append(
                    "子どもや家族の支えを、自分一人に閉じず、信頼できる人の輪を一つ広げる。"
                )
        if "second_child_question" in signals or any("二人目" in s for s in structure.secondary_branches):
            items.append(
                "二人目をめぐる問いを、正解探しではなく、いまの家族で守っているものを確認する時間として、一度書き分ける。"
            )
        if work:
            items.append(
                "自社の運営や住まいの維持を、個人の成功譚ではなく、家族の連続性を支える条件として短いメモに残す。"
            )
        items.append(
            "選ばなかった道に託しているものを一語で書き、それをいまの三人の暮らしや仕事のなかへ、小さく持ち込む形を一つ決める。"
            if family
            else "選ばなかった道に託しているものを一語で書き、いまの生活へ小さく持ち込む形を一つ決める。"
        )
        items.append(
            "この分岐を、匿名の構造だけ残す生きた記録として一文で残し、固有の事情は私的なままにしておく。"
        )
    else:
        if family:
            items.append(
                "Preserve one piece of family memory — a short note, photograph, or sentence — "
                f"as a small practice that answers {structure.present_question}."
            )
            if "child_friends_visit" in signals:
                items.append(
                    "Treat the child's visiting friends as a support network the home already opens — "
                    "not as a substitute for a sibling, but as a present form of continuity."
                )
            else:
                items.append(
                    "Widen the child's or family's support by one trusted relationship, rather than holding everything alone."
                )
        if "second_child_question" in signals:
            items.append(
                "Write the question of a second child as two columns: what is being protected in the present family, "
                "and what remains only as possibility — without forcing a verdict."
            )
        if work:
            items.append(
                "Record, briefly, how running work and housing now sustains family continuity — as observation, not self-blame."
            )
        items.append(
            "Name in one word what the unchosen path still holds, and choose one small way to carry that quality into present life."
        )
        items.append(
            "Leave one anonymous structural note of this branch as a living record, keeping identifying details private."
        )

    # Dedupe and keep 3–5
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
        if len(out) >= 5:
            break
    while len(out) < 3:
        out.append(
            "この分岐について、いま残っている問いを一段落で書く。"
            if ja
            else "Write one paragraph naming the question this branch still leaves."
        )
    return out[:5]


async def generate_editorial_parallel_life(
    request: ParallelLifeEditorialRequest,
) -> ParallelLifeEditorialResponse:
    """Editorial Edition: book-style single essay (LLM required, no heuristic fallback).

    Pipeline: lock facts → generate one full draft → fact-validate → optional
    model revision. Destructive string post-processing is not used.

    ``_heuristic_editorial_result`` / ``_llm_editorial`` remain as legacy helpers
    for inspection only — they are not called from this entrypoint.
    """
    from app.parallel_life_editorial_essay import generate_editorial_essay

    return await generate_editorial_essay(request)


async def _llm_editorial(
    request: ParallelLifeEditorialRequest,
    structure: EditorialBranchStructure,
    normalized: NormalizedEditorialContext,
    grounded,
    api_key: str,
    *,
    ja: bool,
) -> ParallelLifeResult:
    from openai import OpenAI

    from app.parallel_life_facts import facts_prompt_block, extract_parallel_life_facts
    from app.parallel_life_engine import (
        _clean_line,
        _dedupe_semantically,
        _is_valid_english_title,
        _is_valid_japanese_title,
        _validate_cross_lens_synthesis_quality,
        _validate_no_leakage_or_truncation,
        _validate_rebranch_items,
    )
    from app.observatory_lenses import validate_lens_ids
    from app.parallel_life_editorial_normalize import assert_no_long_raw_reuse
    from app.parallel_life_domain import validate_domain_consistency

    facts = extract_parallel_life_facts(request.source_text, request.clarifications, ja=ja)
    facts_block = facts_prompt_block(facts, ja=ja)
    grounded_block = grounded.model_dump()
    structure_block = {
        "primary_branch": structure.primary_branch,
        "realized_outcome": structure.realized_outcome,
        "secondary_branches": structure.secondary_branches,
        "present_question": structure.present_question,
    }
    normalized_block = {
        "present_life_facts": normalized.present_life_facts,
        "emotional_observations": normalized.emotional_observations,
        "current_roles": normalized.current_roles,
        "current_conditions": normalized.current_conditions,
        "secondary_branches": normalized.secondary_branches,
        "unresolved_questions": normalized.unresolved_questions,
        "signals": normalized.signals,
    }
    prior = standard_interpretation_summary(request.standard_result, ja=ja)
    valid_ids = ", ".join(OBSERVATORY_LENSES.keys())
    domain_lock = (
        f"primary_domain={grounded.primary_domain}; primary_event={grounded.primary_event}. "
        "この主題を創作・執筆・作品制作へ置き換えてはならない。"
        if ja
        else f"primary_domain={grounded.primary_domain}; primary_event={grounded.primary_event}. "
        "Do not replace this subject with creativity or writing."
    )

    if ja:
        system = f"""あなたは Parallel Life の編集版（Editorial Edition）を書く編集者です。
標準版の延長ではなく、委嘱された私的エッセイとして書いてください。
{facts_block}
【主題ロック・最重要】{domain_lock}
固定された一次分岐: {json.dumps(grounded_block, ensure_ascii=False)}
分岐構造: {json.dumps(structure_block, ensure_ascii=False)}
正規化済み事実（素材のみ。原文コピー禁止）: {json.dumps(normalized_block, ensure_ascii=False)}
標準版の要約（事実ではない）: {json.dumps(prior, ensure_ascii=False)}
注意: 以下の例は文体の参考のみ。例の主題・人物・場所・行為を事実として使ってはならない。
絶対規則:
- 明示された primary_event を別テーマ（特に創作）へ置き換えない
- タイトルに「創作」「執筆」「小説」を使わない（主題が創作のときを除く）
- ユーザー原文のコピー禁止。事実を意味へ変換する
- Lost/Protected は異なる論理。Lens は 3〜4（ID: {valid_ids}）
- すべて日本語。予言・正誤判定・診断をしない
JSONのみ:
{{"title":str,"subtitle":str,"branch_point":str,"chosen_path":str,"unchosen_life":str,
"lost":[str,...],"protected":[str,...],"residue":str,
"observatory_layers":[{{"id":str,"title":str,"body":str}},...],
"cross_lens_synthesis":str,"rebranch":[str,...],"closing":str}}"""
        user = (
            "書かれた分岐（事実の出所。文章としてコピーしない）:\n"
            f"{request.source_text}\n\n"
            f"主題は「{grounded.primary_event}」（domain={grounded.primary_domain}）です。"
            "この主題を守り、編集原稿を書いてください。"
        )
    else:
        system = f"""You write the Parallel Life Editorial Edition as a commissioned personal essay.
{facts_block}
DOMAIN LOCK: {domain_lock}
Grounded branch: {json.dumps(grounded_block)}
Structure: {json.dumps(structure_block)}
Normalized facts: {json.dumps(normalized_block)}
Standard draft summary (not facts): {json.dumps(prior)}
Examples below (if any) illustrate style only — do not copy their subjects, facts, domains, people, places, or actions.
Rules:
- Never replace primary_event with creativity/writing unless domain is creativity
- Do not copy user sentences; convert facts into meaning
- Choose 3–4 Observatory Lenses (IDs: {valid_ids})
- English only
JSON only with the same schema."""
        user = (
            "Written branch (source of facts — do not copy as prose):\n"
            f"{request.source_text}\n\n"
            f"Keep the subject as «{grounded.primary_event}» (domain={grounded.primary_domain})."
        )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=4000,
    )
    content = (response.choices[0].message.content or "").strip().strip("`")
    if content.lower().startswith("json"):
        content = content[4:].strip()
    data: dict[str, Any] = json.loads(content)

    lost = [_clean_line(x) for x in data.get("lost", []) if str(x).strip()]
    protected = [_clean_line(x) for x in data.get("protected", []) if str(x).strip()]
    rebranch = [_clean_line(x) for x in data.get("rebranch", []) if str(x).strip()]
    lost = _dedupe_semantically(lost, ja)
    protected = _dedupe_semantically(protected, ja)
    if not (3 <= len(lost) <= 6) or not (3 <= len(protected) <= 6) or not (3 <= len(rebranch) <= 6):
        raise ValueError("editorial list lengths invalid")
    _validate_rebranch_items(rebranch, ja)

    raw_layers = data.get("observatory_layers") or []
    layer_ids = validate_lens_ids([str(item.get("id", "")) for item in raw_layers])
    if not (3 <= len(layer_ids) <= 4):
        # Allow 2–4 for resilience; prefer 3–4
        if not (2 <= len(layer_ids) <= 4):
            raise ValueError("editorial observatory_layers count invalid")
    layers: list[ObservatoryLayer] = []
    for item in raw_layers:
        lid = str(item.get("id", ""))
        if lid not in layer_ids:
            continue
        lens_def = OBSERVATORY_LENSES[lid]
        body = _clean_line(str(item.get("body", "")))
        if not body:
            raise ValueError("empty layer body")
        layers.append(
            ObservatoryLayer(
                id=lid,
                title=lens_def.name_en,
                descriptor=lens_def.descriptor_ja if ja else lens_def.descriptor_en,
                body=body,
            )
        )

    title = _clean_line(data["title"])
    if not (_is_valid_japanese_title(title) if ja else _is_valid_english_title(title)):
        raise ValueError("editorial title invalid")

    result = ParallelLifeResult(
        title=title,
        subtitle=_clean_line(data["subtitle"]),
        branch_point=_clean_line(data["branch_point"]),
        chosen_path=_clean_line(data["chosen_path"]),
        unchosen_life=_clean_line(data["unchosen_life"]),
        lost=lost[:6],
        protected=protected[:6],
        residue=_clean_line(data["residue"]),
        observatory_layers=layers,
        cross_lens_synthesis=_clean_line(data["cross_lens_synthesis"]),
        rebranch=rebranch[:6],
        closing=_clean_line(data["closing"]),
        generation_mode="llm",
        language="ja" if ja else "en",
        depth="editorial",
    )
    _validate_cross_lens_synthesis_quality(
        result.cross_lens_synthesis, [layer.title for layer in layers], ja
    )
    _validate_no_leakage_or_truncation(
        [
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
        ],
        ja,
    )
    validate_factual_consistency(request.source_text, result, facts, ja=ja)
    result = postprocess_editorial_result(result, normalized, ja=ja)
    leaks = assert_no_long_raw_reuse(result, normalized, ja=ja)
    if leaks:
        raise ValueError(f"raw input reuse detected: {leaks[0][:40]}")
    validate_domain_consistency(result, grounded, ja=ja)
    return result
