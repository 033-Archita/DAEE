"""Configured concrete LLM providers."""

from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.cloudflare import CloudflareWorkersAIProvider


def cloudflare(account_id: str | None, api_token: str | None, model: str) -> CloudflareWorkersAIProvider:
    return CloudflareWorkersAIProvider(account_id=account_id, api_token=api_token, model=model)


def openrouter(api_key: str | None, model: str) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openrouter",
        api_key=api_key,
        model=model,
        endpoint="https://openrouter.ai/api/v1/chat/completions",
        extra_headers={
            "HTTP-Referer": "https://github.com/033-Archita/DAEE",
            "X-OpenRouter-Title": "Daily Curiosity Agent",
        },
    )


def mistral(api_key: str | None, model: str) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(name="mistral", api_key=api_key, model=model, endpoint="https://api.mistral.ai/v1/chat/completions")
