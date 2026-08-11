"""Observatory Lens configuration and selection logic for Parallel Life.

The Observatory Layer is a defining feature of SHIRO & Co. / Kosuke Protocol:
it reads a single private life branch through several distinct observatory
lenses, so that a personal choice becomes visible as something also shaped by
systems, markets, institutions, places, media, and historical timing.

This module owns:

- the enumerated set of supported ``ObservatoryLensId`` values,
- bilingual metadata for each lens,
- keyword-driven, deterministic lens *selection* (never trust an LLM to invent
  arbitrary lens IDs; all returned IDs are validated against this enum),
- concise, native heuristic body text per lens (used by the heuristic fallback).

Nothing here imports the vector store, so it stays fast and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --- Enumerated lens IDs (the single source of truth) ---
OBSERVATORY_LENS_IDS: tuple[str, ...] = (
    "education-employment",
    "market-signals",
    "book",
    "protocol-publishing",
    "work",
    "city",
    "intimacy",
    "body",
    "clean-society",
    "after-success",
    "old-web",
    "contact-data",
    "meaning-layer",
    "sound",
    "image",
    "style",
)

# The four "core preferred" lenses that define the Parallel Life reading. They
# are preferred where relevant but are never all forced into a single result.
CORE_PREFERRED_LENSES: tuple[str, ...] = (
    "education-employment",
    "market-signals",
    "book",
    "protocol-publishing",
)


@dataclass(frozen=True)
class ObservatoryLensDef:
    """Definition of a single observatory lens.

    The official lens name (``name_en``) is kept in English in both languages
    (product spec §27, and the editorial-quality pass that followed it) — it
    is never translated or transliterated inconsistently (e.g. "市場のシグナ
    ル", "プロトコル・パブリッシング"). ``descriptor_en`` / ``descriptor_ja``
    are a short, concrete phrase (not a full sentence) shown directly under
    the official name in the result document, archive, and Markdown export.
    ``description_en`` / ``description_ja`` remain full sentences used only
    for the longer lens-configuration text (e.g. an About page).
    """

    id: str
    name_en: str
    name_ja: str
    description_en: str
    description_ja: str
    descriptor_en: str
    descriptor_ja: str
    # Trigger keywords (bilingual, lowercased) used for deterministic selection.
    keywords: list[str] = field(default_factory=list)


# Official lens names are kept in English in both languages (per product
# spec); Japanese explanatory text is always provided alongside, never as a
# translated or transliterated version of the name itself.
OBSERVATORY_LENSES: dict[str, ObservatoryLensDef] = {
    "education-employment": ObservatoryLensDef(
        id="education-employment",
        name_en="Education–Employment",
        name_ja="Education–Employment",
        description_en="How education and employment systems structured the choices that were available.",
        description_ja="教育と就労の制度が、選べる選択肢そのものをどう形づくっていたか。",
        descriptor_en="How schooling and work set the terms of a life",
        descriptor_ja="進路と就労が生活の条件を決めていく",
        keywords=[
            "school", "university", "college", "graduate", "graduation", "degree",
            "employment", "job", "career", "hire", "hired", "company", "work",
            "training", "credential", "internship", "relocat", "transfer",
            "大学", "学校", "卒業", "就職", "入社", "内定", "進学", "受験", "資格",
            "研修", "配属", "転勤", "勤務", "新卒", "第一志望", "会社",
        ],
    ),
    "market-signals": ObservatoryLensDef(
        id="market-signals",
        name_en="Market Signals",
        name_ja="Market Signals",
        description_en="The economic conditions — housing, income, work, region — that made a life possible or not.",
        description_ja="住まい・収入・仕事・地域といった、その生活を可能にした（しなかった）経済的条件。",
        descriptor_en="The market conditions behind a livable life",
        descriptor_ja="生活を成立させる市場条件",
        keywords=[
            "housing", "rent", "income", "salary", "wage", "money", "cost",
            "afford", "economy", "market", "marriage", "married", "wedding",
            "child", "children", "childcare", "family", "commute", "transport",
            "migration", "urban", "rural", "region", "support",
            "家賃", "住まい", "住居", "収入", "給料", "お金", "生活費", "経済",
            "結婚", "出産", "子ども", "子供", "育児", "介護", "家族", "地方",
            "都市", "上京", "移住", "通勤", "仕送り",
        ],
    ),
    "book": ObservatoryLensDef(
        id="book",
        name_en="Book",
        name_ja="Book",
        description_en="The literary form hidden inside the branch — what story it could become, and how.",
        description_ja="分岐のなかに隠れている文学の形。それがどんな物語になり得るのか。",
        descriptor_en="The literary form hidden inside a branch",
        descriptor_ja="分岐に潜んでいる物語のかたち",
        keywords=[
            "write", "writing", "wrote", "story", "novel", "essay", "creative",
            "art", "music", "paint", "film", "poem", "diary", "letter",
            "書く", "書か", "小説", "物語", "創作", "作品", "詩", "日記", "手紙",
            "絵", "音楽", "映画", "表現",
        ],
    ),
    "protocol-publishing": ObservatoryLensDef(
        id="protocol-publishing",
        name_en="Protocol Publishing",
        name_ja="Protocol Publishing",
        description_en="How this one branch, placed beside other anonymous records, could reveal a social pattern.",
        description_ja="この分岐が、匿名の他の記録と並べられたとき、社会的なパターンとして見えてくること。",
        descriptor_en="Turning one life into anonymous social record",
        descriptor_ja="個人史を匿名の社会記録へ変える",
        keywords=[
            "generation", "society", "everyone", "common", "many people",
            "world", "era", "times", "その頃", "当時", "時代", "世代", "みんな",
            "社会", "普通", "多くの人",
        ],
    ),
    "work": ObservatoryLensDef(
        id="work",
        name_en="Work",
        name_ja="Work",
        description_en="Organizational life, labor conditions, and identity built around staying, leaving, or changing roles.",
        description_ja="組織での生活、労働の条件、そして留まる・辞める・役割を変えることに結びついた自己。",
        descriptor_en="Staying, leaving, and the self built at work",
        descriptor_ja="留まる・辞めると結びついた自己像",
        keywords=[
            "quit", "resign", "leave the company", "promotion", "boss", "colleague",
            "overwork", "labor", "role", "position",
            "辞め", "退職", "昇進", "上司", "同僚", "残業", "労働", "役職", "部署",
        ],
    ),
    "city": ObservatoryLensDef(
        id="city",
        name_en="City",
        name_ja="City",
        description_en="Place, migration, and belonging — the memory of where a life was or was not lived.",
        description_ja="場所・移動・帰属。どこで生きた（生きなかった）かをめぐる記憶。",
        descriptor_en="Place, movement, and belonging",
        descriptor_ja="場所と帰属をめぐる記憶",
        keywords=[
            "city", "town", "hometown", "move", "moved", "tokyo", "abroad",
            "overseas", "place", "street", "leave home", "return home",
            "街", "町", "都市", "地元", "故郷", "東京", "海外", "上京", "引っ越",
            "移住", "田舎", "帰郷", "戻",
        ],
    ),
    "intimacy": ObservatoryLensDef(
        id="intimacy",
        name_en="Intimacy",
        name_ja="Intimacy",
        description_en="Closeness, partnership, and the tension between shared life and personal autonomy.",
        description_ja="親密さ、パートナーシップ、そして共に生きることと自律とのあいだの緊張。",
        descriptor_en="The tension between closeness and autonomy",
        descriptor_ja="親密さと自律のあいだの緊張",
        keywords=[
            "love", "lover", "partner", "boyfriend", "girlfriend", "relationship",
            "marry", "married", "divorce", "breakup", "broke up", "date", "dating",
            "恋愛", "恋人", "彼氏", "彼女", "パートナー", "結婚", "離婚", "別れ",
            "付き合", "交際", "親密",
        ],
    ),
    "body": ObservatoryLensDef(
        id="body",
        name_en="Body",
        name_ja="Body",
        description_en="Illness, fatigue, limits, and care — the branch as it was lived in the body.",
        description_ja="病い・疲れ・限界・ケア。身体において生きられた分岐。",
        descriptor_en="The branch as lived in the body",
        descriptor_ja="身体で経験された分岐",
        keywords=[
            "illness", "sick", "disease", "tired", "fatigue", "disability",
            "hospital", "health", "recover", "care", "body",
            "病気", "病", "疲れ", "障害", "入院", "健康", "回復", "介護", "身体", "体調",
        ],
    ),
    "clean-society": ObservatoryLensDef(
        id="clean-society",
        name_en="Clean Society",
        name_ja="Clean Society",
        description_en="Normalization and quiet exclusion — who is asked to absorb social risk, and who stays visible.",
        description_ja="規範化と静かな排除。だれが社会のリスクを引き受け、だれが可視のままでいるのか。",
        descriptor_en="How \"normal\" quietly narrows a choice",
        descriptor_ja="「普通」が選択の幅を静かに狭める",
        keywords=[
            "normal", "should", "supposed to", "shame", "expectation", "proper",
            "普通", "べき", "世間", "恥", "期待", "まとも", "常識", "体裁",
        ],
    ),
    "after-success": ObservatoryLensDef(
        id="after-success",
        name_en="After Success",
        name_ja="After Success",
        description_en="Achievement, recognition, and the identity — or emptiness — that follows.",
        description_ja="達成、承認、そしてそのあとに続く自己、あるいは空白。",
        descriptor_en="What remains after an achievement",
        descriptor_ja="達成のあとに残る問い",
        keywords=[
            "success", "achieve", "achievement", "recognition", "award", "famous",
            "retire", "legacy", "empty",
            "成功", "達成", "評価", "承認", "受賞", "有名", "引退", "功績", "空虚",
        ],
    ),
    "old-web": ObservatoryLensDef(
        id="old-web",
        name_en="Old Web",
        name_ja="Old Web",
        description_en="Early internet culture and archived online identities — returnable digital places.",
        description_ja="初期のインターネット文化と、アーカイブされたオンラインの人格。戻れるかもしれないデジタルの場所。",
        descriptor_en="Digital places that cannot be returned to",
        descriptor_ja="戻れないデジタルの場所",
        keywords=[
            "internet", "online", "website", "blog", "forum", "chat", "sns",
            "ネット", "インターネット", "オンライン", "ブログ", "掲示板", "サイト",
        ],
    ),
    "contact-data": ObservatoryLensDef(
        id="contact-data",
        name_en="Contact Data",
        name_ja="Contact Data",
        description_en="Exposure, personal data, and unwanted visibility on extractive platforms.",
        description_ja="露出、個人データ、そして搾取的なプラットフォーム上の望まない可視性。",
        descriptor_en="Visibility and record-keeping never fully chosen",
        descriptor_ja="可視化され、記録される個人の条件",
        keywords=[
            "data", "privacy", "exposed", "platform", "profile", "visibility",
            "データ", "個人情報", "プライバシー", "露出", "プラットフォーム",
        ],
    ),
    "meaning-layer": ObservatoryLensDef(
        id="meaning-layer",
        name_en="Meaning Layer",
        name_ja="Meaning Layer",
        description_en="Language and symbols — how the meaning of the branch changes over time.",
        description_ja="言語と象徴。分岐の意味が時間とともにどう変わっていくか。",
        descriptor_en="How meaning shifts with time",
        descriptor_ja="意味は時間とともに変わっていく",
        keywords=[
            "meaning", "word", "language", "symbol", "interpret",
            "意味", "言葉", "言語", "象徴", "解釈",
        ],
    ),
    "sound": ObservatoryLensDef(
        id="sound",
        name_en="Sound",
        name_ja="Sound",
        description_en="Remembered voices, places heard through sound, music as a timeline.",
        description_ja="覚えている声、音を通して思い出す場所、時間軸としての音楽。",
        descriptor_en="Memory held in sound",
        descriptor_ja="音として残っている記憶",
        keywords=[
            "voice", "music", "song", "sound", "heard", "silence",
            "声", "音", "音楽", "歌", "静けさ",
        ],
    ),
    "image": ObservatoryLensDef(
        id="image",
        name_en="Image",
        name_ja="Image",
        description_en="Photographs, visual memory, absent and imagined scenes.",
        description_ja="写真、視覚的な記憶、失われた像と想像された情景。",
        descriptor_en="The scene that was never photographed",
        descriptor_ja="写真にならなかった情景",
        keywords=[
            "photo", "photograph", "picture", "image", "scene", "saw",
            "写真", "画像", "光景", "情景", "映像",
        ],
    ),
    "style": ObservatoryLensDef(
        id="style",
        name_en="Style",
        name_ja="Style",
        description_en="Clothing, appearance, and the selves that were or were not inhabited.",
        description_ja="服、見た目、そして生きられた（生きられなかった）自己のかたち。",
        descriptor_en="Appearance as a record of a life lived",
        descriptor_ja="見た目に残る、生きられた記録",
        keywords=[
            "clothes", "clothing", "fashion", "appearance", "wear", "style",
            "服", "服装", "見た目", "ファッション", "装い",
        ],
    ),
}


def is_valid_lens_id(lens_id: str) -> bool:
    """Return True if ``lens_id`` is a supported observatory lens ID."""
    return lens_id in OBSERVATORY_LENSES


def _score_lens(lens: ObservatoryLensDef, text: str) -> int:
    lowered = text.lower()
    return sum(1 for kw in lens.keywords if kw.lower() in lowered)


def select_observatory_lenses(
    source_text: str,
    extra_text: str = "",
    depth: str = "standard",
) -> list[str]:
    """Deterministically select 2–4 relevant observatory lens IDs.

    Selection rules (see product spec §36):
    - 2–3 lenses in standard depth, 3–4 in deep depth.
    - minimum 2, maximum 4, no duplicates, each materially different.
    - Education–Employment preferred for school-to-work branches.
    - Market Signals preferred for housing / income / job / family-formation.
    - Book preferred when a strong narrative structure is present.
    - Protocol Publishing preferred when comparison across anonymous lives
      would reveal a pattern (favored in deep mode).
    Never forces all four core preferred lenses into a single result.
    """
    combined = f"{source_text}\n{extra_text}"

    scored = [
        (lens_id, _score_lens(lens, combined))
        for lens_id, lens in OBSERVATORY_LENSES.items()
    ]
    # Keep lenses with at least one keyword hit, best first. Ties are broken by
    # the enum order (which places the core preferred lenses first).
    order_index = {lid: i for i, lid in enumerate(OBSERVATORY_LENS_IDS)}
    matched = sorted(
        [(lid, score) for lid, score in scored if score > 0],
        key=lambda item: (-item[1], order_index[item[0]]),
    )
    selected = [lid for lid, _ in matched]

    # Ensure Book is available as a literary reading when a narrative exists but
    # was not otherwise selected; it is broadly applicable, so it is a good
    # secondary. Market Signals is the other broadly-applicable fallback.
    for fallback in ("market-signals", "book"):
        if fallback not in selected:
            selected.append(fallback)

    # Protocol Publishing is favored in deep mode when it is not already chosen.
    rich = depth in ("deep", "editorial")
    if rich and "protocol-publishing" not in selected:
        selected.append("protocol-publishing")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    deduped: list[str] = []
    for lid in selected:
        if lid not in seen and is_valid_lens_id(lid):
            seen.add(lid)
            deduped.append(lid)

    max_lenses = 4 if rich else 3
    min_lenses = 3 if rich else 2
    result = deduped[:max_lenses]
    # Guarantee the minimum count (the two fallbacks above ensure enough exist).
    if len(result) < min_lenses:
        for lid in ("market-signals", "book", "protocol-publishing"):
            if lid not in result:
                result.append(lid)
            if len(result) >= min_lenses:
                break
    return result[:max_lenses]


def validate_lens_ids(ids: list[str]) -> list[str]:
    """Filter to valid, unique observatory lens IDs (max 4), preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for lid in ids:
        if is_valid_lens_id(lid) and lid not in seen:
            seen.add(lid)
            out.append(lid)
    return out[:4]
