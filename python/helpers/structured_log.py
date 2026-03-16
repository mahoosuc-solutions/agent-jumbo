"""Structured JSON logging for production observability."""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

_correlation_id = threading.local()


def set_correlation_id(cid: str) -> None:
    _correlation_id.value = cid


def get_correlation_id() -> str:
    return getattr(_correlation_id, "value", "")


class StructuredFormatter(logging.Formatter):
    """Emit log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        cid = get_correlation_id()
        if cid:
            entry["correlation_id"] = cid
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = str(record.exc_info[1])
        # Merge any extra fields
        for key in ("event", "user", "ip", "path", "status", "duration_ms", "request_id"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val
        return json.dumps(entry, default=str)


def setup_structured_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured logging. Call once at startup."""
    logger = logging.getLogger("agent_jumbo")
    if logger.handlers:
        return logger  # Already configured

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Get the structured logger."""
    return logging.getLogger("agent_jumbo")


def log_event(
    event: str,
    level: str = "INFO",
    **kwargs: Any,
) -> None:
    """Log a structured event."""
    logger = get_logger()
    extra = {"event": event, **kwargs}
    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        event,
        extra=extra,
    )
