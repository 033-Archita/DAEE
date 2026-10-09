"""Bounded, configuration-driven LLM provider fallback."""

from __future__ import annotations

import logging
from typing import Any

from app.llm.base import LLMProvider, LLMResponse, ProviderUnavailableError, RateLimitError, StructuredOutputError
from app.memory.health import ProviderHealthRepository


class AllProvidersFailedError(RuntimeError):
    pass


class LLMRouter:
    def __init__(self, providers: dict[str, LLMProvider], order: tuple[str, ...], health: ProviderHealthRepository) -> None:
        self._providers, self._order, self._health = providers, order, health
        self._logger = logging.getLogger(__name__)

    def generate_structured(self, prompt: str, *, task: str) -> dict[str, Any]:
        attempted: list[str] = []
        for provider_name in self._order:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_configured or self._health.in_cooldown(provider_name):
                continue
            attempted.append(provider_name)
            try:
                result = provider.generate_structured(prompt, task=task)
            except RateLimitError:
                self._health.record_failure(provider_name, "rate_limited", cooldown_seconds=300)
                self._logger.warning("LLM provider rate limited", extra={"event": "provider_failure"})
            except (ProviderUnavailableError, StructuredOutputError):
                self._health.record_failure(provider_name, "unavailable", cooldown_seconds=60)
                self._logger.warning("LLM provider unavailable", extra={"event": "provider_failure"})
            else:
                self._health.record_success(provider_name)
                return result
        raise AllProvidersFailedError(f"No LLM provider completed task '{task}' (attempted: {', '.join(attempted) or 'none'}).")

    def generate(self, prompt: str, *, task: str) -> LLMResponse:
        attempted: list[str] = []
        for provider_name in self._order:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_configured or self._health.in_cooldown(provider_name):
                continue
            attempted.append(provider_name)
            try:
                result = provider.generate(prompt, task=task)
            except RateLimitError:
                self._health.record_failure(provider_name, "rate_limited", cooldown_seconds=300)
            except ProviderUnavailableError:
                self._health.record_failure(provider_name, "unavailable", cooldown_seconds=60)
            else:
                self._health.record_success(provider_name)
                return result
        raise AllProvidersFailedError(f"No LLM provider completed task '{task}' (attempted: {', '.join(attempted) or 'none'}).")
