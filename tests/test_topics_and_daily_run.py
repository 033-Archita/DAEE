import pytest

from app.memory.redis import RedisRepository
from app.orchestration.daily_run import DailyRunError, DailyRunService
from app.topics.deduplication import normalize_topic_id
from app.topics.generator import TopicGenerator
from app.topics.models import TopicCandidate
from app.topics.repository import TopicRepository
from tests.fakes import FakeRedis


def repositories():
    redis_repository = RedisRepository("redis://localhost:6379/0")
    redis_repository._client = FakeRedis()
    return redis_repository, TopicRepository(redis_repository)


class FakeRouter:
    def __init__(self, payload): self.payload, self.calls = payload, 0
    def generate_structured(self, prompt, *, task): self.calls += 1; return self.payload


def candidate(number):
    return TopicCandidate(title=f"Topic {number}", summary="Why it is interesting", category="History", normalized_id=f"topic-{number}")


def test_normalization_collapses_title_variations():
    assert normalize_topic_id("Kaprekar’s Constant!") == "kaprekars-constant"
    assert normalize_topic_id("  KAPREKAR'S---constant ") == "kaprekars-constant"


def test_refill_excludes_sent_and_duplicate_candidates():
    _, topics = repositories()
    topics.mark_sent([TopicCandidate("Cobra Effect", "x", "Economics", "cobra-effect")])
    router = FakeRouter({"topics": [
        {"title": "Cobra effect", "summary": "duplicate", "category": "Economics"},
        {"title": "Kaprekar's constant", "summary": "number puzzle", "category": "Mathematics"},
        {"title": "Kaprekar’s Constant", "summary": "same topic", "category": "Mathematics"},
        {"title": "The Dvorak keyboard", "summary": "layout history", "category": "Design"},
    ]})

    created = TopicGenerator(router, topics, pool_size=5, low_watermark=2).refill_if_needed()

    assert [item.normalized_id for item in created] == ["kaprekars-constant", "the-dvorak-keyboard"]
    assert topics.pool_size() == 2
    assert router.calls == 1
    assert TopicGenerator(router, topics, pool_size=5, low_watermark=1).refill_if_needed() == []


def test_daily_run_reserves_exactly_three_and_is_idempotent():
    redis_repository, topics = repositories()
    topics.add_to_pool([candidate(1), candidate(2), candidate(3)])
    service = DailyRunService(redis_repository, topics)

    first = service.start("2026-08-09")
    retry = service.start("2026-08-09")

    assert len(first.topics) == 3
    assert retry.topics == first.topics
    assert topics.pool_size() == 0
    assert service.mark_failed("2026-08-09", "LLMs unavailable").topics == first.topics
    completed = service.mark_completed("2026-08-09")
    assert completed.status == "completed"
    assert {item.normalized_id for item in first.topics} == topics.sent_ids()


def test_daily_run_returns_partial_reservation_to_pool():
    redis_repository, topics = repositories()
    topics.add_to_pool([candidate(1), candidate(2)])

    with pytest.raises(DailyRunError, match="At least three"):
        DailyRunService(redis_repository, topics).start("2026-08-09")

    assert topics.pool_size() == 2


def test_email_delivery_claim_prevents_duplicate_send_attempts():
    redis_repository, topics = repositories()
    topics.add_to_pool([candidate(1), candidate(2), candidate(3)])
    service = DailyRunService(redis_repository, topics)
    service.start("2026-08-09")

    assert service.begin_email_delivery("2026-08-09") is True
    assert service.begin_email_delivery("2026-08-09") is False
    service.mark_email_send_failed("2026-08-09", "network error")
    assert service.begin_email_delivery("2026-08-09") is True
