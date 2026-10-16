import json
import logging
import sys

from app.logging_config import JsonFormatter


def test_json_formatter_includes_traceback_and_redacts_configured_secrets(monkeypatch) -> None:
    secret = "test-provider-secret"
    monkeypatch.setenv("OPENROUTER_API_KEY", secret)
    record = logging.LogRecord("test", logging.ERROR, __file__, 1, "workflow failed", (), None)
    try:
        raise RuntimeError(f"provider rejected {secret}")
    except RuntimeError:
        record.exc_info = sys.exc_info()

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "workflow failed"
    assert "RuntimeError" in payload["exception"]
    assert secret not in payload["exception"]
    assert "[REDACTED]" in payload["exception"]


def test_json_formatter_includes_safe_provider_failure_details() -> None:
    record = logging.LogRecord("test", logging.WARNING, __file__, 1, "provider unavailable", (), None)
    record.provider = "openrouter"
    record.reason = "openrouter rejected the request (401)"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["provider"] == "openrouter"
    assert payload["reason"] == "openrouter rejected the request (401)"