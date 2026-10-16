from unittest.mock import patch

import pytest
from pymongo.errors import ConfigurationError

from app.memory.mongo import MongoConnectionError, MongoRepository


def test_missing_atlas_srv_record_has_actionable_safe_error() -> None:
    repository = MongoRepository("mongodb+srv://user:secret@missing.example.net", "daily_curiosity")
    with patch("app.memory.mongo.MongoClient", side_effect=ConfigurationError("The DNS query name does not exist: _mongodb._tcp.missing.example.net")):
        with pytest.raises(MongoConnectionError) as error:
            repository.connect()

    assert "Atlas > Connect > Drivers" in str(error.value)
    assert "secret" not in str(error.value)