"""Shared fixtures for Editorial Edition single-essay tests."""

from __future__ import annotations

from typing import Any

# Book-style fertility essay — family-formation markers, no creativity takeover.
FERTILITY_ESSAY_JA: dict[str, Any] = {
    "title": "三人になった45歳",
    "subtitle": "かなった願いの隣に、まだ開いている分岐がある。",
    "branch_point": (
        "45歳のとき、不妊治療を経て子どもを授かった。"
        "その選択は、妻と息子と三人で暮らす人生を開いた。"
    ),
    "chosen_path": (
        "選んだ道は、治療を続け、家族三人の生活を築くことだった。"
        "住まいと仕事の運営も、その三人の時間に合わせて形を変えていった。"
    ),
    "unchosen_life": (
        "選ばなかった道は、不妊治療を諦めることだった。"
        "その道では、別の生活のリズムが続いていたかもしれない。"
    ),
    "lost": [
        "治療を続けない場合に見えていた時間の使い方",
        "二人だけの生活設計のまま進んでいた可能性",
        "二人目を持たない前提での、別の余白",
    ],
    "protected": [
        "妻と息子と三人で暮らす日々",
        "子どもを授かったという事実",
        "家庭が開かれた場所になっている感覚",
    ],
    "residue": (
        "叶った願いの隣に、まだ次の家族の形をめぐる問いが残っている。"
        "それは後悔というより、実現した生活のそばに並ぶ、別の分岐の影である。"
    ),
    "observatory_layers": [
        {
            "id": "intimacy",
            "body": (
                "親密さのレイヤーでは、三人という関係の密度が、"
                "以前の二人の時間とは違う支え方を求めている。"
            ),
        },
        {
            "id": "body",
            "body": (
                "身体のレイヤーでは、治療と出産を経た時間が、"
                "今の生活のリズムに静かに残っている。"
            ),
        },
        {
            "id": "book",
            "body": (
                "記録のレイヤーでは、家族の記憶をどう残すかという問いが、"
                "現在の生活のなかで開いている。"
            ),
        },
    ],
    "cross_lens_synthesis": (
        "親密さと身体、記録のレイヤーを重ねると、"
        "この分岐は「得られなかったもの」ではなく、"
        "得たものの隣に残る問いとして読める。"
    ),
    "rebranch": [
        "二人目をめぐる問いを、結論ではなく観察として置いてみる",
        "三人の生活のなかで、余白をどう設計するかを見直す",
        "家族の記録を、今の暮らしに合う形で残してみる",
    ],
    "closing": (
        "選ばなかった道は消えないが、いま立っているのは三人の生活である。"
        "問いは答えに急がなくてよい。現在の生活へ、静かに戻る。"
    ),
}

UNIVERSITY_ESSAY_JA: dict[str, Any] = {
    "title": "第一志望に進んだ年",
    "subtitle": "合格という事実のあとに残る、別の想像。",
    "branch_point": (
        "第一志望の早稲田大学第一文学部に受かった。"
        "実際に選んだのは、進学することだった。"
    ),
    "chosen_path": "選んだ道は、早稲田大学へ進学し、学びに身を置くことだった。",
    "unchosen_life": "選ばなかった道は、進学を諦めることだった。",
    "lost": ["進学しなかった場合の生活リズム", "別の進路で見えていた交友"],
    "protected": ["第一志望への進学", "学びを続けられた時間"],
    "residue": "合格して進んだあとも、別の道の想像が静かに残ることがある。",
    "observatory_layers": [
        {"id": "education-employment", "body": "進学は、その後の就労への橋渡しとしても読める。"},
        {"id": "protocol-publishing", "body": "この分岐は、個人の履歴としてではなく、選択の構造として残る。"},
        {"id": "book", "body": "記録として見ると、合格と進学は一つの章の始まりである。"},
    ],
    "cross_lens_synthesis": "教育と記録のレイヤーを重ねると、進学は到達点ではなく継続の起点に見える。",
    "rebranch": ["学びの意味を今の言葉で書き直す", "進学しなかった想像を、裁かずに置いておく"],
    "closing": "選んだ道のうえに立ったまま、問いは現在の生活へ戻る。",
}


def patch_editorial_essay(monkeypatch, essay: dict[str, Any] | None = None) -> None:
    """Force Editorial Edition to use a fixed essay JSON (no real OpenAI call)."""
    payload = essay if essay is not None else FERTILITY_ESSAY_JA
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    def _fake_chat_json(api_key: str, system: str, user: str, *, max_tokens: int = 4500):
        return payload

    monkeypatch.setattr(
        "app.parallel_life_editorial_essay._chat_json",
        _fake_chat_json,
    )
