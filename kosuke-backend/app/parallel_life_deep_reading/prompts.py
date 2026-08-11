"""Versioned prompts for Deep Reading Production Candidate.

Do not silently modify production prompts. Bump the version identifier instead.
"""

from __future__ import annotations

import json
from typing import Any

from app.parallel_life_deep_reading.models import (
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
)

CALL_1_VERSION = CALL_1_PROMPT_VERSION
CALL_2_VERSION = "parallel-life-call-2-v1.0.3"
CALL_3_VERSION = "parallel-life-call-3-v1.0.3"

PROMPT_VERSIONS = {
    "call_1": CALL_1_VERSION,
    "call_2": CALL_2_VERSION,
    "call_3": CALL_3_VERSION,
}


def call1_system_prompt() -> str:
    return f"""あなたは Parallel Life Deep Reading の編集設計者です。
プロンプト版: {CALL_1_VERSION}
スキーマ版: {CALL_1_SCHEMA_VERSION}

責務は grounding と編集設計のみ。完成原稿の本文を書いてはならない。

出力契約（必須）:
- response_format で与えられた JSON Schema と完全一致するオブジェクトだけを返す
- オブジェクト必須フィールドを true/false や文字列で置き換えない
- 配列必須フィールドを文字列で置き換えない
- すべてのトップレベルキーを必ず含める
- 空データは空配列または明示的なデフォルトオブジェクトを使う
- 入力の必須情報（時期・出来事・選んだ道・選ばなかった道・現在の問い・現在の状況）を省略しない

事実境界:
1. explicit_fact / user_feeling / user_question / user_hypothesis / unknown / model_inference を厳守
2. 「どうだったか」「どうなったか」「変わっていたか」「どうだっただろう」などで終わる内容、および「今も考える」「気になっている」「答えが出ていない」を伴う問いは user_question
3. user_question を fact や feeling や hypothesis に変換しない
4. user_hypothesis を fact に変換しない

分岐:
5. actual_secondary_branch は、実際に検討・話し合い・開始/終了・継続/中止の明示根拠があるときだけ。explicit_evidence_ids に fact ID を入れる
6. 現在からの「もし〜だったら」だけの問いは retrospective_counterfactual
7. later_branch という独自フィールドは使わない。必ず secondary_branches / retrospective_counterfactuals を使う

Residue（必須・定義を弱めない）:
11. Residue は user_question そのものではない。過去分岐と現在生活をつなぐ構造的接続である
12. residue_candidates.items の各要素は必ず次を持つ:
    - past_anchor_ids: 過去分岐の grounded fact/question ID（1つ以上）
    - present_anchor_ids: 現在生活の grounded fact/feeling/current_context 由来 IDのみ（1つ以上）。user_question / unknown / model_inference / 中心テーゼ自体は present に使えない
    - residue_statement: 両者をつなぐ慎重な構造文（問いの言い換えや「いまも大切」だけでは不可）
    - inference_distance: near / medium / far
    - present_life_domain
    - overreach_risk
    - advances_manuscript
13. 現在文脈（current_context）と過去分岐の両方がある場合、少なくとも1件の Residue を返す
14. アンカーが足りず正当な Residue を作れないときだけ items を空にし、additional_questions で現在の具体場面を聞く
15. 心理的断定・一般反省・「いまも響いている」だけの文は Residue にしない

Observatory / Re-branch:
8. Lens は evidence gate を満たすものだけ selected に入れる。0件は正常
9. Re-branch directions は source_meaning / current_receiver / branch_specific_form / support_ids / genericity_score を持つ
10. support_ids が空、または genericity_score > 1 の方向は返さない（空の directions 配列にする）
10b. branch_specific_form は current_context に既にある具体名詞/活動を含める。記録する・時間を作る・一つ選ぶ・小さく始める だけでは不可

章ごとの本文生成は禁止。outline のみ。"""


