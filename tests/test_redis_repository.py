from unittest.mock import Mock, patch

import pytest
import redis

from app.memory.redis import RedisConnectionError, RedisRepository


def test_connect_pings_redis_and_exposes_helpers() -> None:
    client = Mock()
    client.ping.return_value = True
    client.get.return_value = "value"
    client.set.return_value = True
    client.delete.return_value = 1

    with patch("app.memory.redis.redis.Redis.from_url", return_value=client) as from_url:
        repository = RedisRepository("redis://localhost:6379/0")
        repository.connect()

    from_url.assert_called_once_with("redis://localhost:6379/0", decode_responses=True)
    client.ping.assert_called_once()
    assert repository.get("example") == "value"
    assert repository.set("example", "value", expires_in_seconds=60) is True
    client.set.assert_called_once_with("example", "value", ex=60)
    assert repository.delete("example") == 1


def test_connection_error_does_not_expose_redis_password() -> None:
    client = Mock()
    client.ping.side_effect = redis.ConnectionError("network unavailable")
    repository = RedisRepository("rediss://default:super-secret@example.redis.cloud:18342/0")

    with patch("app.memory.redis.redis.Redis.from_url", return_value=client):
        with pytest.raises(RedisConnectionError) as error:
            repository.connect()

    assert "super-secret" not in str(error.value)
    assert "example.redis.cloud:18342" in str(error.value)


def test_operations_require_a_connection() -> None:
    repository = RedisRepository("redis://localhost:6379/0")

    with pytest.raises(RuntimeError, match="not connected"):
        repository.get("example")
