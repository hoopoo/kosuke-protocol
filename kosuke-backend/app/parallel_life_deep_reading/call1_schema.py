"""Call 1 JSON Schema helpers and accessors (canonical models live in models.py)."""

from __future__ import annotations

from typing import Any

from app.parallel_life_deep_reading.models import (
    CALL_1_PROMPT_VERSION,
    CALL_1_SCHEMA_VERSION,
    AdditionalQuestions,
    Call1LLMPayload,
    Call1ParseDiagnostics,
    Call1Response,
    Call1Result,
    EditorialOutline,
    LostStructure,
    ObservatoryLensCandidate,
    ObservatoryLensSelection,
    ProtectedStructure,
    RebranchDesign,
    RebranchDirection,
    RepetitionMapEntry,
    RepetitionPreventionMap,
    ResidueCandidate,
    ResidueCandidates,
    SensitiveDomainAnalysis,
    SourceCoverage,
)


class Call1SchemaError(Exception):
    """Typed Call 1 schema failure — do not proceed to confirmation/Call 2."""

    def __init__(
        self,
        message: str,
        *,
        diagnostics: Call1ParseDiagnostics | None = None,
        partial: Call1Response | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics or Call1ParseDiagnostics()
        self.partial = partial


def _strip_unsupported_schema_keys(node: Any) -> Any:
    if isinstance(node, dict):
        banned = {
            "default",
            "title",
            "description",
            "examples",
            "minimum",
            "maximum",
            "exclusiveMinimum",
            "exclusiveMaximum",
            "minLength",
            "maxLength",
            "pattern",
            "format",
            "minItems",
            "maxItems",
            "uniqueItems",
            "const",
        }
        out: dict[str, Any] = {}
        for k, v in node.items():
            if k in banned:
                continue
            if k == "anyOf":
                variants = [_strip_unsupported_schema_keys(x) for x in v]
                non_null = [
                    x
                    for x in variants
                    if not (isinstance(x, dict) and x.get("type") == "null")
                ]
                if len(non_null) == 1 and isinstance(non_null[0], dict):
                    for nk, nv in non_null[0].items():
                        out[nk] = nv
                    continue
                out[k] = variants
                continue
            out[k] = _strip_unsupported_schema_keys(v)
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"].keys())
        return out
    if isinstance(node, list):
        return [_strip_unsupported_schema_keys(x) for x in node]
    return node


def call1_json_schema() -> dict[str, Any]:
    schema = Call1LLMPayload.model_json_schema()
    cleaned = _strip_unsupported_schema_keys(schema)
    if "$defs" in cleaned:
        cleaned["$defs"] = {
            k: _strip_unsupported_schema_keys(v) for k, v in cleaned["$defs"].items()
        }
    cleaned["additionalProperties"] = False
    if "properties" in cleaned:
        cleaned["required"] = list(cleaned["properties"].keys())
    return cleaned


def openai_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "parallel_life_call1_response",
            "strict": True,
            "schema": call1_json_schema(),
        },
    }


def call1_selected_lenses(call1: Call1Response | Any) -> list[ObservatoryLensCandidate]:
    sel = getattr(call1, "selected_observatory_lenses", None)
    if sel is None:
        return []
    if hasattr(sel, "selected"):
        return list(sel.selected or [])
    if isinstance(sel, list):
        return list(sel)
    return []


def call1_evaluated_lenses(call1: Call1Response | Any) -> list[ObservatoryLensCandidate]:
    sel = getattr(call1, "selected_observatory_lenses", None)
    if sel is None:
        return []
    if hasattr(sel, "evaluated"):
        return list(sel.evaluated or [])
    if isinstance(sel, list):
        return list(sel)
    return []


def call1_rebranch_directions(call1: Call1Response | Any) -> list[RebranchDirection]:
    rb = getattr(call1, "rebranch_design", None)
    if rb is None:
        return []
    if hasattr(rb, "directions"):
        return list(rb.directions or [])
    if isinstance(rb, list):
        return list(rb)
    return []


def call1_residue_items(call1: Call1Response | Any) -> list[ResidueCandidate]:
    rc = getattr(call1, "residue_candidates", None)
    if rc is None:
        return []
    if hasattr(rc, "items"):
        return list(rc.items or [])
    if isinstance(rc, list):
        return list(rc)
    return []


def call1_additional_question_list(call1: Call1Response | Any) -> list[str]:
    aq = getattr(call1, "additional_questions", None)
    if aq is None:
        return []
    if hasattr(aq, "questions"):
        return list(aq.questions or [])
    if isinstance(aq, list):
        return [str(x) for x in aq]
    return []


__all__ = [
    "CALL_1_PROMPT_VERSION",
    "CALL_1_SCHEMA_VERSION",
    "AdditionalQuestions",
    "Call1LLMPayload",
    "Call1ParseDiagnostics",
    "Call1Response",
    "Call1Result",
    "Call1SchemaError",
    "EditorialOutline",
    "LostStructure",
    "ObservatoryLensSelection",
    "ProtectedStructure",
    "RebranchDesign",
    "RepetitionMapEntry",
    "RepetitionPreventionMap",
    "ResidueCandidates",
    "SensitiveDomainAnalysis",
    "SourceCoverage",
    "call1_additional_question_list",
    "call1_evaluated_lenses",
    "call1_json_schema",
    "call1_rebranch_directions",
    "call1_residue_items",
    "call1_selected_lenses",
    "openai_response_format",
]
