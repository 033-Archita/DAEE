"""Compatibility layer for Redis-backed and MongoDB Atlas-backed persistence.

Older imports still reference `app.memory.redis`, and the existing tests expect a
real Redis client wrapper with the same API used by the project code.
"""

from __future__ import annotations

import importlib
import re
from typing import Any


class RedisConnectionError(ConnectionError):
    """Raised when the Redis service cannot be reached."""


class RedisRepository:
    """Small Redis-compatible repository that matches the app's usage patterns."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client
        raise RuntimeError("Redis is not connected. Call connect() first.")

    @property
    def safe_location(self) -> str:
        parsed = re.sub(r":([^@]+)@", ":***@", self._url)
        return parsed.replace("redis://", "").replace("rediss://", "")

    def connect(self) -> None:
        import redis

        try:
            self._client = redis.Redis.from_url(self._url, decode_responses=True)
            self._client.ping()
        except redis.ConnectionError as error:
            raise RedisConnectionError(f"Could not connect to Redis at {self.safe_location}.") from error

    def get(self, key: str) -> str | None:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return self._client.get(key)

    def set(self, key: str, value: str, *, expires_in_seconds: int | None = None, nx: bool = False) -> bool:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        if expires_in_seconds is not None and nx:
            return bool(self._client.set(key, value, ex=expires_in_seconds, nx=True))
        if expires_in_seconds is not None:
            return bool(self._client.set(key, value, ex=expires_in_seconds))
        if nx:
            return bool(self._client.set(key, value, nx=True))
        return bool(self._client.set(key, value))

    def delete(self, key: str) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.delete(key))

    def hgetall(self, key: str) -> dict[str, str]:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return dict(self._client.hgetall(key))

    def hset(self, key: str, mapping: dict[str, Any]) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.hset(key, mapping=mapping))

    def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.hincrby(key, field, amount))

    def expire(self, key: str, seconds: int) -> bool:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return bool(self._client.expire(key, seconds))

    def llen(self, key: str) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.llen(key))

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return list(self._client.lrange(key, start, end))

    def rpush(self, key: str, *values: str) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.rpush(key, *values))

    def lpush(self, key: str, *values: str) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.lpush(key, *values))

    def lpop(self, key: str, count: int | None = None) -> str | list[str] | None:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        if count is None:
            return self._client.lpop(key)
        return self._client.lpop(key, count)

    def smembers(self, key: str) -> set[str]:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return set(self._client.smembers(key))

    def sadd(self, key: str, *values: str) -> int:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return int(self._client.sadd(key, *values))

    def __getattr__(self, name: str) -> Any:
        if self._client is None:
            raise RuntimeError("Redis is not connected. Call connect() first.")
        return getattr(self._client, name)


def __getattr__(name: str) -> Any:
    if name == "redis":
        return importlib.import_module("redis")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["RedisConnectionError", "RedisRepository", "redis"]
