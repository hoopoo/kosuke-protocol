"""Editorial Edition as a single book-style essay generation.

Standard mode keeps the structured heuristic/LLM pipeline.
Editorial Edition is publishing: one fact lock, one full-draft generation,
fact-only validation, and at most one model revision pass.

Destructive string post-processing (raw-reuse strip, sentence chopping) is
intentionally NOT applied here — those produced artifacts such as 「不。」.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from app.models import (
    EditorialBranchStructure,
    EditorialContext,
    ObservatoryLayer,
    ParallelLifeEditorialRequest,
    ParallelLifeEditorialResponse,
    ParallelLifeResult,
)
from app.observatory_lenses import OBSERVATORY_LENSES, validate_lens_ids
from app.parallel_life_domain import (
    GroundedPrimaryBranch,
    domain_consistency_issues,
    extract_grounded_primary_branch,
)
from app.parallel_life_editorial_normalize import normalize_editorial_context
from app.parallel_life_facts import (
    extract_parallel_life_facts,
    facts_prompt_block,
    validate_factual_consistency,
)

_CJK_RE = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
_ORPHAN_FRAGMENT_RE = re.compile(
    r"(?:^|[。．\s])([ぁ-んァ-ヶ一-龥A-Za-z]{1,2})[。．](?:\s|$)"
)


class EditorialLLMRequiredError(RuntimeError):
    """Raised when Editorial Edition cannot run without an LLM."""


class EditorialGenerationError(RuntimeError):
    """Raised when Editorial Edition generation or revision fails."""


def _is_ja(language: str, text: str = "") -> bool:
    if language and language.lower().startswith("ja"):
        return True
    return bool(_CJK_RE.search(text))


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def build_editorial_fact_packet(
    request: ParallelLifeEditorialRequest,
    grounded: GroundedPrimaryBranch,
    structure: EditorialBranchStructure,
    *,
    ja: bool,
) -> dict[str, Any]:
    """Stage 1: lock facts only — no prose generation."""
    ctx = request.editorial_context
    clar = request.clarifications
    normalized = normalize_editorial_context(
        request.source_text, clar, ctx, structure, ja=ja
    )
    return {
        "age": grounded.age,
        "primary_event": grounded.primary_event,
        "chosen_path": grounded.chosen_path or clar.chosen_path,
        "unchosen_path": grounded.unchosen_path or clar.unchosen_path,
        "secondary_branches": grounded.secondary_branches or structure.secondary_branches,
        "present_question": grounded.present_question or structure.present_question,
        "primary_domain": grounded.primary_domain,
        "secondary_tags": grounded.secondary_tags,
        "child_polarity": grounded.child_polarity,
        "explicit_entities": grounded.explicit_entities,
        "present_life_facts": normalized.present_life_facts,
        "current_roles": normalized.current_roles,
        "current_conditions": normalized.current_conditions,
        "emotional_observations": normalized.emotional_observations,
        "editorial_answers": {
            k: v
            for k, v in ctx.model_dump().items()
            if isinstance(v, str) and v.strip()
        },
    }


def _result_prose_blob(result: ParallelLifeResult) -> str:
    return " ".join(
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
        ]
    )


def detect_orphan_fragments(result: ParallelLifeResult) -> list[str]:
    """Detect broken leftovers like 「不。」 from prior destructive editors.

    Must not false-positive on normal words such as 「不妊治療」.
    """
    blob = _result_prose_blob(result)
    found: list[str] = []
    # Standalone 1–2 char sentence ending in 。／． (e.g. "不。")
    for m in _ORPHAN_FRAGMENT_RE.finditer(blob):
        frag = m.group(1)
        if frag in ("不", "あ", "い", "う", "え", "お", "ん"):
            found.append(frag + "。")
    # Explicit standalone "不。" (period after 不) — not 「不妊」.
    if re.search(r"(?:^|[。．\s　])不。", blob):
        found.append("不。")
    return list(dict.fromkeys(found))


def fact_validate_editorial(
    result: ParallelLifeResult,
    request: ParallelLifeEditorialRequest,
    grounded: GroundedPrimaryBranch,
    *,
    ja: bool,
) -> list[str]:
    """Stage 3: validate facts only — do not police literary style."""
    issues: list[str] = []
    facts = extract_parallel_life_facts(
        request.source_text, request.clarifications, ja=ja
    )
    try:
        validate_factual_consistency(request.source_text, result, facts, ja=ja)
    except ValueError as exc:
        issues.append(f"factual_consistency:{exc}")

    issues.extend(domain_consistency_issues(result, grounded, ja=ja))

    orphans = detect_orphan_fragments(result)
    if orphans:
        issues.append("orphan_fragments:" + ",".join(orphans))

    # Structural minimums (not stylistic)
    if not result.title.strip():
        issues.append("empty_title")
    if not result.branch_point.strip() or not result.closing.strip():
        issues.append("empty_required_section")
    if not (2 <= len(result.observatory_layers) <= 4):
        issues.append("observatory_layer_count")
    if not (2 <= len(result.lost) <= 8):
        issues.append("lost_count")
    if not (2 <= len(result.protected) <= 8):
        issues.append("protected_count")
    if not (2 <= len(result.rebranch) <= 8):
        issues.append("rebranch_count")

    if grounded.child_polarity == "had_child":
        blob = _result_prose_blob(result)
        if ja and any(k in blob for k in ("子どもを持たなかった", "授からなかった", "産まれなかった")):
            if "二人目" not in blob:  # allow counterfactual about second child
                issues.append("inverted_had_child")

    return issues


def _book_system_prompt(fact_packet: dict[str, Any], facts_block: str, *, ja: bool) -> str:
    valid_ids = ", ".join(OBSERVATORY_LENSES.keys())
    packet = json.dumps(fact_packet, ensure_ascii=False, indent=2)
    if ja:
        return f"""あなたは Parallel Life Protocol の編集者です。
