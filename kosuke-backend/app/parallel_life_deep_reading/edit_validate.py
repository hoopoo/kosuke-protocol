"""Call 3: whole-document editing and validation (fact-bounded)."""

from __future__ import annotations

from typing import Any

from app.parallel_life_deep_reading.call1_schema import call1_residue_items, call1_selected_lenses
from app.parallel_life_deep_reading.draft import build_evidence_ledger
from app.parallel_life_deep_reading.llm import DeepReadingGenerationError, chat_json
from app.parallel_life_deep_reading.production_models import CALL_3_MODEL
from app.parallel_life_deep_reading.models import (
    Call1Result,
    Call2Draft,
    Call3Result,
    GenerationStatus,
    RebranchDirection,
)
from app.parallel_life_deep_reading.prompts import (
    CALL_3_VERSION,
    call3_editorial_naturalness_user_prompt,
    call3_language_pass_user_prompt,
    call3_system_prompt,
    call3_user_prompt,
)
from app.parallel_life_deep_reading.runtime_validation import (
    finalize_call3_body,
    filter_publishable_rebranch,
    recalculate_publication_gate,
    title_has_unsupported_causal_frame,
    validate_title,
)
from app.parallel_life_deep_reading.v101_gates import repair_unrealized_path_modality


def _pick_title(
    candidates: list[str],
    call1: Call1Result,
    body: str,
    preferred: str = "",
) -> tuple[str, str]:
    ordered = []
    if preferred.strip():
        ordered.append(preferred.strip())
    ordered.extend([c for c in candidates if c.strip()])
    seen: set[str] = set()
    uniq: list[str] = []
    for t in ordered:
        if t not in seen:
            seen.add(t)
            uniq.append(t)

    for title in uniq:
        if title_has_unsupported_causal_frame(title, call1.grounded_input):
            continue
        tv = validate_title(
            title,
            "",
            call1.grounded_input,
            call1.central_thesis.statement,
            body,
        )
        if tv.passed:
            return title, ""
    for title in uniq:
        if title_has_unsupported_causal_frame(title, call1.grounded_input):
            continue
        tv = validate_title(
            title,
            "",
            call1.grounded_input,
            call1.central_thesis.statement,
            body,
        )
        if not tv.title_introduces_new_unverified_theme and not tv.title_causal_frame_violation:
            return title, ""
    # Safe fallbacks without causal-frame tokens.
    for fallback in ("分岐を読み直す", "過去と現在のあいだ", "選択と現在の生活"):
        tv = validate_title(
            fallback,
            "",
            call1.grounded_input,
            call1.central_thesis.statement,
            body,
        )
        if tv.passed or not title_has_unsupported_causal_frame(fallback, call1.grounded_input):
            return fallback, ""
    return "分岐を読み直す", ""


