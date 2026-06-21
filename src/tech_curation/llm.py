"""Shared LLM client (DeepSeek via OpenAI-compatible API)."""
from __future__ import annotations

import os

from openai import OpenAI

_BASE_URL = "https://api.deepseek.com"
MODEL_FAST = "deepseek-chat"
MODEL_SMART = "deepseek-chat"


def chat(
    messages: list[dict],
    *,
    max_tokens: int = 256,
    system: str | None = None,
    model: str = MODEL_FAST,
) -> str:
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url=_BASE_URL)
    if system:
        messages = [{"role": "system", "content": system}] + list(messages)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content.strip()