book.shiroand.io/parallel-life の編集版と同じく、人生の分岐を一篇の編集原稿として書いてください。

目的：
過去の選択を裁くのではなく、その分岐が今の自分に何を残したのかを読み直す。
個人の分岐を、必要なときだけ社会観測レイヤーと照合する。

【固定事実 — これだけが真実。文章を書くとき反転・置換してはならない】
{facts_block}
{packet}

出力は JSON のみ。Title から結びまでを、セクション別の部品ではなく一篇の流れとして書く。
各フィールドは文書の章に対応するが、読者には一つの原稿として響くように書く。

出力スキーマ:
{{
  "title": str,
  "subtitle": str,
  "branch_point": str,
  "chosen_path": str,
  "unchosen_life": str,
  "lost": [str, ...],
  "protected": [str, ...],
  "residue": str,
  "observatory_layers": [{{"id": str, "body": str}}, ...],
  "cross_lens_synthesis": str,
  "rebranch": [str, ...],
  "closing": str
}}

編集方針:
- 後悔を煽らない。「本当はこっちが正解だった」と断定しない
- Lost と Protected は異なる論理で書く
- Observatory Layer は 3〜4（ID: {valid_ids}）。title は不要（公式英語名はサーバ側で付与）
- 先に人生を読み、その結果として必要な Lens が現れるように書く（Lens 説明の羅列にしない）
- 最後は必ず現在の生活へ戻る
- primary_domain が family-formation のとき、主題を創作・執筆へ置き換えない
- ユーザー原文をコピーしない。事実を意味へ変換する
- 医療・心理療法・法律の代替にしない
- すべて日本語
- 「可能性」「構造」などの語をコード都合で避けない。自然な編集日本語で書く
"""
    return f"""You are the editor for Parallel Life Protocol Editorial Edition.
Write one continuous personal essay in the Parallel Life document form.

LOCKED FACTS — do not invert or replace:
{facts_block}
{packet}

Return JSON only with keys:
title, subtitle, branch_point, chosen_path, unchosen_life, lost, protected,
residue, observatory_layers (id+body, 3-4 from: {valid_ids}),
cross_lens_synthesis, rebranch, closing.

