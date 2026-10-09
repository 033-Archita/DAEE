"""Redis structures for the unused reservoir and sent-topic history."""

from __future__ import annotations

import json

from app.memory.redis import RedisRepository
from app.topics.models import TopicCandidate


class TopicRepository:
    pool_key = "topics:pool"
    sent_key = "topics:sent"

    def __init__(self, redis_repository: RedisRepository) -> None:
        self._redis = redis_repository

    def pool_size(self) -> int:
        return int(self._redis.client.llen(self.pool_key))

    def pool_ids(self) -> set[str]:
        return {TopicCandidate.from_dict(json.loads(item)).normalized_id for item in self._redis.client.lrange(self.pool_key, 0, -1)}

    def sent_ids(self) -> set[str]:
        return set(self._redis.client.smembers(self.sent_key))

    def add_to_pool(self, candidates: list[TopicCandidate]) -> int:
        if not candidates:
            return 0
        return int(self._redis.client.rpush(self.pool_key, *(json.dumps(item.as_dict()) for item in candidates)))

    def reserve_topics(self, count: int) -> list[TopicCandidate]:
        raw_items = self._redis.client.lpop(self.pool_key, count)
        if raw_items is None:
            return []
        if isinstance(raw_items, str):
            raw_items = [raw_items]
        return [TopicCandidate.from_dict(json.loads(item)) for item in raw_items]

    def mark_sent(self, candidates: list[TopicCandidate]) -> None:
        if candidates:
            self._redis.client.sadd(self.sent_key, *(candidate.normalized_id for candidate in candidates))