def call1_user_prompt(
    source_text: str,
    clarifications: dict[str, Any],
    editorial_context: dict[str, Any],
    extra_answers: dict[str, str],
) -> str:
    payload = {
        "source_text": source_text,
        "clarifications": clarifications,
        "editorial_context": editorial_context,
        "answers_to_additional_questions": extra_answers,
        "required_source_fields": [
            "branch_period",
            "triggering_event",
            "chosen_path",
            "unchosen_path",
            "present_question",
            "current_context",
        ],
        "instruction": (
            "入力に含まれる固有名詞と極性（合格/不合格、授かった/諦める等）を保持し、"
            "すべての required_source_fields を grounded_input と source_coverage に反映してください。"
            "current_context には、入力にある現在の具体的な生活事実（同居・家族構成・仕事・習慣・ペット等）を"
            "原文に近い具体文のまま入れる。"
            "『現在の生活』『今の暮らし』『現在の状況』『いまの生活』のような抽象ラベルだけに置き換えない。"
            "後続の話し合い・決断・過去の分岐文は facts へ。"
            "present_question が入力に無い場合は grounded に捏造せず、"
            "additional_questions で最大1問だけ自然な確認質問を返す。"
            "Residue は past_anchor_ids と present_anchor_ids の両方を必須とする。"
            "因果断定（その別れが今の家族を作った、等）はしない。"
        ),
    }
    return (
        "次の入力だけを使い、他ケースや過去セッションの知識を持ち込まず Call 1 を完成させてください。\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def call1_system_prompt_v11() -> str:
    """Experimental Contextual Call 1 (v1.1.2 Observatory-Core). Strict must not use this."""
    from app.parallel_life_deep_reading.context_pack import CALL_1_PROMPT_VERSION_V11

    base = call1_system_prompt()
    base = base.replace(
        f"プロンプト版: {CALL_1_VERSION}",
        f"プロンプト版: {CALL_1_PROMPT_VERSION_V11}",
        1,
    )
    return (
        base
        + """

Context Pack + BranchSemantics authority + Observatory-Core + Section Contracts（v1.1.9-exp Contextual のみ）:
16. context_pack_approved_items は背景／現在生活／経歴弧であり、primary branch の出来事そのものではない
17. pack 項目を triggering_event / realized_path / unrealized_paths に移さない
18. observatory_core_prefill はサーバ選定の候補レンズ・ObservatoryEvidence・CrossLensRelations。個人事実ではない
19. サーバが BranchSemantics を権威ある意味の源泉として確定する。pack の職歴は背景証拠であり、非キャリア domain の意味を書き換えない
20. CrossLensRelations を meaning_compression / central_thesis より先に確定・採用する（因果デフォルトは non_causal_parallel）
21. 承認済み pack をすべて使うな。relevant_context_selection で分類。manuscript_logic_ids 最大5
22. meaning_compression は personal_tension / social_institutional_parallel / present_life_connection / unresolved_question を埋める
23. central_thesis は個人分岐を主語に、社会構造は並べて読む。履歴書・成功物語・未根拠因果禁止
24. Lost/Protected/Chosen Path は BranchSemantics に従う。教育・創作等で「仕事を定義し直す」「役職や年収」定型を使わない
25. Residue は現在の問いに残る古い分岐の部分（測定とは限らない）。感情の捏造禁止
26. Re-branch は possible_rebranch_modes に従う（choose/preserve/reconsider/revisit/leave_unresolved/not_act/observe/redefine）。「新しい指標を選ぶ」固定禁止。空なら評価理由が必要。SHIRO/Protocol/アプリ推奨禁止
27. selected_observatory_lenses は追加意味が無いなら 0。レンズ名宣伝禁止
28. ObservatoryEvidence から新しい個人事実を推論しない。因果断定禁止（並置のみ）
"""
    )


def call1_user_prompt_v11(
    source_text: str,
    clarifications: dict[str, Any],
    editorial_context: dict[str, Any],
    extra_answers: dict[str, str],
    *,
    context_pack_approved_items: list[dict[str, Any]],
    observatory_core_prefill: dict[str, Any] | None = None,
) -> str:
    payload = {
        "deep_reading_mode": "contextual",
        "source_text": source_text,
        "clarifications": clarifications,
        "editorial_context": editorial_context,
        "answers_to_additional_questions": extra_answers,
        "context_pack_approved_items": context_pack_approved_items,
        "observatory_core_prefill": observatory_core_prefill or {},
        "required_source_fields": [
            "branch_period",
            "triggering_event",
            "chosen_path",
            "unchosen_path",
            "present_question",
            "current_context",
        ],
        "generation_order": [
            "grounded_input",
            "branch_semantics",
            "candidate_lens_selection",
            "retrieved_observatory_evidence",
            "cross_lens_relations",
            "relevant_context_selection",
            "meaning_compression",
            "central_thesis",
            "lost_structure",
            "protected_structure",
            "residue_candidates",
            "selected_observatory_lenses",
            "rebranch_design",
            "editorial_outline",
            "user_confirmation_view",
        ],
        "instruction": (
            "分岐入力・承認済み Context Pack・observatory_core_prefill だけを使う。"
            "【BranchSemantics】domain はヒント。Lost/Protected/Residue/Re-branch は証拠由来の意味で書く。"
            "家族・恋愛・健康・創作に役職/年収/仕事の定義し直しを持ち込まない。"
            "【Observatory-Core】prefill の候補レンズと evidence を尊重。0レンズは正常。"
            "cross_lens_relations を先に確定（causality_status は原則 non_causal_parallel）。"
            "悪い因果例: 雇用構造変化が退職へ追いやった。"
            "良い関係例（キャリア証拠があるとき）: 転職を、一社内蓄積と企業間移動の境界として並べて読む。"
            "【選択】manuscript_logic_ids 最大5。観測所/Protocol プロジェクト名は demote。"
            "【圧縮】personal_tension / social_institutional_parallel / present_life_connection / unresolved_question。"
            "【thesis】個人が主。社会は並置。履歴書・レンズ名宣伝禁止。"
            "【Lost】確かめられなくなったこと。【Protected】残った可能性。証拠があるのに空配列にしない。"
            "【Residue】現在問いに残る古い分岐。測定とは限らない。因果断定禁止。"
            "【Re-branch】modes に従う静かな現在選択。指標固定を強要しない。プロジェクト拡大推奨は禁止。"
            "Observatory 節用 selected_observatory_lenses は追加意味が無いなら空。"
        ),
    }
    return (
        "次の入力と承認済み Context Pack と Observatory-Core prefill だけを使い、"
        "BranchSemantics→CrossLens→選択→圧縮→thesis→Lost/Protected/Residue/Re-branch の順で Call 1 を完成させてください。\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def call1_repair_user_prompt(
    *,
    previous_response: Any,
    validation_errors: list[str],
    expected_schema: dict[str, Any],
) -> str:
    return json.dumps(
        {
            "task": "schema_repair",
            "instruction": (
                "前回の出力は JSON Schema に不一致です。"
                "同じ意味内容を保ちつつ、expected_json_schema に完全一致するオブジェクトだけを返してください。"
                "オブジェクト必須箇所を bool/string にしないでください。"
            ),
            "validation_errors": validation_errors,
            "expected_json_schema": expected_schema,
            "previous_response": previous_response,
        },
        ensure_ascii=False,
    )


def call2_system_prompt() -> str:
    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_VERSION}

