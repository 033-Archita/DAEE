"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


def load_dotenv(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE entries without overriding real environment values."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer.") from error
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _provider_order() -> tuple[str, ...]:
    supported = {"groq", "mistral"}
    order = tuple(item.strip().lower() for item in os.getenv("LLM_PROVIDER_ORDER", "groq,mistral").split(",") if item.strip())
    if not order or len(order) != len(set(order)) or any(item not in supported for item in order):
        raise ConfigurationError("LLM_PROVIDER_ORDER must be a unique comma-separated list of groq and/or mistral.")
    return order


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_database: str
    redis_url: str
    app_env: str
    log_level: str
    timezone: str
    pool_size: int
    low_watermark: int
    llm_provider_order: tuple[str, ...]
    groq_api_key: str | None
    mistral_api_key: str | None
    groq_model: str
    mistral_model: str
    tavily_api_key: str | None
    tavily_max_results: int
    gmail_oauth_client_id: str | None
    gmail_oauth_client_secret: str | None
    gmail_refresh_token: str | None
    gmail_recipient: str | None

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        mongo_uri = (os.getenv("MONGO_URI") or os.getenv("REDIS_URL", "")).strip()
        if not mongo_uri:
            raise ConfigurationError("MONGO_URI is required.")
        parsed_mongo_uri = urlparse(mongo_uri)
        if parsed_mongo_uri.scheme not in {"mongodb", "mongodb+srv", "redis", "rediss"} or not parsed_mongo_uri.hostname:
            raise ConfigurationError("MONGO_URI must be a valid mongodb://, mongodb+srv://, redis://, or rediss:// URL.")

        mongo_database = (os.getenv("MONGO_DATABASE") or parsed_mongo_uri.path.lstrip("/") or "daily_curiosity").strip()
        if not mongo_database:
            raise ConfigurationError("MONGO_DATABASE is required.")

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if log_level not in valid_levels:
            raise ConfigurationError(f"LOG_LEVEL must be one of: {', '.join(sorted(valid_levels))}.")

        timezone = os.getenv("TIMEZONE", "Asia/Kolkata")
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ConfigurationError(f"TIMEZONE is not a valid IANA timezone: {timezone}.") from error

        pool_size = _positive_int("POOL_SIZE", 50)
        low_watermark = _positive_int("LOW_WATERMARK", 15)
        if low_watermark >= pool_size:
            raise ConfigurationError("LOW_WATERMARK must be smaller than POOL_SIZE.")

        return cls(
            mongo_uri=mongo_uri,
            mongo_database=mongo_database,
            redis_url=mongo_uri,
            app_env=os.getenv("APP_ENV", "development"),
            log_level=log_level,
            timezone=timezone,
            pool_size=pool_size,
            low_watermark=low_watermark,
            llm_provider_order=_provider_order(),
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            mistral_api_key=os.getenv("MISTRAL_API_KEY") or None,
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            mistral_model=os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
            tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
            tavily_max_results=_positive_int("TAVILY_MAX_RESULTS", 5),
            gmail_oauth_client_id=os.getenv("GMAIL_OAUTH_CLIENT_ID") or None,
            gmail_oauth_client_secret=os.getenv("GMAIL_OAUTH_CLIENT_SECRET") or None,
            gmail_refresh_token=os.getenv("GMAIL_REFRESH_TOKEN") or None,
            gmail_recipient=os.getenv("GMAIL_RECIPIENT") or None,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings for normal application execution."""
    return Settings.from_environment()