Rules:
- Do not judge the past or claim the other life was correct
- Lost and Protected use different logics
- Lenses emerge from the life reading
- End in the present life
- Do not replace family-formation with creativity
- English only
"""


def _parse_essay_json(content: str) -> dict[str, Any]:
    text = (content or "").strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    # Tolerate leading/trailing prose around JSON
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _result_from_essay_data(
    data: dict[str, Any],
    *,
    ja: bool,
) -> ParallelLifeResult:
    from app.parallel_life_engine import (
        _is_valid_english_title,
        _is_valid_japanese_title,
    )

    lost = [_clean_line(x) for x in data.get("lost", []) if str(x).strip()]
    protected = [_clean_line(x) for x in data.get("protected", []) if str(x).strip()]
    rebranch = [_clean_line(x) for x in data.get("rebranch", []) if str(x).strip()]

    raw_layers = data.get("observatory_layers") or []
    layer_ids = validate_lens_ids([str(item.get("id", "")) for item in raw_layers])
    if not (2 <= len(layer_ids) <= 4):
        raise EditorialGenerationError("observatory_layers count invalid")

    layers: list[ObservatoryLayer] = []
    for item in raw_layers:
        lid = str(item.get("id", ""))
        if lid not in layer_ids:
            continue
        lens_def = OBSERVATORY_LENSES[lid]
        body = _clean_line(str(item.get("body", "")))
        if not body:
            continue
        layers.append(
            ObservatoryLayer(
                id=lid,
                title=lens_def.name_en,
                descriptor=lens_def.descriptor_ja if ja else lens_def.descriptor_en,
                body=body,
            )
        )
    if not (2 <= len(layers) <= 4):
        raise EditorialGenerationError("observatory_layers empty after parse")

    title = _clean_line(str(data.get("title", "")))
    if not (_is_valid_japanese_title(title) if ja else _is_valid_english_title(title)):
        # Soft: keep title if non-empty; revision pass can fix
        if not title:
            raise EditorialGenerationError("empty title")

    return ParallelLifeResult(
        title=title,
        subtitle=_clean_line(str(data.get("subtitle", ""))),
        branch_point=_clean_line(str(data.get("branch_point", ""))),
        chosen_path=_clean_line(str(data.get("chosen_path", ""))),
        unchosen_life=_clean_line(str(data.get("unchosen_life", ""))),
        lost=lost[:8] or ["（未記入）"] if ja else ["(unspecified)"],
        protected=protected[:8] or ["（未記入）"] if ja else ["(unspecified)"],
        residue=_clean_line(str(data.get("residue", ""))),
        observatory_layers=layers,
        cross_lens_synthesis=_clean_line(str(data.get("cross_lens_synthesis", ""))),
        rebranch=rebranch[:8] or ["（未記入）"] if ja else ["(unspecified)"],
        closing=_clean_line(str(data.get("closing", ""))),
        generation_mode="llm",
        language="ja" if ja else "en",
        depth="editorial",
    )


def _chat_json(api_key: str, system: str, user: str, *, max_tokens: int = 4500) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    return _parse_essay_json(response.choices[0].message.content or "")


async def _generate_essay(
    request: ParallelLifeEditorialRequest,
    fact_packet: dict[str, Any],
    api_key: str,
    *,
    ja: bool,
) -> ParallelLifeResult:
    facts = extract_parallel_life_facts(
        request.source_text, request.clarifications, ja=ja
    )
    facts_block = facts_prompt_block(facts, ja=ja)
    system = _book_system_prompt(fact_packet, facts_block, ja=ja)
    if ja:
        user = (
            "以下の分岐について、Parallel Life Protocol の編集版として一篇を書いてください。\n\n"
            f"元の記述（事実の出所。文章としてコピーしない）:\n{request.source_text}\n\n"
            "Title から結びまでを、一つの原稿として JSON で返してください。"
        )
    else:
        user = (
            "Write the Editorial Edition as one continuous essay in JSON.\n\n"
            f"Source (facts only — do not copy wording):\n{request.source_text}"
        )
    data = _chat_json(api_key, system, user)
    return _result_from_essay_data(data, ja=ja)


async def _revise_essay(
    request: ParallelLifeEditorialRequest,
    draft: ParallelLifeResult,
    fact_packet: dict[str, Any],
    issues: list[str],
    api_key: str,
    *,
    ja: bool,
) -> ParallelLifeResult:
    """Stage 4: ask the model to re-edit the full draft — never string-chop."""
    draft_json = {
        "title": draft.title,
        "subtitle": draft.subtitle,
        "branch_point": draft.branch_point,
        "chosen_path": draft.chosen_path,
        "unchosen_life": draft.unchosen_life,
        "lost": draft.lost,
        "protected": draft.protected,
        "residue": draft.residue,
        "observatory_layers": [
            {"id": layer.id, "body": layer.body} for layer in draft.observatory_layers
        ],
        "cross_lens_synthesis": draft.cross_lens_synthesis,
        "rebranch": draft.rebranch,
        "closing": draft.closing,
    }
    if ja:
        system = """あなたは編集者です。下書きを全文再編集してください。