def run_call3_edit_validate(
    call1: Call1Result,
    draft: Call2Draft,
    *,
    max_passes: int = 2,
) -> Call3Result:
    if not call1.grounded_input.confirmed_by_user:
        raise DeepReadingGenerationError(
            "Call 3 rejected: grounded_input.confirmed_by_user must be true."
        )
    if not call1_residue_items(call1):
        raise DeepReadingGenerationError(
            "Call 3 rejected: validated Residue is required."
        )

    body = draft.body_markdown
    fallback_body = draft.body_markdown  # Call2 structured markdown — restore source
    title_candidates = list(draft.title_candidates)
    # v1.1.3-exp: omit résumé-like literary subtitles
    subtitle = ""
    if getattr(call1, "section_contracts", None):
        subtitle = ""
    elif draft.subtitle_candidates:
        subtitle = draft.subtitle_candidates[0]
    rebranch = list(draft.rebranch_candidates)
    if not rebranch:
        from app.parallel_life_deep_reading.call1_schema import call1_rebranch_directions

        rebranch = list(call1_rebranch_directions(call1))
    ledger = build_evidence_ledger(call1)

    prior_issues: list[str] = []
    edited_title = ""
    pv = (getattr(call1, "prompt_version", None) or "")
    schema_v = (getattr(call1, "schema_version", None) or "").strip()
    # Runtime pin decides Call3 contract; Call1 prompt may remain v1.1.9-exp
    is_v1111 = "v1.1.11" in schema_v or "v1.1.11" in pv
    is_v1110 = (not is_v1111) and ("v1.1.10" in schema_v or "v1.1.10" in pv)
    is_v119 = (not is_v1111 and not is_v1110) and "v1.1.9" in pv
    is_v118 = "v1.1.8" in pv
    is_v117 = "v1.1.7" in pv
    # Track A freeze: v1.1.11 keeps locked-label restore / no literary rename pass
    is_track_a_frozen = is_v1111 or is_v1110
    call3_prompt_version = CALL_3_VERSION
    if is_v1111:
        from app.parallel_life_deep_reading.section_contracts import (
            CALL_3_PROMPT_VERSION_V1111,
        )

        call3_prompt_version = CALL_3_PROMPT_VERSION_V1111
    elif is_v1110:
        from app.parallel_life_deep_reading.section_contracts import (
            CALL_3_PROMPT_VERSION_V1110,
        )

        call3_prompt_version = CALL_3_PROMPT_VERSION_V1110
    elif is_v119:
        from app.parallel_life_deep_reading.section_contracts import (
            CALL_3_PROMPT_VERSION_V119,
        )

        call3_prompt_version = CALL_3_PROMPT_VERSION_V119
    elif is_v118:
        from app.parallel_life_deep_reading.section_contracts import (
            CALL_3_PROMPT_VERSION_V118,
        )

        call3_prompt_version = CALL_3_PROMPT_VERSION_V118
    elif is_v117:
        from app.parallel_life_deep_reading.section_contracts import (
            CALL_3_PROMPT_VERSION_V117,
        )

        call3_prompt_version = CALL_3_PROMPT_VERSION_V117

    def _preserve_locked_sections(current: str) -> str:
        section_contracts = getattr(call1, "section_contracts", None)
        if not section_contracts:
            return current
        from app.parallel_life_deep_reading.section_contracts import (
            restore_locked_section_manuscript,
        )

        return restore_locked_section_manuscript(
            current,
            fallback_body=fallback_body,
            contracts=section_contracts,
        )

    # Normalize Call2 headings before edit loop
    body = _preserve_locked_sections(body)
    if is_v1111 or is_track_a_frozen:
        from app.parallel_life_deep_reading.runtime_validation import (
            rewrite_unsupported_causality_phrases,
        )

        body = rewrite_unsupported_causality_phrases(body)

    for pass_i in range(max_passes):
        omit_obs = len(call1_selected_lenses(call1)) == 0
        _, publishable_rb = filter_publishable_rebranch(
            rebranch, grounded=call1.grounded_input
        )
        omit_rb = len(publishable_rb) == 0

        gate = recalculate_publication_gate(
            grounded=call1.grounded_input,
            call1=call1,
            draft=draft,
            body=body,
            title=edited_title or (title_candidates[0] if title_candidates else ""),
            subtitle=subtitle,
            rebranch_candidates=rebranch,
        )
        prior_issues = list(gate.blocking_reasons)
        for label, items in (
            ("unsupported_causality", gate.unsupported_causality),
            ("unsupported_causal_frame", gate.unsupported_causal_frame),
            ("schema_leakage_prose", gate.schema_leakage_prose),
            ("unsupported_affect", gate.unsupported_affect),
            ("unsupported_role_behavior", gate.unsupported_role_behavior),
            ("unsupported_personal_detail", gate.unsupported_personal_details),
            ("unsupported_scene", gate.unsupported_scenes),
        ):
            for item in items:
                excerpt = getattr(item, "excerpt", "") or ""
                if excerpt:
                    prior_issues.append(f"{label}: {excerpt[:120]}")

        needs_model = (
            gate.unsupported_scenes
            or gate.unsupported_personal_details
            or gate.unsupported_causality
            or gate.unsupported_causal_frame
            or gate.schema_leakage_prose
            or gate.unrealized_path_modality_violations
            or gate.unsupported_affect
            or gate.unsupported_role_behavior
            or gate.generic_advice_findings
            or not gate.title_validation.passed
            or gate.title_validation.title_causal_frame_violation
            or not gate.residue_centrality
            or "unpublished_rebranch_in_body" in gate.blocking_reasons
            or gate.unsupported_paragraphs
        ) and pass_i < max_passes

        if needs_model:
            # Model rewrites semantic overreach in context before deterministic strip.
            draft_json = {
                "body_markdown": body,
                "title_candidates": title_candidates,
                "subtitle_candidates": draft.subtitle_candidates,
                "paragraph_support": [
                    p.model_dump(mode="json") for p in draft.paragraph_support
                ],
                "rebranch_candidates": [r.model_dump(mode="json") for r in publishable_rb],
            }
            data = chat_json(
                call3_system_prompt(),
                call3_user_prompt(
                    call1.model_dump(mode="json"),
                    draft_json,
                    prior_issues,
                    evidence_ledger=ledger,
                ),
                max_tokens=7000,
                temperature=0.3,
                model=CALL_3_MODEL,
            )
            body = str(data.get("body_markdown") or body).strip() + "\n"
            body = _preserve_locked_sections(body)
            edited_title = str(data.get("final_title") or edited_title)
            subtitle = str(data.get("final_subtitle") or subtitle)
            if isinstance(data.get("rebranch_candidates"), list):
                rebranch = [
                    RebranchDirection(**x)
                    if isinstance(x, dict)
                    else x
                    for x in data["rebranch_candidates"]
                    if isinstance(x, dict)
                ]

        title, _ = _pick_title(title_candidates, call1, body, preferred=edited_title)
        edited_title = title

        # Section-contract paths: compress résumé + ensure Re-branch decision + naturalness
        section_contracts = getattr(call1, "section_contracts", None)
        if section_contracts:
            from app.parallel_life_deep_reading.section_contracts import (
                abstract_vocabulary_density,
                apply_editorial_naturalness_pass,
                compress_resume_body,
                ensure_rebranch_decision_in_body,
                section_resume_flags,
            )

            flags = section_resume_flags(f"{edited_title}\n{subtitle}\n{body}")
            if (
                flags.get("compression_required")
                or flags.get("resume_density", 0) > 3
                or is_v117
                or is_v118
            ):
                body = compress_resume_body(body)
                subtitle = ""
            body = ensure_rebranch_decision_in_body(body, section_contracts)
            body = _preserve_locked_sections(body)
            dens = abstract_vocabulary_density(body)
            # Track A freeze (v1.1.10+): do NOT run literary naturalness LLM that
            # rewrites headings. Keep v1.1.7/1.1.8 naturalness only for those pins.
            if (is_v117 or is_v118) and not is_track_a_frozen and pass_i == 0:
                # Explicit editorial naturalness objective (claims preserved)
                re_dec = {}
                if isinstance(section_contracts, dict):
                    re_dec = (section_contracts.get("diagnostics") or {}).get(
                        "rebranch_decision"
                    ) or {}
                    for c in section_contracts.get("contracts") or []:
                        if c.get("section_id") == "re_branch" and c.get("rebranch_decision"):
                            re_dec = c.get("rebranch_decision") or re_dec
                editorial = chat_json(
                    call3_system_prompt(),
                    call3_editorial_naturalness_user_prompt(
                        body,
                        edited_title,
                        rebranch_decision=re_dec,
                        abstract_density=dens,
                        prior_issues=list(prior_issues),
                    ),
                    max_tokens=7000,
                    temperature=0.25,
                    model=CALL_3_MODEL,
                )
                body = str(editorial.get("body_markdown") or body).strip() + "\n"
                if editorial.get("final_title"):
                    edited_title = str(editorial.get("final_title"))
                body = apply_editorial_naturalness_pass(body)
                body = ensure_rebranch_decision_in_body(body, section_contracts)
                body = _preserve_locked_sections(body)

        gate = recalculate_publication_gate(
            grounded=call1.grounded_input,
            call1=call1,
            draft=draft,
            body=body,
            title=edited_title,
            subtitle=subtitle,
            rebranch_candidates=rebranch,
        )
        # Safety net: strip remaining unsupported excerpts after model rewrite.
        body = finalize_call3_body(
            body,
            gate,
            omit_observatory=omit_obs,
            omit_rebranch=len(filter_publishable_rebranch(
                rebranch, grounded=call1.grounded_input
            )[1])
            == 0,
        )
        body = _preserve_locked_sections(body)
        if gate.unrealized_path_modality_violations:
            body = repair_unrealized_path_modality(body, call1)
            body = _preserve_locked_sections(body)
        gate = recalculate_publication_gate(
            grounded=call1.grounded_input,
            call1=call1,
            draft=draft,
            body=body,
            title=edited_title,
            subtitle=subtitle,
            rebranch_candidates=rebranch,
        )

        # Final language pass: remove system-like scaffolding without adding content.
        language_needed = (
            gate.schema_leakage_prose
            or gate.unsupported_causal_frame
            or gate.unrealized_path_modality_violations
            or gate.title_validation.title_causal_frame_violation
            or any(
                x in (body or "")
                for x in ("実際に選んだのは", "この選択は、実際", "影響を与えているのか")
            )
        )
        if language_needed and pass_i < max_passes:
            lang = chat_json(
                call3_system_prompt(),
                call3_language_pass_user_prompt(
                    body,
                    edited_title,
                    list(gate.blocking_reasons)
                    + [f"schema_leakage_prose: {s.excerpt[:100]}" for s in gate.schema_leakage_prose]
                    + [
                        f"unsupported_causal_frame: {f.excerpt[:100]}"
                        for f in gate.unsupported_causal_frame
                    ],
                ),
                max_tokens=7000,
                temperature=0.2,
                model=CALL_3_MODEL,
            )
            body = str(lang.get("body_markdown") or body).strip() + "\n"
            body = _preserve_locked_sections(body)
            if lang.get("final_title"):
                edited_title = str(lang.get("final_title"))
            if lang.get("final_subtitle"):
                subtitle = str(lang.get("final_subtitle"))
            title, _ = _pick_title(title_candidates, call1, body, preferred=edited_title)
            edited_title = title
            gate = recalculate_publication_gate(
                grounded=call1.grounded_input,
                call1=call1,
                draft=draft,
                body=body,
                title=edited_title,
                subtitle=subtitle,
                rebranch_candidates=rebranch,
            )
            body = finalize_call3_body(
                body,
                gate,
                omit_observatory=omit_obs,
                omit_rebranch=len(
                    filter_publishable_rebranch(
                        rebranch, grounded=call1.grounded_input
                    )[1]
                )
                == 0,
            )
            body = _preserve_locked_sections(body)
            gate = recalculate_publication_gate(
                grounded=call1.grounded_input,
                call1=call1,
                draft=draft,
                body=body,
                title=edited_title,
                subtitle=subtitle,
                rebranch_candidates=rebranch,
            )

        if gate.publishable:
            return Call3Result(
                status=GenerationStatus.complete,
                final_title=edited_title,
                final_subtitle=subtitle,
                body_markdown=body,
                validation=gate,
                prompt_version=call3_prompt_version,
                character_count=len(body),
            )

    title, _ = _pick_title(title_candidates, call1, body, preferred=edited_title)
    gate = recalculate_publication_gate(
        grounded=call1.grounded_input,
        call1=call1,
        draft=draft,
        body=body,
        title=title,
        subtitle=subtitle,
        rebranch_candidates=rebranch,
    )
    return Call3Result(
        status=GenerationStatus.validation_failed
        if not gate.publishable
        else GenerationStatus.complete,
        final_title=title,
        final_subtitle=subtitle,
        body_markdown=body,
        validation=gate,
        prompt_version=call3_prompt_version,
        character_count=len(body),
    )


def export_markdown(
    call3: Call3Result,
    *,
    metadata: dict[str, Any] | None = None,
    include_diagnostics: bool = False,
) -> str:
    lines = [f"# {call3.final_title}", ""]
    if call3.final_subtitle.strip():
        lines.extend([f"*{call3.final_subtitle.strip()}*", ""])
    lines.append(call3.body_markdown.strip())
    lines.append("")
    if metadata:
        lines.append("---")
        lines.append("")
        for key, value in metadata.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    if include_diagnostics:
        lines.append("<!-- diagnostics")
        lines.append(str(call3.validation.model_dump(mode="json")))
        lines.append("-->")
    return "\n".join(lines).rstrip() + "\n"
