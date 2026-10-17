"""Cloudflare Workers AI REST provider and standalone API smoke test."""

from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import load_dotenv
from app.llm.base import LLMProvider, LLMResponse, ProviderUnavailableError, RateLimitError


class CloudflareWorkersAIProvider(LLMProvider):
    name = "cloudflare"

    def __init__(self, *, account_id: str | None, api_token: str | None, model: str) -> None:
        self._account_id, self._api_token, self._model = account_id, api_token, model

    @property
    def is_configured(self) -> bool:
        return bool(self._account_id and self._api_token)

    @property
    def endpoint(self) -> str:
        return f"https://api.cloudflare.com/client/v4/accounts/{self._account_id}/ai/run/{self._model}"

    def generate(self, prompt: str, *, task: str) -> LLMResponse:
        if not self.is_configured:
            raise ProviderUnavailableError("Cloudflare Workers AI is not configured.")
        request = Request(
            self.endpoint,
            data=json.dumps({"prompt": prompt}).encode(),
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=90) as response:
                payload = json.loads(response.read().decode())
        except HTTPError as error:
            details = error.read().decode(errors="replace")[:500]
            if error.code == 429:
                raise RateLimitError(f"Cloudflare Workers AI rate limited the request ({error.code}): {details}") from error
            if error.code >= 500 or error.code in {408, 409}:
                raise ProviderUnavailableError(f"Cloudflare Workers AI is temporarily unavailable ({error.code}): {details}") from error
            raise ProviderUnavailableError(f"Cloudflare Workers AI rejected the request ({error.code}): {details}") from error
        except (URLError, TimeoutError) as error:
            raise ProviderUnavailableError("Cloudflare Workers AI could not be reached.") from error
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ProviderUnavailableError("Cloudflare Workers AI returned invalid JSON.") from error

        if not isinstance(payload, dict):
            raise ProviderUnavailableError("Cloudflare Workers AI returned an invalid response.")
        if not payload.get("success"):
            raise ProviderUnavailableError(f"Cloudflare Workers AI returned API errors: {payload.get('errors', [])}")
        try:
            text = payload["result"]["response"]
        except (KeyError, TypeError) as error:
            raise ProviderUnavailableError("Cloudflare Workers AI returned an invalid response.") from error
        if not isinstance(text, str) or not text.strip():
            raise ProviderUnavailableError("Cloudflare Workers AI returned an empty response.")
        return LLMResponse(text=text, provider=self.name, model=self._model, usage={})


def smoke_test() -> int:
    load_dotenv()
    provider = CloudflareWorkersAIProvider(
        account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID"),
        api_token=os.getenv("CLOUDFLARE_API_TOKEN"),
        model=os.getenv("CLOUDFLARE_MODEL", "@cf/meta/llama-3.1-8b-instruct"),
    )
    if not provider.is_configured:
        print("Cloudflare Workers AI is not configured. Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN.")
        return 1
    prompt = (
        "Share one fascinating, scientifically accurate curiosity about the world. "
        "Explain it in simple, engaging language in approximately 120 words."
    )
    try:
        result = provider.generate(prompt, task="cloudflare_smoke_test")
    except (ProviderUnavailableError, RateLimitError) as error:
        print(f"Cloudflare Workers AI test failed: {error}")
        return 1
    print("\n--- GENERATED CURIOSITY ---\n")
    print(result.text)
    return 0


if __name__ == "__main__":
    sys.exit(smoke_test())