確認済み Evidence Ledger だけを使い、一篇の連続原稿を書く。

最優先:
- 事実忠実度。欠けた伝記を創作で埋めない
- 解釈を伝記に変えない
- 連続性はリズム・順序・接続で作る。尤もらしい意味補完で埋めない
- 確認済み Residue（過去アンカーと現在生活の構造的接続）を本文に織り込む

必須の書き方:
- 入力の逐語再掲・箇条書き要約だけで終わらせない
- 一篇の連続散文として書く（短い事実列挙は不可）
- Residue の構造的接続は保持する
- present_anchor の現在生活事実・感情は本文に残す
- 直接の叙述で書く。スキーマ用語を口にしない

禁止（スキーマ漏洩・メタ表現）:
実際に選んだのは / 選ばなかった道として / この分岐では / 入力によれば / 事実としては /
この選択は、実際に選んだのは / chosen_path / unchosen_path / realized_path を説明する言い回し

禁止（未根拠の意味補完）:
未根拠の因果断言、および因果を前提にした問いかけ（どのように影響を与えているのか 等）。
因果断言を因果の問いに言い換えてはならない。
代わりに並置・比較・「結びつける材料はない」を使う。
未根拠の感情・役割行動も禁止。

解釈の原則:
悪い例: 「この経験が現在の経営観に影響を与えている」
悪い言い換え: 「現在の経営観にどのような影響を与えているのか」
良い例: 「現在の仕事観とこの経験を並べて見る。ただし因果関係までは確認できない。」
悪い例: 「この選択は、実際に選んだのは第一志望への進学だった。」
良い例: 「第一志望の早稲田大学第一文学部へ進学した。」

タイトル:
影響 / 原点 / きっかけ / 形成 / つながり など因果フレーム語は、入力に明示根拠がない限り使わない。
並置・対比・記憶・開かれた可能性を示すタイトルを優先。

