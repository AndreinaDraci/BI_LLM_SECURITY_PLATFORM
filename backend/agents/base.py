"""
Base agent class with shared LLM call logic (Anthropic + OpenAI + Groq + OpenRouter).
"""
from __future__ import annotations
import os
import time
from typing import Any

try:
    import anthropic as _anthropic
    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False

try:
    import openai as _openai
    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class BaseAgent:
    name: str = "BaseAgent"
    description: str = ""

    def __init__(self, provider: str = "anthropic", model: str | None = None):
        self.provider = provider.lower()

        if self.provider == "anthropic":
            self.model = model or "claude-haiku-4-5-20251001"
            if _HAS_ANTHROPIC:
                self._client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        elif self.provider == "openai":
            self.model = model or "claude-haiku-4-5-20251001"
            if _HAS_OPENAI:
                self._client = _openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        elif self.provider == "groq":
            self.model = model or "claude-haiku-4-5-20251001"
            if _HAS_OPENAI:
                self._client = _openai.OpenAI(
                    api_key=os.getenv("GROQ_API_KEY"),
                    base_url="https://api.groq.com/openai/v1",
                )

        elif self.provider == "openrouter":
            self.model = model or "claude-haiku-4-5-20251001"
            if _HAS_OPENAI:
                self._client = _openai.OpenAI(
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url="https://openrouter.ai/api/v1",
                )

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _call_llm(self, system: str, user: str, max_tokens: int = 1500) -> str:
        for attempt in range(3):
            try:
                if self.provider == "anthropic" and _HAS_ANTHROPIC:
                    resp = self._client.messages.create(
                        model=self.model,
                        max_tokens=max_tokens,
                        system=system,
                        messages=[{"role": "user", "content": user}],
                    )
                    return resp.content[0].text

                elif self.provider in ("openai", "groq", "openrouter") and _HAS_OPENAI:
                    resp = self._client.chat.completions.create(
                        model=self.model,
                        max_tokens=max_tokens,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    )
                    return resp.choices[0].message.content

                else:
                    raise RuntimeError(f"Provider not available: {self.provider}")

            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    time.sleep(3)
                    continue
                raise

        raise RuntimeError("Max retries exceeded")

    def run(self, query: str, context: dict | None = None) -> dict[str, Any]:
        raise NotImplementedError
