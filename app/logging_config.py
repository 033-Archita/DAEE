"""Small, structured logging setup with no secret-bearing fields."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event"):
            payload["event"] = record.event
        for name in ("provider", "reason"):
            value = getattr(record, name, None)
            if value is not None:
                payload[name] = value
        if record.exc_info:
            exception = self.formatException(record.exc_info)
            for name in (
                "MONGO_URI",
                "OPENROUTER_API_KEY",
                "CLOUDFLARE_API_TOKEN",
                "MISTRAL_API_KEY",
                "TAVILY_API_KEY",
                "GMAIL_OAUTH_CLIENT_SECRET",
                "GMAIL_REFRESH_TOKEN",
            ):
                secret = os.getenv(name)
                if secret:
                    exception = exception.replace(secret, "[REDACTED]")
            payload["exception"] = exception
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
