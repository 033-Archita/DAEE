from unittest.mock import Mock

from app.llm.base import LLMResponse, ProviderUnavailableError, RateLimitError
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.providers import openrouter
from app.llm.router import LLMRouter
from app.memory.health import ProviderHealthRepository
from app.memory.redis import RedisRepository
from tests.fakes import FakeRedis


def test_openai_compatible_provider_supports_structured_output() -> None:
    provider = OpenAICompatibleProvider(name="openrouter", api_key="test", model="test-model", endpoint="https://example.test")
    provider.generate = Mock(return_value=LLMResponse(text='{"topics": []}', provider="openrouter", model="test-model", usage={}))

    assert provider.generate_structured("prompt", task="topic_generation") == {"topics": []}


def test_openrouter_provider_uses_api_endpoint_and_attribution_headers() -> None:
    provider = openrouter("test-key", "openrouter/free")

    assert provider._endpoint == "https://openrouter.ai/api/v1/chat/completions"
    assert provider._extra_headers["HTTP-Referer"] == "https://github.com/033-Archita/DAEE"
    assert provider._extra_headers["X-OpenRouter-Title"] == "Daily Curiosity Agent"


class FakeProvider:
    def __init__(self, name, result=None, error=None, configured=True):
        self.name, self.result, self.error, self.configured, self.calls = name, result, error, configured, 0

    @property
    def is_configured(self): return self.configured

    def generate_structured(self, prompt, *, task):
        self.calls += 1
        if self.error: raise self.error
        return self.result


def connected_repository():
    repository = RedisRepository("redis://localhost:6379/0")
    repository._client = FakeRedis()
    return repository


def test_router_falls_back_and_records_rate_limit():
    repository = connected_repository()
    first = FakeProvider("openrouter", error=RateLimitError())
    second = FakeProvider("mistral", result={"topics": []})
    router = LLMRouter({"openrouter": first, "mistral": second}, ("openrouter", "mistral"), ProviderHealthRepository(repository))

    assert router.generate_structured("prompt", task="topic_generation") == {"topics": []}
    assert first.calls == 1 and second.calls == 1
    assert repository.client.hgetall("provider:health:openrouter")["status"] == "rate_limited"

    router.generate_structured("prompt", task="topic_generation")
    assert first.calls == 1  # cooldown avoids another request
    assert second.calls == 2


def test_router_skips_unconfigured_provider():
    repository = connected_repository()
    disabled = FakeProvider("openrouter", configured=False)
    available = FakeProvider("mistral", result={"ok": True})
    router = LLMRouter({"openrouter": disabled, "mistral": available}, ("openrouter", "mistral"), ProviderHealthRepository(repository))

    assert router.generate_structured("prompt", task="topic_generation") == {"ok": True}
    assert disabled.calls == 0
