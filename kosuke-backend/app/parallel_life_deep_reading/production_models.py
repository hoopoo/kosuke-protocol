"""Explicit production model split for Parallel Life Deep Reading.

Versioned separately from prompts and runtime validation.

Frozen in Parallel Life Deep Reading Production v1.0
(`PRODUCTION_MANIFEST.json`). Do not silently change frozen production
model IDs; bump to v1.0.x or v1.1 instead.
"""

from __future__ import annotations

import os
from typing import Any

PRODUCTION_MODELS_VERSION = "parallel-life-production-models-v1.0"

# Call 1 keeps the existing stable default (env override for infra only).
CALL_1_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
CALL_2_MODEL = "gpt-5.6-terra"
CALL_3_MODEL = "gpt-5.6-terra"

PRODUCTION_MODELS = {
    "version": PRODUCTION_MODELS_VERSION,
    "call_1": CALL_1_MODEL,
    "call_2": CALL_2_MODEL,
    "call_3": CALL_3_MODEL,
}


def model_for_call(call: str) -> str:
    mapping = {
        "call_1": CALL_1_MODEL,
        "call_2": CALL_2_MODEL,
        "call_3": CALL_3_MODEL,
    }
    if call not in mapping:
        raise ValueError(f"unknown call key: {call}")
    return mapping[call]


def production_model_metadata() -> dict[str, Any]:
    return {
        "production_models_version": PRODUCTION_MODELS_VERSION,
        "call_1_model": CALL_1_MODEL,
        "call_2_model": CALL_2_MODEL,
        "call_3_model": CALL_3_MODEL,
        "models": dict(PRODUCTION_MODELS),
    }
