"""Curated seed corpus for the Parallel Life lens.

This corpus is intentionally separate from the open Lens corpus
(``app.experience_engine.SEED_FRAGMENTS_*``). It is not used for vector
sampling — Parallel Life does not read from the ChromaDB fragment ecosystem —
it is used by the heuristic generator to add one restrained, literary line of
texture to the Residue and Closing sections, and it documents the conceptual
domains the Parallel Life Lens is built to reason about.

Every fragment is original (not a quotation), independently understandable,
and tagged with a conceptual domain so the Observatory Lens selection logic
and the heuristic generator can draw on relevant material.
"""

from __future__ import annotations

SEED_CORPUS_ID = "parallel_life_seed_v1"


PARALLEL_LIFE_SEED_JA: list[dict[str, str]] = [
    {"text": "分岐点は選んだ瞬間には見えず、あとになってようやく輪郭を持つ。", "domain": "timing"},
    {"text": "選ばなかった道は、完成した作品ではなく、開いたままの問いである。", "domain": "unchosen-path"},
    {"text": "ひとつの選択は、同時にいくつもの生活の条件を決めてしまう。", "domain": "constraint"},
    {"text": "戻るという言葉は、同じ場所に帰ることではなく、同じ感覚を探すことを指すことがある。", "domain": "return"},
    {"text": "続けなかった創作は、失われたのではなく、別の形でまだ待っている。", "domain": "unrealized-creativity"},
    {"text": "自律と親密さは、いつも同じ量だけ手に入るわけではない。", "domain": "autonomy"},
    {"text": "移動は、場所を変えるだけでなく、誰と時間を過ごすかを変える。", "domain": "migration"},
    {"text": "守られたものは、失われたものと同じ重さで、静かにそこにある。", "domain": "continuity"},
    {"text": "安定は選択の結果であると同時に、その後の選択の範囲を決める条件にもなる。", "domain": "stability"},
    {"text": "帰属は一度で決まるものではなく、何度も選び直されるものだ。", "domain": "belonging"},
    {"text": "ケアの時間は他の時間を削るが、削られた時間の分だけ何かが守られてもいる。", "domain": "care"},
    {"text": "可能性は、実現しなかったことによって消えるのではなく、形を変えて残る。", "domain": "possibility"},
    {"text": "その時代に何が「普通」とされていたかは、個人の選択の重さを変えてしまう。", "domain": "historical-conditions"},
    {"text": "取り戻すことと、繰り返すことは、似ているようでまったく違う行為だ。", "domain": "recovery-vs-reversal"},
    {"text": "ひとつの分岐のなかに、恋愛だけでなく、住まいや仕事の条件も同時に含まれている。", "domain": "intimacy"},
    {"text": "働き続けることは、ときに自分の時間を差し出すことで、ときに自分を保つことでもある。", "domain": "work"},
]

PARALLEL_LIFE_SEED_EN: list[dict[str, str]] = [
    {"text": "A branch point rarely looks like one at the moment it is crossed.", "domain": "timing"},
    {"text": "The unchosen path is not a finished work but a question left open.", "domain": "unchosen-path"},
    {"text": "A single choice quietly sets the terms for many other choices at once.", "domain": "constraint"},
    {"text": "To return is sometimes not to reach the same place, but to search for the same feeling.", "domain": "return"},
    {"text": "A creative practice left unfinished is not lost — it waits in another shape.", "domain": "unrealized-creativity"},
    {"text": "Autonomy and intimacy are not always available in equal measure.", "domain": "autonomy"},
    {"text": "To move is not only to change a place, but to change who you spend time with.", "domain": "migration"},
    {"text": "What was protected sits with the same quiet weight as what was lost.", "domain": "continuity"},
    {"text": "Stability is both the result of a choice and a condition that shapes the choices after it.", "domain": "stability"},
    {"text": "Belonging is rarely decided once; it is chosen again and again.", "domain": "belonging"},
    {"text": "Time spent in care takes time from elsewhere, and something is protected by that same act.", "domain": "care"},
    {"text": "A possibility does not vanish by going unlived; it changes shape and stays.", "domain": "possibility"},
    {"text": "What an era treated as ordinary quietly changes how heavy a single choice feels.", "domain": "historical-conditions"},
    {"text": "To recover something and to repeat it are close in appearance, but not the same act.", "domain": "recovery-vs-reversal"},
    {"text": "A single branch usually holds housing and work inside what looks like only a matter of love.", "domain": "intimacy"},
    {"text": "Staying in work can mean giving your time away, and it can also mean keeping yourself intact.", "domain": "work"},
]


def get_parallel_life_seed(language: str) -> list[dict[str, str]]:
    """Return the Parallel Life seed corpus for the active language."""
    return PARALLEL_LIFE_SEED_JA if (language or "").lower().startswith("ja") else PARALLEL_LIFE_SEED_EN


def seed_line_for_domain(
    language: str,
    domain: str,
    fallback_index: int = 0,
    *,
    allowed_domains: set[str] | None = None,
) -> str:
    """Return a seed line matching ``domain`` if allowed; never cross primary domain."""
    corpus = get_parallel_life_seed(language)
    if allowed_domains is not None and domain not in allowed_domains:
        # Fall back inside the allowed set only — never inject creativity into family cases.
        allowed_items = [item for item in corpus if item["domain"] in allowed_domains]
        if allowed_items:
            return allowed_items[fallback_index % len(allowed_items)]["text"]
        return ""
    matches = [item["text"] for item in corpus if item["domain"] == domain]
    if allowed_domains is not None:
        matches = [item["text"] for item in corpus if item["domain"] == domain and domain in allowed_domains]
    if matches:
        return matches[fallback_index % len(matches)]
    if allowed_domains is not None:
        allowed_items = [item for item in corpus if item["domain"] in allowed_domains]
        if allowed_items:
            return allowed_items[fallback_index % len(allowed_items)]["text"]
        return ""
    return corpus[fallback_index % len(corpus)]["text"]
