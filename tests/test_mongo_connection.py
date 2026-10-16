from unittest.mock import Mock, patch

import pytest
from pymongo import MongoClient
from pymongo.errors import ConfigurationError

from app.memory.mongo import MongoConnectionError, MongoRepository


def test_missing_atlas_srv_record_has_actionable_safe_error() -> None:
    repository = MongoRepository("mongodb+srv://user:secret@missing.example.net", "daily_curiosity")
    with patch("app.memory.mongo.MongoClient", side_effect=ConfigurationError("The DNS query name does not exist: _mongodb._tcp.missing.example.net")):
        with pytest.raises(MongoConnectionError) as error:
            repository.connect()

    assert "Atlas > Connect > Drivers" in str(error.value)
    assert "secret" not in str(error.value)


def test_mongo_client_uses_repository_methods_not_dynamic_database_attributes() -> None:
    repository = MongoRepository("mongodb://localhost:27017", "daily_curiosity")
    client = MongoClient("mongodb://localhost:27017")
    repository._client = client
    repository._collection = Mock()
    repository._collection.find_one.return_value = None

    try:
        assert repository.client is repository
        assert repository.client.llen("topics:pool") == 0
    finally:
        client.close()