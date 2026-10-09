"""Configured concrete LLM providers."""

from app.llm.openai_compatible import OpenAICompatibleProvider


def groq(api_key: str | None, model: str) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(name="groq", api_key=api_key, model=model, endpoint="https://api.groq.com/openai/v1/chat/completions")


def mistral(api_key: str | None, model: str) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(name="mistral", api_key=api_key, model=model, endpoint="https://api.mistral.ai/v1/chat/completions")
