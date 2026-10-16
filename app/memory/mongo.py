"""MongoDB Atlas-backed application memory used by the project."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.errors import ConfigurationError as PyMongoConfigurationError
from pymongo.errors import DuplicateKeyError
from pymongo.errors import PyMongoError


class MongoConnectionError(ConnectionError):
    """Raised when MongoDB Atlas cannot be reached."""


class RedisConnectionError(MongoConnectionError):
    """Backward-compatible alias used by older imports."""


class MongoRepository:
    """Mongo-backed repository implementing the small Redis-like API used by the app."""

    def __init__(self, mongo_uri: str, database: str | None = None) -> None:
        self._mongo_uri = mongo_uri
        self._database_name = database or (urlparse(mongo_uri).path.lstrip("/") or "daily_curiosity")
        self._client: MongoClient | None = None
        self._database = None
        self._collection = None

    @property
    def safe_location(self) -> str:
        parsed = urlparse(self._mongo_uri)
        return f"{parsed.hostname}:{parsed.port or 27017}"

    def connect(self) -> None:
        try:
            self._client = MongoClient(self._mongo_uri, serverSelectionTimeoutMS=5000)
            self._database = self._client[self._database_name]
            self._collection = self._database["application_state"]
            self._client.admin.command("ping")
        except PyMongoError as error:
            if isinstance(error, PyMongoConfigurationError) and "DNS query name does not exist" in str(error):
                message = "The MongoDB Atlas SRV hostname in MONGO_URI could not be resolved. Copy the current connection string from Atlas > Connect > Drivers."
            else:
                message = f"Could not connect to MongoDB Atlas at {self.safe_location} ({type(error).__name__}). Check the Atlas network access list and database credentials."
            raise MongoConnectionError(message) from error

    @property
    def client(self) -> "MongoRepository":
        if self._uses_legacy_client():
            return self._client
        if self._collection is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        return self

    def _uses_legacy_client(self) -> bool:
        return self._client is not None and not isinstance(self._client, MongoClient)

    def _delegate_to_client(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        if self._client is not None and not hasattr(self._client, "_collection") and hasattr(self._client, method_name):
            return getattr(self._client, method_name)(*args, **kwargs)
        if self._collection is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        raise AttributeError(f"MongoRepository has no attribute '{method_name}'")

    def _read(self, key: str) -> dict[str, Any] | None:
        if self._collection is None:
            raise RuntimeError("MongoDB is not connected. Call connect() first.")
        document = self._collection.find_one({"_id": key})
        if not document:
            return None
        expires_at = document.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
            self._collection.delete_one({"_id": key})
            return None
        return document

    def _write_value(self, key: str, value: Any, *, expires_in_seconds: int | None = None) -> None:
        payload: dict[str, Any] = {"_id": key, "value": value, "kind": "value"}
        if expires_in_seconds is not None:
            payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat()
        self._collection.update_one({"_id": key}, {"$set": payload}, upsert=True)

    def get(self, key: str) -> str | None:
        document = self._read(key)
        if document is None:
            return None
        value = document.get("value")
        return value if isinstance(value, str) else json.dumps(value) if value is not None else None

    def set(
        self,
        key: str,
        value: str,
        *,
        expires_in_seconds: int | None = None,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool:
        if ex is not None:
            if expires_in_seconds is not None:
                raise ValueError("Use either ex or expires_in_seconds, not both.")
            expires_in_seconds = ex
        if self._uses_legacy_client():
            return bool(self._client.set(key, value, ex=expires_in_seconds, nx=nx))
        if nx:
            if self._read(key) is not None:
                return False
            payload: dict[str, Any] = {"_id": key, "value": value, "kind": "value"}
            if expires_in_seconds is not None:
                payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)).isoformat()
            try:
                self._collection.insert_one(payload)
            except DuplicateKeyError:
                return False
            return True
        self._write_value(key, value, expires_in_seconds=expires_in_seconds)
        return True

    def delete(self, key: str) -> int:
        if self._uses_legacy_client():
            return int(self._client.delete(key))
        result = self._collection.delete_one({"_id": key})
        return int(result.deleted_count)

    def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        document = self._read(key)
        if document is None:
            return None
        value = document.get("value")
        if value is None:
            return None
        return value if isinstance(value, (dict, list)) else json.loads(str(value))

    def set_json(self, key: str, value: dict[str, Any] | list[Any], *, expires_in_seconds: int | None = None) -> bool:
        self._write_value(key, value, expires_in_seconds=expires_in_seconds)
        return True

    def hset(self, key: str, mapping: dict[str, Any]) -> int:
        if self._uses_legacy_client():
            return int(self._client.hset(key, mapping=mapping))
        document = self._read(key) or {"_id": key, "value": {}, "kind": "hash"}
        current = dict(document.get("value", {}))
        new_fields = 0
        for field, item in mapping.items():
            if field not in current:
                new_fields += 1
            current[str(field)] = str(item)
        self._collection.update_one({"_id": key}, {"$set": {"value": current, "kind": "hash"}}, upsert=True)
        return new_fields

    def hgetall(self, key: str) -> dict[str, str]:
        document = self._read(key)
        if document is None:
            return {}
        value = document.get("value", {})
        if not isinstance(value, dict):
            return {}
        return {str(k): str(v) for k, v in value.items()}

    def hincrby(self, key: str, field: str, amount: int = 1) -> int:
        if self._uses_legacy_client():
            return int(self._client.hincrby(key, field, amount))
        document = self._read(key) or {"_id": key, "value": {}, "kind": "hash"}
        current = dict(document.get("value", {}))
        current_value = int(current.get(field, 0))
        next_value = current_value + int(amount)
        current[str(field)] = str(next_value)
        self._collection.update_one({"_id": key}, {"$set": {"value": current, "kind": "hash"}}, upsert=True)
        return next_value

    def expire(self, key: str, seconds: int) -> bool:
        if self._uses_legacy_client():
            return bool(self._client.expire(key, seconds))
        document = self._read(key)
        if document is None:
            return False
        self._collection.update_one({"_id": key}, {"$set": {"expires_at": (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()}})
        return True

    def llen(self, key: str) -> int:
        if self._uses_legacy_client():
            return int(self._client.llen(key))
        document = self._read(key)
        if document is None:
            return 0
        value = document.get("value", [])
        return len(value) if isinstance(value, list) else 0

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        if self._uses_legacy_client():
            return list(self._client.lrange(key, start, end))
        document = self._read(key)
        items = document.get("value", []) if document else []
        if not isinstance(items, list):
            return []
        if end == -1:
            return [str(item) for item in items[start:]]
        return [str(item) for item in items[start : end + 1]]

    def rpush(self, key: str, *values: str) -> int:
        if self._uses_legacy_client():
            return int(self._client.rpush(key, *values))
        document = self._read(key) or {"_id": key, "value": [], "kind": "list"}
        current = list(document.get("value", []))
        current.extend(values)
        self._collection.update_one({"_id": key}, {"$set": {"value": current, "kind": "list"}}, upsert=True)
        return len(current)

    def lpush(self, key: str, *values: str) -> int:
        if self._uses_legacy_client():
            return int(self._client.lpush(key, *values))
        document = self._read(key) or {"_id": key, "value": [], "kind": "list"}
        current = list(document.get("value", []))
        current = list(values) + current
        self._collection.update_one({"_id": key}, {"$set": {"value": current, "kind": "list"}}, upsert=True)
        return len(current)

    def lpop(self, key: str, count: int | None = None) -> str | list[str] | None:
        if self._uses_legacy_client():
            return self._client.lpop(key, count) if count is not None else self._client.lpop(key)
        document = self._read(key)
        if document is None:
            return None
        items = list(document.get("value", []))
        if not items:
            return None
        if count is None:
            item = items.pop(0)
            self._collection.update_one({"_id": key}, {"$set": {"value": items, "kind": "list"}})
            return str(item)
        result = items[:count]
        remaining = items[count:]
        self._collection.update_one({"_id": key}, {"$set": {"value": remaining, "kind": "list"}})
        return [str(item) for item in result]

    def smembers(self, key: str) -> set[str]:
        if self._uses_legacy_client():
            return set(self._client.smembers(key))
        document = self._read(key)
        if document is None:
            return set()
        value = document.get("value", set())
        if not isinstance(value, set):
            return set()
        return {str(item) for item in value}

    def sadd(self, key: str, *values: str) -> int:
        if self._uses_legacy_client():
            return int(self._client.sadd(key, *values))
        document = self._read(key) or {"_id": key, "value": set(), "kind": "set"}
        current = set(document.get("value", set()))
        before = len(current)
        current.update(values)
        self._collection.update_one({"_id": key}, {"$set": {"value": list(current), "kind": "set"}}, upsert=True)
        return len(current) - before

    def hget(self, key: str, field: str) -> str | None:
        value = self.hgetall(key)
        return value.get(field)

    def setnx(self, key: str, value: str, *, expires_in_seconds: int | None = None) -> bool:
        existing = self._read(key)
        if existing is not None:
            return False
        self._write_value(key, value, expires_in_seconds=expires_in_seconds)
        return True

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"MongoRepository has no attribute '{name}'")


RedisRepository = MongoRepository
