"""OpenAI JSON helper for Deep Reading. No heuristic long-form fallback."""

from __future__ import annotations

import json
import os
from typing import Any


class DeepReadingLLMRequiredError(RuntimeError):
    """Raised when Deep Reading cannot run without an LLM."""


class DeepReadingGenerationError(RuntimeError):
    """Raised when a Deep Reading LLM call fails (retriable)."""


def parse_json_content(content: str) -> dict[str, Any]:
    text = (content or "").strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def require_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise DeepReadingLLMRequiredError(
            "Deep Reading には LLM が必要です。OPENAI_API_KEY を設定してから再試行してください。"
        )
    return key


def _uses_max_completion_tokens(model: str) -> bool:
    m = (model or "").lower()
    return m.startswith("gpt-5") or "terra" in m or "sol" in m or "luna" in m


def chat_json(
    system: str,
    user: str,
    *,
    max_tokens: int = 6000,
    temperature: float = 0.4,
    response_format: dict[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Synchronous chat completion returning parsed JSON.

    Deep Reading must not fabricate a template manuscript on failure.
    Prefer response_format JSON Schema structured output when provided.
    """
    api_key = require_api_key()
    resolved_model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": response_format or {"type": "json_object"},
        }
        if _uses_max_completion_tokens(resolved_model):
            kwargs["max_completion_tokens"] = max_tokens
            # GPT-5.6 family rejects custom temperature / max_tokens.
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        return parse_json_content(content)
    except DeepReadingLLMRequiredError:
        raise
    except Exception as exc:
        raise DeepReadingGenerationError(
            "Deep Reading の生成に失敗しました。確認済み構造は保持されています。再試行してください。"
        ) from exc


def chat_json_schema(
    system: str,
    user: str,
    response_format: dict[str, Any],
    *,
    max_tokens: int = 6000,
    temperature: float = 0.2,
    model: str | None = None,
) -> dict[str, Any]:
    """Call 1 structured output helper."""
    from app.parallel_life_deep_reading.production_models import CALL_1_MODEL

    return chat_json(
        system,
        user,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format=response_format,
        model=model or CALL_1_MODEL,
    )
