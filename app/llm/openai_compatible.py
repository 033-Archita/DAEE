"""HTTP implementation shared by OpenAI-compatible providers."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.llm.base import LLMResponse, ProviderUnavailableError, RateLimitError


class OpenAICompatibleProvider:
    name: str

    def __init__(self, *, name: str, api_key: str | None, model: str, endpoint: str, extra_headers: dict[str, str] | None = None) -> None:
        self.name, self._api_key, self._model, self._endpoint = name, api_key, model, endpoint
        self._extra_headers = extra_headers or {}

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, *, task: str) -> LLMResponse:
        if not self.is_configured:
            raise ProviderUnavailableError(f"{self.name} is not configured.")
        body = json.dumps({"model": self._model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.9}).encode()
        request = Request(self._endpoint, data=body, headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json", **self._extra_headers}, method="POST")
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode())
        except HTTPError as error:
            if error.code == 429:
                raise RateLimitError(f"{self.name} rate limited the request.") from error
            if error.code >= 500 or error.code in {408, 409}:
                raise ProviderUnavailableError(f"{self.name} is temporarily unavailable ({error.code}).") from error
            raise ProviderUnavailableError(f"{self.name} rejected the request ({error.code}).") from error
        except (URLError, TimeoutError) as error:
            raise ProviderUnavailableError(f"{self.name} could not be reached.") from error
        try:
            usage = payload.get("usage", {})
            content = payload["choices"][0]["message"]["content"]
        except (AttributeError, IndexError, KeyError, TypeError) as error:
            raise ProviderUnavailableError(f"{self.name} returned an invalid response.") from error
        return LLMResponse(text=content, provider=self.name, model=self._model, usage={"prompt_tokens": int(usage.get("prompt_tokens", 0)), "completion_tokens": int(usage.get("completion_tokens", 0)), "total_tokens": int(usage.get("total_tokens", 0))})
