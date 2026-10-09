"""Mongo-backed, expiring provider-health signals from real requests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.memory.mongo import MongoRepository


class ProviderHealthRepository:
    def __init__(self, mongo_repository: MongoRepository) -> None:
        self._mongo = mongo_repository

    @staticmethod
    def _key(provider: str) -> str:
        return f"provider:health:{provider}"

    def in_cooldown(self, provider: str) -> bool:
        state = self._mongo.client.hgetall(self._key(provider))
        return bool(state.get("cooldown_until", "") > datetime.now(UTC).isoformat())

    def record_success(self, provider: str) -> None:
        now = datetime.now(UTC).isoformat()
        self._mongo.client.hset(self._key(provider), {"status": "healthy", "last_success": now, "cooldown_until": ""})
        self._mongo.client.hincrby(self._key(provider), "requests", 1)
        self._mongo.client.expire(self._key(provider), 60 * 60 * 24 * 30)

    def record_failure(self, provider: str, failure_type: str, *, cooldown_seconds: int) -> None:
        now = datetime.now(UTC)
        self._mongo.client.hset(self._key(provider), {"status": failure_type, "last_failure": now.isoformat(), "failure_type": failure_type, "cooldown_until": (now + timedelta(seconds=cooldown_seconds)).isoformat()})
        self._mongo.client.hincrby(self._key(provider), "requests", 1)
        self._mongo.client.expire(self._key(provider), 60 * 60 * 24 * 30)
