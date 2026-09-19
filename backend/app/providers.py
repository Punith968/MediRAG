"""Provider interfaces and a small OpenRouter implementation for generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI


class GenerationProvider(Protocol):
    """Minimal interface used by MediRAG's generation pipeline."""

    @property
    def configured(self) -> bool: ...

    def generate(self, messages: list[dict], timeout: float = 30.0) -> str: ...


@dataclass
class OpenRouterProvider:
    """OpenAI-SDK-compatible provider backed by OpenRouter."""

    api_key: str
    model: str
    base_url: str = "https://openrouter.ai/api/v1"

    def __post_init__(self) -> None:
        self._client = (
            OpenAI(base_url=self.base_url, api_key=self.api_key)
            if self.api_key
            else None
        )

    @property
    def configured(self) -> bool:
        return self._client is not None

    def generate(self, messages: list[dict], timeout: float = 30.0) -> str:
        if self._client is None:
            raise RuntimeError("Generation provider is not configured.")
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            timeout=timeout,
        )
        return response.choices[0].message.content or ""