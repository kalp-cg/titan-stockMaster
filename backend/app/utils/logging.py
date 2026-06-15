"""
Structured JSON logging using structlog.

Provides correlation-ID injection, request context, and configurable
log level.  Import `get_logger` everywhere — never use `print`.
"""

from __future__ import annotations

import logging
import sys
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

# Per-request correlation ID stored in a context variable so it propagates
# through async call stacks without any manual passing.
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get() or str(uuid.uuid4())


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def _add_correlation_id(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Inject the current correlation ID into every log record."""
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def _order_keys(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Ensure timestamp and level appear first for readability."""
    ordered: dict[str, Any] = {}
    for key in ("timestamp", "level", "correlation_id", "event"):
        if key in event_dict:
            ordered[key] = event_dict.pop(key)
    ordered.update(event_dict)
    return ordered


def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure structlog for the application.

    Args:
        log_level: Standard Python log level string.
        json_logs: If True, emit JSON; otherwise emit human-readable format.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[Callable[..., Any]] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_correlation_id,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            _order_keys,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "yfinance", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)
