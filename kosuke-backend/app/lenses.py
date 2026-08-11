"""Lens configuration for the Protocol Experience.

A Lens is a lightweight configuration that shapes how the guided experience
frames fragment generation, sampling, and meaning generation. The MVP ships a
single active lens ("open"), but the interface is designed so that future
lenses (Parallel Life, Decision, Work, Body, City, Relationship) can be added
without changing the experience flow itself.

To add a future lens, register a new Lens in ``LENSES`` and set
``available=True`` once its prompts/seed corpus are tuned. Nothing in the
experience endpoints hardcodes a single lens.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lens:
    """A configurable framing for the meaning-generation experience."""

    id: str
    name_en: str
    name_ja: str
    description_en: str
    description_ja: str
    # Short guidance injected into fragment/meaning generation prompts.
    focus_en: str
    focus_ja: str
    # Thematic tags used to bias sampling / tag experience fragments.
    seed_tags: list[str] = field(default_factory=list)
    available: bool = True


DEFAULT_LENS = "open"


LENSES: dict[str, Lens] = {
    "open": Lens(
        id="open",
        name_en="Open Reflection",
        name_ja="オープン・リフレクション",
        description_en="A free exploration of whatever remains with you.",
        description_ja="いま残っているものを自由に探索します。",
        focus_en="whatever thought, memory, question, or feeling remains with the person",
        focus_ja="その人の中に残っている思考・記憶・問い・感情",
        seed_tags=["experience"],
        available=True,
    ),
    # --- Future lenses (roadmap, not yet active in the UI) ---
    # The first future lens will be "Parallel Life". These are registered so
    # the interface is ready, but marked unavailable so the MVP does not expose
    # them prematurely.
    "parallel_life": Lens(
        id="parallel_life",
        name_en="Parallel Life",
        name_ja="パラレルライフ",
        description_en="Explore a version of your life that could have been.",
        description_ja="ありえたかもしれない、もう一つの人生を探索します。",
        focus_en="a choice, path, or version of the self that could have unfolded differently",
        focus_ja="別の形でありえた選択・道・自分",
        seed_tags=["experience", "parallel_life"],
        available=False,
    ),
    "decision": Lens(
        id="decision",
        name_en="Decision",
        name_ja="ディシジョン",
        description_en="Sit with a decision you have not yet made.",
        description_ja="まだ下していない決断と向き合います。",
        focus_en="a decision the person is holding and has not yet resolved",
        focus_ja="その人が抱えている、まだ決めていない決断",
        seed_tags=["experience", "decision"],
        available=False,
    ),
    "work": Lens(
        id="work",
        name_en="Work",
        name_ja="ワーク",
        description_en="Reflect on your relationship with work.",
        description_ja="仕事との関係を見つめ直します。",
        focus_en="the person's relationship with work, craft, and purpose",
        focus_ja="仕事・技・目的との関係",
        seed_tags=["experience", "work"],
        available=False,
    ),
    "body": Lens(
        id="body",
        name_en="Body",
        name_ja="ボディ",
        description_en="Listen to what the body remembers.",
        description_ja="身体が覚えているものに耳を澄まします。",
        focus_en="the felt, embodied, physical dimension of the person's experience",
        focus_ja="身体的に感じられている経験の次元",
        seed_tags=["experience", "body"],
        available=False,
    ),
    "city": Lens(
        id="city",
        name_en="City",
        name_ja="シティ",
        description_en="Trace a place that stays with you.",
        description_ja="心に残る場所をたどります。",
        focus_en="a place, city, or environment that stays with the person",
        focus_ja="その人の中に残る場所・都市・環境",
        seed_tags=["experience", "city"],
        available=False,
    ),
    "relationship": Lens(
        id="relationship",
        name_en="Relationship",
        name_ja="リレーションシップ",
        description_en="Hold a relationship that is still open.",
        description_ja="まだ開いたままの関係と向き合います。",
        focus_en="a relationship or connection that remains unresolved for the person",
        focus_ja="その人の中で未解決のままの関係やつながり",
        seed_tags=["experience", "relationship"],
        available=False,
    ),
}


def get_lens(lens_id: str | None) -> Lens:
    """Return the requested lens, falling back to the default lens."""
    if not lens_id:
        return LENSES[DEFAULT_LENS]
    return LENSES.get(lens_id, LENSES[DEFAULT_LENS])


def available_lenses() -> list[Lens]:
    """Return the lenses currently exposed to users."""
    return [lens for lens in LENSES.values() if lens.available]
