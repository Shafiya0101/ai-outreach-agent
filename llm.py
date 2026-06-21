"""
One thin wrapper around the LLM. We use Mistral via its OpenAI-compatible API,
so we use the well-supported `openai` client pointed at Mistral's servers.

Swap providers by changing BASE_URL / MODEL / the env var name below.

`complete()`        -> raw response (used by the research agent for tool calls)
`text_of()`         -> pull plain text out of a response
`complete_json(T)`  -> force the model to fill a Pydantic schema T
"""

from __future__ import annotations
import json
import os
import time
from typing import Type, TypeVar, List, Dict, Any

from pydantic import BaseModel
from openai import OpenAI

T = TypeVar("T", bound=BaseModel)

# --- provider config (Mistral, OpenAI-compatible endpoint) ---
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.mistral.ai/v1")
MODEL = os.environ.get("LLM_MODEL", "mistral-large-latest")
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.environ.get("MISTRAL_API_KEY")
        if not key:
            raise RuntimeError(
                "MISTRAL_API_KEY is not set. In PowerShell run:\n"
                '  $env:MISTRAL_API_KEY="your-key-here"'
            )
        _client = OpenAI(api_key=key, base_url=BASE_URL)
    return _client


def _call(**kwargs):
    """
    Make one chat call, automatically waiting out the free-tier rate limit.
    Mistral's free tier allows ~2 requests/minute, so on a 429 we pause and retry.
    """
    client = _get_client()
    for attempt in range(6):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "rate" in msg or "capacity" in msg or "limit" in msg:
                wait = 20 * (attempt + 1)
                print(f"[free-tier rate limit hit — waiting {wait}s then retrying...]")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Mistral kept rate-limiting. Wait a minute and try again.")


def complete(system: str, messages: List[Dict[str, Any]], temperature: float = 0.4,
             tools: list | None = None, max_tokens: int = 2000):
    """Raw call. Returns the response so callers can read tool calls."""
    msgs = [{"role": "system", "content": system}] + messages
    kwargs: Dict[str, Any] = dict(
        model=MODEL, messages=msgs, temperature=temperature, max_tokens=max_tokens,
    )
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    return _call(**kwargs)


def text_of(response) -> str:
    return (response.choices[0].message.content or "").strip()


def complete_json(system: str, user: str, schema: Type[T], temperature: float = 0.0) -> T:
    """
    Force a structured answer. We ask for JSON, validate with Pydantic,
    and retry once if the model returns something invalid.
    """
    instruction = (
        f"{system}\n\nReturn ONLY a valid JSON object matching this schema. "
        f"No prose, no markdown fences.\n\nSCHEMA:\n{json.dumps(schema.model_json_schema())}"
    )
    for attempt in range(2):
        resp = _call(
            model=MODEL,
            messages=[{"role": "system", "content": instruction},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return schema.model_validate_json(raw)
        except Exception as e:
            if attempt == 1:
                raise ValueError(f"Model did not return valid {schema.__name__}: {e}\nGot:\n{raw}")
            user = f"{user}\n\nYour previous reply was invalid: {e}. Return valid JSON only."
    raise RuntimeError("unreachable")