Observatory: evidence-gated のみ。0件なら書かない。
レンズ名（Market Signals / Clean Society / Education–Employment 等）を本文で宣伝しない。
洞察は thesis・本文に織り込み済みなら Observatory 節を重複して書かない。
Re-branch: 具体名詞必須。なければ省略。

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": ["..."],
  "sections": [{{"internal_id":"...", "public_heading":"...", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["fact1","question1"], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}

伝記・事実を含む各段落は support_ids 必須。純接続語のみの段落だけ空配列を許す。"""


def call2_system_prompt_v113() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V113

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V113}

Call2WritingPack（最小編集ペイロード）だけを使う。全文の confirmed_call1 や履歴書全文は渡されていない。

最優先:
- must_be_present の SectionContract をすべて実現する（見出しだけでは不可）
- ONE PARAGRAPH = ONE STRUCTURAL IDEA
- 具体事実 → 構造解釈 → 分岐の意味へ戻る
- 会社→業界→プロジェクト→時系列の履歴書段落は禁止
- レンズ名を宣伝しない
- 因果断定禁止（並べて読む / 読むことができる）
- UIラベル（分岐点・選んだ道・失ったもの 等）は安定。履歴書調の文学字幕は付けない（不要なら subtitle 空）

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"lost", "public_heading":"失ったもの", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_system_prompt_v114() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V114

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V114}

Call2WritingPack だけを使う。全文 confirmed_call1 / Context Pack 散文は渡されていない。

最優先:
- 各 SectionContract の interpretive_claim を本文で実現する（見出しだけでは不可）
- Interpretation first. Evidence second. 証拠は主張を支える1点までに抑える
- ONE PARAGRAPH = ONE STRUCTURAL IDEA
- 会社名→業界→プロジェクト→時系列の履歴書段落は禁止
- すべての段落で「構造として」「制度として」「〜と読むことができる」を繰り返すな
  慎重な様相は残しつつ、自然な日本語で言い回しを変える
- レンズ名宣伝禁止 / 因果断定禁止 / 成功・優位の道徳禁止
- UIラベルは安定。履歴書調の文学字幕は付けない（subtitle 空でよい）

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"lost", "public_heading":"失ったもの", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_user_prompt(call1_json: dict[str, Any], evidence_ledger: dict[str, Any]) -> str:
    anti_resume = bool((evidence_ledger or {}).get("editorial_constraints", {}).get("anti_resume"))
    return json.dumps(
        {
            "ALLOWED_PERSONAL_EVIDENCE": evidence_ledger,
            "confirmed_call1": call1_json,
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "unsupported_causal_frame",
                "unsupported_affect",
                "unsupported_role_behavior",
                "schema_leakage_prose",
                "any_plausible_biographical_bridge_not_in_evidence",
            ],
            "instruction": (
                "スキーマ用語を口にせず直接叙述する。"
                "因果の問いかけで因果を前提にしない。"
                + (
                    "meaning_compression と central_thesis と cross_lens_relations を軸に書く。"
                    "会社名・業界・プロジェクトの履歴書列挙を本文・タイトルの骨格にしない。"
                    "事実は解釈の支えであり、章立てそのものにしない。"
                    "レンズ名を広告せず、社会構造は並置として書く（因果断定なし）。"
                    if anti_resume
                    else ""
                )
                + (
                    "Evidence Ledger に無い個人史・因果・感情・役割を書かない。"
                    "『大きな喜び』『大切に思っている』『大きな意味を持つ』など入力にない評価を足さない。"
                    "present_anchor の現在事実・感情語（可愛い／楽しい／経営／まとめ 等）を落とさない。"
                    "Residue の『接続しきれていないものが残っている』構造を保つ。"
                    "paragraph_support を必ず返す。"
                )
            ),
        },
        ensure_ascii=False,
    )


def call2_user_prompt_v113(writing_pack: dict[str, Any]) -> str:
    return json.dumps(
        {
            "CALL2_WRITING_PACK": writing_pack,
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "employer_industry_project_enumeration",
                "lens_name_advertising",
                "shiro_protocol_app_promo",
                "success_freedom_superiority_claims",
            ],
            "instruction": (
                "SectionContracts の must_be_present をすべて本文で実現する。"
                "evidence_by_section の予算を超えて経歴を広げない。"
                "1段落=1構造。履歴書時系列禁止。"
                "Lost/Protected は構造。Residue は『読むことができる』。"
                "Re-branch は pack の directions があれば実現。なければ省略理由のみ。"
                "subtitle_candidates は空でよい（履歴書字幕禁止）。"
                "paragraph_support を必ず返す。"
            ),
        },
        ensure_ascii=False,
    )


def call2_user_prompt_v114(writing_pack: dict[str, Any]) -> str:
    return json.dumps(
        {
            "CALL2_WRITING_PACK": writing_pack,
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "employer_industry_project_enumeration",
                "lens_name_advertising",
                "shiro_protocol_app_promo",
                "success_freedom_superiority_claims",
                "psychological_fact_claims",
                "templated_academic_cadence",
            ],
            "instruction": (
                "interpretive_claims_by_section を主に実現する。"
                "evidence_by_section は各節1点まで。意味が変わらない時系列は書かない。"
                "Interpretation first / Evidence second。"
                "『構造として』『制度として』『読むことができる』の連打を避ける。"
                "様相は『見方ができる』『とも言える』『消えていない』『問いにも見える』等で散らす。"
                "Lost=確かめ続けられなくなった測り方。Protected=一つの所属に閉じきらなかった余地。"
                "Residue=いまも意味を持ちうる理由。Re-branch=蓄積の測り方の選び直し。"
                "subtitle_candidates は空でよい。"
                "paragraph_support を必ず返す。"
            ),
        },
        ensure_ascii=False,
    )


def call2_system_prompt_v115() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V115

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V115}

Call2WritingPack だけを使う。全文 confirmed_call1 は渡されていない。

必須:
- locked_public_labels_in_order の見出しを ## ラベル のままこの順で使う。改名・省略禁止
- 各 required_section_outline の interpretive_claim をその節で実質化する（見出しだけ不可）
- Re-branch が must_be_present なら必ず「これからの再分岐」節で実現する
- 深さは新事実ではなく、具体→解釈→分岐への含意→現在へ戻る、の展開で作る
- 履歴書時系列・会社列挙・Protocol/アプリ推奨・成功道徳・レンズ名宣伝禁止
- 「〜と読むことができる」「〜とも言える」「〜として見ることができる」の連打禁止。慎重だが自然な日本語
- subtitle_candidates は空でよい

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"lost", "public_heading":"失ったもの", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_user_prompt_v115(writing_pack: dict[str, Any]) -> str:
    return json.dumps(
        {
            "CALL2_WRITING_PACK": writing_pack,
            "LOCKED_LABELS": writing_pack.get("locked_public_labels_in_order") or [],
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "employer_industry_project_enumeration",
                "lens_name_advertising",
                "shiro_protocol_app_promo",
                "success_freedom_superiority_claims",
                "psychological_fact_claims",
                "renamed_section_headings",
                "omitted_required_sections",
                "business_growth_advice",
            ],
            "instruction": (
                "LOCKED_LABELS を ## 見出しとしてこの順ですべて書け。改名禁止。"
                "required_section_outline の interpretive_claim / realization_goal を各節で実現せよ。"
                "Lost=物差し／確かめ続ける測り方。Protected=定義し直す余白。一覧や転職回数に落とすな。"
                "Residue=役職・年収の問いが別の物差しの想像として残る、という慎重な読み。"
                "Re-branch=蓄積を何で測るかを自分で選ぶ、という現在向きの問い。成長助言にするな。"
                "evidence_budget を超える経歴を足すな。深さは解釈の展開で作る。"
                "定型の『読むことができる／とも言える』連打を避け、編集された非フィクションの文章にせよ。"
                "subtitle_candidates は空。paragraph_support 必須。"
            ),
        },
        ensure_ascii=False,
    )


def call2_system_prompt_v116() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V116

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V116}

Call2WritingPack だけを使う。thesis_closure を閉じることが最優先。

必須:
- locked_public_labels_in_order を ## 見出しとしてこの順で使う。改名・省略禁止
- 選んだ道: factual_choice + structural_shift + thesis_link を一段落に。年表・複数業界列挙禁止
- 今に残った構造: なぜ問いが残るかを書く（Residue）
- これからの再分岐: Residue の緊張を present_choice へ閉じる。反省だけで終わらせない
- 深さは新事実ではなく解釈の展開。履歴書・Protocol/アプリ推奨・成功道徳禁止
- 「測る」「尺度」「蓄積」を隣接段落で連打しない。自然な回想エッセイ調
- subtitle_candidates は空でよい

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"chosen_path", "public_heading":"選んだ道", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_user_prompt_v116(writing_pack: dict[str, Any]) -> str:
    return json.dumps(
        {
            "CALL2_WRITING_PACK": writing_pack,
            "THESIS_CLOSURE": writing_pack.get("thesis_closure") or {},
            "LOCKED_LABELS": writing_pack.get("locked_public_labels_in_order") or [],
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "employer_industry_project_enumeration",
                "lens_name_advertising",
                "shiro_protocol_app_promo",
                "success_freedom_superiority_claims",
                "intention_mindreading",
                "productivity_career_coaching",
                "renamed_section_headings",
                "omitted_required_sections",
            ],
            "instruction": (
                "THESIS_CLOSURE を守れ。"
                "選んだ道=選択の事実＋構造転換（内部蓄積→定義し直し）＋いまの問いへの連結。"
                "『その後いくつかの場を経験』だけの年表は禁止。"
                "今に残った構造=一制度の物差しと現在の生活の緊張が問いを残すこと。"
                "これからの再分岐=役職・年収だけを唯一指標にせず、何を長期の蓄積と見なすかを自分で選ぶ余地。"
                "考えていく、だけで終わらせるな。静かな現在向きの結論にせよ。"
                "evidence は各節1点まで。観測/Protocol/文章制作の列挙禁止。"
                "LOCKED_LABELS をすべて ## で書け。subtitle 空。paragraph_support 必須。"
            ),
        },
        ensure_ascii=False,
    )


def call2_system_prompt_v117() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V117

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V117}

Call2WritingPack を使う。Re-branch は問いではなく現在の選択で閉じる。

必須:
- locked_public_labels を ## 見出しとしてこの順。改名・省略禁止
- ReBranchDecision を実現: present_choice + what_is_no_longer_required + Residue 接続
- これからの再分岐は静かな結論。問いだけ／反省だけ／「すべき」「今こそ」「挑戦」「成長」禁止
- 深さは新事実ではなく、Lost/Protected/Residue/Re-branch で含意を一段深める一文
- 「蓄積」「構造」「尺度」「制度」の連打を避け、具体語や日常語へ分散
- 複数業界・観測/Protocol/文章制作のカタログ禁止。現在の生活は一点まで
- subtitle_candidates は空

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"re_branch", "public_heading":"これからの再分岐", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_user_prompt_v117(writing_pack: dict[str, Any]) -> str:
    return json.dumps(
        {
            "CALL2_WRITING_PACK": writing_pack,
            "REBRANCH_DECISION": writing_pack.get("rebranch_decision") or {},
            "THESIS_CLOSURE": writing_pack.get("thesis_closure") or {},
            "LOCKED_LABELS": writing_pack.get("locked_public_labels_in_order") or [],
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "employer_industry_project_enumeration",
                "project_catalogue",
                "lens_name_advertising",
                "shiro_protocol_app_promo",
                "productivity_career_coaching",
                "question_only_rebranch",
                "growth_challenge_rhetoric",
                "renamed_section_headings",
                "omitted_required_sections",
            ],
            "instruction": (
                "REBRANCH_DECISION を本文で実現せよ。問いだけで終えるな。"
                "これからの再分岐=(A)いま選び直せる余地 (B)役職・年収だけを唯一指標にしなくてよい "
                "(C)Residueの緊張への接続。静かな結論。助言口調禁止。"
                "選んだ道は年表に落とすな。現在生活の例は一点まで。"
                "抽象語（蓄積・構造・尺度・制度）を隣接で連打しない。"
                "Lost/Protected/Residue/Re-branch は含意を一段深めてよいが、新事実は足すな。"
                "LOCKED_LABELS をすべて ## で。subtitle 空。paragraph_support 必須。"
            ),
        },
        ensure_ascii=False,
    )


def call2_system_prompt_v118() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V118

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V118}

Call2WritingPack + BranchSemantics を使う。ドメインはヒントであり、キャリア定型文を強制しない。

必須:
- locked_public_labels を ## 見出しとしてこの順。改名・省略禁止
- Lost/Protected/Residue/Re-branch は BranchSemantics / ReBranchDecision の意味を実現
- Re-branch は問いではなく現在の選択／非選択で閉じる（modes: choose/preserve/reconsider/revisit/leave_unresolved/not_act/observe/redefine）
- 家族・恋愛・健康・創作に「役職や年収」「仕事を定義し直す」を持ち込まない（証拠があるキャリア分岐のみ可）
- これからの再分岐は静かな結論。助言口調／成長修辞禁止
- 抽象語の連打を避け、具体語や日常語へ分散
- subtitle_candidates は空

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"re_branch", "public_heading":"これからの再分岐", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_system_prompt_v119() -> str:
    from app.parallel_life_deep_reading.section_contracts import CALL_2_PROMPT_VERSION_V119

    return f"""あなたは Parallel Life Deep Reading の原稿執筆者です。
プロンプト版: {CALL_2_PROMPT_VERSION_V119}

Call2WritingPack + BranchSemantics を権威ある意味の源泉として使う。
Context Pack の職歴は背景証拠であり、非キャリア分岐の意味領域を書き換えない。

必須:
- locked_public_labels を ## 見出しとしてこの順。改名・省略禁止
- Lost/Protected/Residue/Re-branch / Chosen Path は BranchSemantics に従う
- 教育・創作・家族・恋愛・健康で「所属が変わるたびに自分の仕事を定義し直す」「役職や年収」「持ち運ぶ蓄積」を使わない
- 背景の仕事事実は、分岐の意味に関連するときだけ並べて読む（キャリア定型へ変換しない）
- Re-branch は問いではなく現在の選択／非選択で閉じる
- これからの再分岐は静かな結論。助言口調／成長修辞禁止
- subtitle_candidates は空

JSON のみ:
{{
  "body_markdown": "...",
  "title_candidates": ["...", "...", "..."],
  "subtitle_candidates": [],
  "sections": [{{"internal_id":"re_branch", "public_heading":"これからの再分岐", "included": true}}],
  "paragraph_support": [
    {{"paragraph_id":"p01", "support_ids":["..."], "contains_inference": false}}
  ],
  "rebranch_candidates": [],
  "rebranch_omitted_reason": null,
  "diagnostics": {{}}
}}
"""


def call2_user_prompt_v119(writing_pack: dict[str, Any]) -> str:
    return call2_user_prompt_v118(writing_pack)


def call2_user_prompt_v118(writing_pack: dict[str, Any]) -> str:
    return json.dumps(
        {
            "CALL2_WRITING_PACK": writing_pack,
            "BRANCH_SEMANTICS": writing_pack.get("branch_semantics") or {},
            "REBRANCH_DECISION": writing_pack.get("rebranch_decision") or {},
            "THESIS_CLOSURE": writing_pack.get("thesis_closure") or {},
            "LOCKED_LABELS": writing_pack.get("locked_public_labels_in_order") or [],
            "DO_NOT_INVENT": [
                "dates_not_supplied",
                "unsupported_causality",
                "employer_industry_project_enumeration",
                "project_catalogue",
                "lens_name_advertising",
                "shiro_protocol_app_promo",
                "productivity_career_coaching",
                "career_template_on_non_career_branch",
                "question_only_rebranch",
                "growth_challenge_rhetoric",
                "renamed_section_headings",
                "omitted_required_sections",
            ],
            "instruction": (
                "BRANCH_SEMANTICS と REBRANCH_DECISION を本文で実現せよ。"
                "キャリア定型（役職・年収・仕事の定義し直し・持ち運ぶ蓄積）は、"
                "domain が career/entrepreneurship で証拠があるときだけ。"
                "Lost=確かめられなくなったこと。Protected=残った可能性。"
                "Residue=いまの問いに残る古い分岐。Re-branch=静かな現在の選択／非選択。"
                "選んだ道は年表に落とすな。新事実は足すな。"
                "LOCKED_LABELS をすべて ## で。subtitle 空。paragraph_support 必須。"
            ),
        },
        ensure_ascii=False,
    )


def call3_editorial_naturalness_user_prompt(
    body: str,
    title: str,
    *,
    rebranch_decision: dict[str, Any] | None = None,
    abstract_density: dict[str, Any] | None = None,
    prior_issues: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "task": "editorial_naturalness_pass",
            "editorial_objective": (
                "Preserve all validated meaning and evidence, "
                "but rewrite explanatory / schema-like prose "
                "into natural edited Japanese nonfiction."
            ),
            "hard_constraints": [
                "do_not_change_claims",
                "do_not_add_biography",
                "do_not_remove_required_sections",
                "do_not_loosen_title_or_gates",
                "rebranch_must_remain_a_present_choice_not_a_question",
                "no_coaching_rhetoric",
            ],
            "REBRANCH_DECISION": rebranch_decision or {},
            "ABSTRACT_VOCAB_DENSITY": abstract_density or {},
            "prior_runtime_issues": prior_issues or [],
            "current_title": title,
            "body_markdown": body,
            "instruction": (
                "意味と根拠は保ち、説明調・スキーマ臭い文を編集された日本語ノンフィクションへ。"
                "これからの再分岐が問い／反省だけで終わっていれば、"
                "REBRANCH_DECISION の present_choice と what_is_no_longer_required を静かに実現せよ。"
                "抽象語が excess なら、意味を変えず日常語へ分散。"
                "観測/Protocol/文章制作・複数業界のカタログは一点の現在例へ圧縮。"
                "新しい伝記を足さない。JSONのみ。"
            ),
            "response_shape": {
                "final_title": "...",
                "final_subtitle": "",
                "body_markdown": "...",
                "diagnostics": {"editorial_changes": []},
            },
        },
        ensure_ascii=False,
    )


def call3_system_prompt() -> str:
    return f"""あなたは Parallel Life Deep Reading の全文編集者・検証者です。
プロンプト版: {CALL_3_VERSION}

優先順位:
1. 事実忠実度
2. semantic overreach の除去（文脈ごと書き直し）:
   unsupported_personal_detail / unsupported_scene /
   unsupported_causality / unsupported_causal_frame /
   unsupported_affect / unsupported_role_behavior / schema_leakage_prose
3. 中心テーゼと Residue の保持
4. 最終言語パス: システム臭い・分析臭い足場を、新しい内容を足さずに除去
5. 自然な日本語と連続性

重要な禁止:
- 因果断言を因果の問いに言い換えない
  悪い: 「影響している」→「どのように影響しているのか」
  良い: 「並べて見る」／「直接結びつける材料はない」
- スキーマ漏洩（この選択は、実際に選んだのは…）を直接叙述へ直す
- タイトルに未根拠の影響・原点・きっかけ・形成を使わない

最終言語パスの点検:
schema leakage / メタ説明 / 因果語の反復 / 不自然な主語反復 /
「〜は、〜のは」構文 / 冗長な「実際に」 / 「〜という」の反復 / レポート調接続

JSON のみ:
{{
  "final_title": "...",
  "final_subtitle": "...",
  "body_markdown": "...",
  "diagnostics": {{
    "unsupported_causal_frame_removed": [],
    "schema_leakage_removed": [],
    "unsupported_causality_removed": [],
    "notes": []
  }}
}}"""


def call3_user_prompt(
    call1_json: dict[str, Any],
    draft_json: dict[str, Any],
    prior_issues: list[str],
    evidence_ledger: dict[str, Any] | None = None,
) -> str:
    return json.dumps(
        {
            "priority": [
                "factual_fidelity",
                "semantic_overreach_rewrite",
                "remove_causal_frame_and_schema_leakage",
                "final_language_pass",
                "preserve_thesis_and_residue",
            ],
            "ALLOWED_PERSONAL_EVIDENCE": evidence_ledger or {},
            "confirmed_structure": call1_json,
            "draft": draft_json,
            "prior_runtime_issues": prior_issues,
            "instruction": (
                "全文を編集する。因果フレームの問いは並置・比較・材料不足の明示へ。"
                "『この選択は、実際に選んだのは』系は直接叙述へ。"
                "新しい伝記・感情・役割を足さない。Residue と present anchor を保つ。"
                "タイトルに未根拠の『影響』を使わない。"
            ),
        },
        ensure_ascii=False,
    )


def call3_language_pass_user_prompt(
    body: str,
    title: str,
    prior_issues: list[str],
) -> str:
    return json.dumps(
        {
            "task": "final_language_pass",
            "instruction": (
                "事実内容は変えず、システム臭い足場だけを直す。"
                "schema leakage・『〜は、〜のは』・冗長な『実際に』・因果フレーム問いを除去。"
                "新しい内容を追加しない。JSON のみ返す。"
            ),
            "prior_runtime_issues": prior_issues,
            "current_title": title,
            "body_markdown": body,
            "response_shape": {
                "final_title": "...",
                "final_subtitle": "...",
                "body_markdown": "...",
            },
        },
        ensure_ascii=False,
    )
