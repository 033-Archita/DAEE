import pytest

from app.config import ConfigurationError, Settings


def clear_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("REDIS_URL", "APP_ENV", "LOG_LEVEL", "TIMEZONE", "POOL_SIZE", "LOW_WATERMARK", "LLM_PROVIDER_ORDER", "GROQ_API_KEY", "GROQ_MODEL", "MISTRAL_API_KEY", "MISTRAL_MODEL"):
        monkeypatch.delenv(name, raising=False)


def test_settings_load_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    settings = Settings.from_environment()

    assert settings.timezone == "Asia/Kolkata"
    assert settings.pool_size == 50
    assert settings.low_watermark == 15


def test_mongo_uri_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.setenv("MONGO_URI", "mongodb+srv://user:pass@cluster.mongodb.net/daily_curiosity")

    settings = Settings.from_environment()

    assert settings.mongo_uri == "mongodb+srv://user:pass@cluster.mongodb.net/daily_curiosity"
    assert settings.mongo_database == "daily_curiosity"


def test_redis_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)

    with pytest.raises(ConfigurationError, match="MONGO_URI"):
        Settings.from_environment()


def test_low_watermark_must_be_smaller_than_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_settings_environment(monkeypatch)
    monkeypatch.setattr("app.config.load_dotenv", lambda: None)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("POOL_SIZE", "15")
    monkeypatch.setenv("LOW_WATERMARK", "15")

    with pytest.raises(ConfigurationError, match="LOW_WATERMARK"):
        Settings.from_environment()