文字列の部分削除はしない。必ず完成した JSON 全文を返す。
固定事実は変えない。重複、タイプミス、不自然な切れ端（例:「不。」）、主題逸脱を直す。"""
        user = (
            f"固定事実:\n{json.dumps(fact_packet, ensure_ascii=False)}\n\n"
            f"検証で見つかった問題:\n{json.dumps(issues, ensure_ascii=False)}\n\n"
            f"下書き JSON:\n{json.dumps(draft_json, ensure_ascii=False)}\n\n"
            "事実を保ったまま、一篇として再編集した JSON を返してください。"
        )
    else:
        system = (
            "You are an editor. Revise the full draft as complete JSON. "
            "Do not delete substrings; rewrite. Keep locked facts."
        )
        user = (
            f"Locked facts:\n{json.dumps(fact_packet)}\n\n"
            f"Issues:\n{json.dumps(issues)}\n\n"
            f"Draft:\n{json.dumps(draft_json)}\n\n"
            "Return revised JSON."
        )
    data = _chat_json(api_key, system, user, max_tokens=4500)
    return _result_from_essay_data(data, ja=ja)


async def generate_editorial_essay(
    request: ParallelLifeEditorialRequest,
) -> ParallelLifeEditorialResponse:
    """Editorial Edition pipeline: facts → essay → fact-validate → optional revise."""
    # Lazy import avoids circular import with parallel_life_editorial.
    from app.parallel_life_editorial import extract_editorial_branch_structure

    ja = _is_ja(request.language, request.source_text)
    grounded = extract_grounded_primary_branch(
        request.source_text,
        request.clarifications,
        request.editorial_context,
        ja=ja,
    )
    structure = extract_editorial_branch_structure(
        request.source_text,
        request.clarifications,
        request.editorial_context,
        ja=ja,
    )
    structure = structure.model_copy(
        update={
            "primary_branch": (
                grounded.primary_event
                if grounded.primary_domain == "family-formation"
                else structure.primary_branch
            ),
            "secondary_branches": grounded.secondary_branches or structure.secondary_branches,
            "present_question": grounded.present_question or structure.present_question,
            "inferred_themes": grounded.inferred_themes,
            "current_life_context": [],  # filled from fact packet after normalize
        }
    )
    fact_packet = build_editorial_fact_packet(request, grounded, structure, ja=ja)
    structure = structure.model_copy(
        update={"current_life_context": list(fact_packet.get("present_life_facts") or [])[:6]}
    )

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise EditorialLLMRequiredError(
            "編集版には LLM が必要です。OPENAI_API_KEY を設定してから、もう一度お試しください。"
            if ja
            else "The Editorial Edition requires an LLM. Set OPENAI_API_KEY and try again."
        )

    try:
        result = await _generate_essay(request, fact_packet, api_key, ja=ja)
    except Exception as exc:
        raise EditorialGenerationError(
            "編集版を生成できませんでした。入力は保存されています。もう一度お試しください。"
            if ja
            else "The Editorial Edition could not be generated. Your input was preserved. Please try again."
        ) from exc

    issues = fact_validate_editorial(result, request, grounded, ja=ja)
    if issues:
        try:
            result = await _revise_essay(
                request, result, fact_packet, issues, api_key, ja=ja
            )
        except Exception as exc:
            raise EditorialGenerationError(
                "編集版の再編集に失敗しました。もう一度お試しください。"
                if ja
                else "Editorial revision failed. Please try again."
            ) from exc
        issues2 = fact_validate_editorial(result, request, grounded, ja=ja)
        if issues2:
            raise EditorialGenerationError(
                "編集版を事実を保ったまま完成できませんでした。もう一度お試しください。"
                if ja
                else "The Editorial Edition could not be completed while preserving facts. Please try again."
            )

    return ParallelLifeEditorialResponse(branch_structure=structure, result=result)


__all__ = [
    "EditorialGenerationError",
    "EditorialLLMRequiredError",
    "build_editorial_fact_packet",
    "detect_orphan_fragments",
    "fact_validate_editorial",
    "generate_editorial_essay",
]
