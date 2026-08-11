"""Parallel Life Lens configuration.

Parallel Life is the first primary public experience of Kosuke Protocol. This
module owns the single typed configuration object that describes the lens to
the frontend — entry prompts, supported depths, the enumerated Observatory
Lenses, and the seed corpus identifier — so none of this is hardcoded into the
UI (see product spec §8, §38-39).

The lens is activated (``available=True``) once its generation logic has
passing tests (product spec §47 step 23). It is intentionally separate from
the generic six-stage ``app.lenses`` registry: Parallel Life does not use the
Fragment / Sample / Fluke / Reflection / Meaning flow at all, it has its own
dedicated endpoint and document shape.
"""

from __future__ import annotations

from app.models import ObservatoryLensInfo, ParallelLifeLensConfig
from app.observatory_lenses import OBSERVATORY_LENS_IDS, OBSERVATORY_LENSES
from app.parallel_life_seed import SEED_CORPUS_ID

PARALLEL_LIFE_LENS_ID = "parallel-life"


def _observatory_lens_infos() -> list[ObservatoryLensInfo]:
    return [
        ObservatoryLensInfo(
            id=lens_id,
            name_en=OBSERVATORY_LENSES[lens_id].name_en,
            name_ja=OBSERVATORY_LENSES[lens_id].name_ja,
            description_en=OBSERVATORY_LENSES[lens_id].description_en,
            description_ja=OBSERVATORY_LENSES[lens_id].description_ja,
        )
        for lens_id in OBSERVATORY_LENS_IDS
    ]


def get_parallel_life_lens_config() -> ParallelLifeLensConfig:
    """Return the typed Parallel Life lens configuration for the frontend."""
    return ParallelLifeLensConfig(
        id=PARALLEL_LIFE_LENS_ID,
        name="Parallel Life",
        name_ja="パラレルライフ",
        description_en=(
            "A private life branch, read as a chosen path, an unchosen life, "
            "and the social conditions that shaped both."
        ),
        description_ja=(
            "人生のひとつの分岐を、選んだ道・選ばなかった人生・そしてその両方を"
            "形づくった社会的な条件として読む体験です。"
        ),
        available=True,
        entry_prompts_en={
            "heading": "Is there a turning point in your life that still returns to you?",
            "support": (
                "A job you did not take, a city you did not live in, a relationship you "
                "did not continue, or a creative path you left behind.\n"
                "Write only what happened. You do not need a conclusion."
            ),
            "placeholder": (
                "Example:\nAt twenty, I ended a relationship and returned to my hometown "
                "for work.\nSometimes I wonder whether we might have married if I had "
                "stayed in Tokyo."
            ),
        },
        entry_prompts_ja={
            "heading": "あなたの人生で、\n今もときどき思い出す分岐はありますか。",
            "support": (
                "選ばなかった仕事、住まなかった街、続けなかった関係、やめた創作。\n"
                "事実だけを書いてください。結論は必要ありません。"
            ),
            "placeholder": (
                "例：\n20歳のとき、彼氏と別れて、就職のために田舎へ帰った。\n"
                "あのまま東京に残っていたら、結婚していたのかなと思うことがある。"
            ),
        },
        supported_depths=["standard", "editorial"],
        observatory_lenses=_observatory_lens_infos(),
        seed_corpus_id=SEED_CORPUS_ID,
    )
