"""The small internal interface used by the rest of the application."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LLMError(RuntimeError):
    """Base LLM error."""


class ProviderUnavailableError(LLMError):
    """Temporary network or upstream availability failure."""


class RateLimitError(LLMError):
    """Provider rate limit failure."""


class StructuredOutputError(LLMError):
    """An otherwise successful response was not valid requested JSON."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    usage: dict[str, int]


class LLMProvider(ABC):
    name: str

    @property
    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def generate(self, prompt: str, *, task: str) -> LLMResponse: ...

    def generate_structured(self, prompt: str, *, task: str) -> dict[str, Any]:
        import json
        response = self.generate(f"{prompt}\n\nReturn only a valid JSON object. Do not use Markdown fences.", task=task)
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as error:
            raise StructuredOutputError(f"{self.name} returned invalid JSON.") from error
