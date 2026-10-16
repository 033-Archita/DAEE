from unittest.mock import Mock

from app.llm.base import LLMResponse, ProviderUnavailableError, RateLimitError
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.router import LLMRouter
from app.memory.health import ProviderHealthRepository
from app.memory.redis import RedisRepository
from tests.fakes import FakeRedis


def test_openai_compatible_provider_supports_structured_output() -> None:
    provider = OpenAICompatibleProvider(name="groq", api_key="test", model="test-model", endpoint="https://example.test")
    provider.generate = Mock(return_value=LLMResponse(text='{"topics": []}', provider="groq", model="test-model", usage={}))

    assert provider.generate_structured("prompt", task="topic_generation") == {"topics": []}


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
    first = FakeProvider("groq", error=RateLimitError())
    second = FakeProvider("mistral", result={"topics": []})
    router = LLMRouter({"groq": first, "mistral": second}, ("groq", "mistral"), ProviderHealthRepository(repository))

    assert router.generate_structured("prompt", task="topic_generation") == {"topics": []}
    assert first.calls == 1 and second.calls == 1
    assert repository.client.hgetall("provider:health:groq")["status"] == "rate_limited"

    router.generate_structured("prompt", task="topic_generation")
    assert first.calls == 1  # cooldown avoids another request
    assert second.calls == 2


def test_router_skips_unconfigured_provider():
    repository = connected_repository()
    disabled = FakeProvider("groq", configured=False)
    available = FakeProvider("mistral", result={"ok": True})
    router = LLMRouter({"groq": disabled, "mistral": available}, ("groq", "mistral"), ProviderHealthRepository(repository))

    assert router.generate_structured("prompt", task="topic_generation") == {"ok": True}
    assert disabled.calls == 0
