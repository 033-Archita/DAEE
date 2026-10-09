"""Daily selection state, deliberately separate from future research/email work."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.memory.redis import RedisRepository
from app.topics.models import TopicCandidate
from app.topics.repository import TopicRepository


class DailyRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class DailyRun:
    date: str
    status: str
    topics: list[TopicCandidate]


class DailyRunService:
    """Reserves exactly three topics once; retries return the same reservation."""

    def __init__(self, redis_repository: RedisRepository, topics: TopicRepository) -> None:
        self._redis, self._topics = redis_repository, topics

    @staticmethod
    def _key(date: str) -> str:
        return f"daily:run:{date}"

    @staticmethod
    def _lock_key(date: str) -> str:
        return f"daily:run-lock:{date}"

    @staticmethod
    def _delivery_lock_key(date: str) -> str:
        return f"daily:delivery-lock:{date}"

    def start(self, date: str) -> DailyRun:
        key = self._key(date)
        existing = self._redis.client.hgetall(key)
        if existing:
            return DailyRun(date=date, status=existing["status"], topics=[TopicCandidate.from_dict(item) for item in json.loads(existing["topics"])])
        if not self._redis.client.set(self._lock_key(date), "1", nx=True, ex=60 * 60 * 48):
            existing = self._redis.client.hgetall(key)
            if existing:
                return DailyRun(date=date, status=existing["status"], topics=[TopicCandidate.from_dict(item) for item in json.loads(existing["topics"])])
            raise DailyRunError("A daily run is being initialized; retry shortly.")
        reserved = self._topics.reserve_topics(3)
        if len(reserved) != 3:
            # Put back any partial reservation in its original order before failing.
            if reserved:
                self._redis.client.lpush(self._topics.pool_key, *(json.dumps(item.as_dict()) for item in reversed(reserved)))
            raise DailyRunError("At least three unused topics are required before starting a daily run.")
        self._redis.client.hset(key, mapping={"status": "started", "topics": json.dumps([item.as_dict() for item in reserved])})
        return DailyRun(date=date, status="started", topics=reserved)

    def mark_completed(self, date: str) -> DailyRun:
        run = self.start(date)
        if run.status == "completed":
            return run
        self._topics.mark_sent(run.topics)
        self._redis.client.hset(self._key(date), mapping={"status": "completed"})
        return DailyRun(date=date, status="completed", topics=run.topics)

    def begin_email_delivery(self, date: str) -> bool:
        """Claim delivery once. An ambiguous in-progress send is never resent automatically."""
        run = self.start(date)
        state = self._redis.client.hgetall(self._key(date))
        if run.status == "completed" or state.get("email_status") in {"sending", "sent"}:
            return False
        if not self._redis.client.set(self._delivery_lock_key(date), "1", nx=True, ex=60 * 30):
            return False
        self._redis.client.hset(self._key(date), mapping={"email_status": "sending"})
        return True

    def mark_email_sent(self, date: str, gmail_message_id: str) -> None:
        self._redis.client.hset(self._key(date), mapping={"email_status": "sent", "gmail_message_id": gmail_message_id})
        self._redis.delete(self._delivery_lock_key(date))

    def mark_email_send_failed(self, date: str, reason: str) -> None:
        self._redis.client.hset(self._key(date), mapping={"email_status": "failed", "email_failure_reason": reason[:500]})
        self._redis.delete(self._delivery_lock_key(date))

    def mark_failed(self, date: str, reason: str) -> DailyRun:
        run = self.start(date)
        if run.status == "completed":
            return run
        self._redis.client.hset(self._key(date), mapping={"status": "failed", "failure_reason": reason[:500]})
        return DailyRun(date=date, status="failed", topics=run.topics)
