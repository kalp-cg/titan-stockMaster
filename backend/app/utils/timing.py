"""
Performance instrumentation decorators and utilities.

Provides @timed for measuring and logging execution time of both
synchronous and asynchronous functions.  Slow operations above a
configurable threshold are logged at WARNING level.
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from app.utils.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Operations exceeding this threshold in milliseconds are logged as warnings.
_DEFAULT_SLOW_THRESHOLD_MS: float = 500.0


def _make_wrapper(func: F, label: str, slow_threshold_ms: float, log_args: bool) -> F:
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            extra: dict[str, Any] = {"operation": label}
            if log_args and args:
                extra["args"] = [repr(a)[:120] for a in args]

            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1_000
                extra["elapsed_ms"] = round(elapsed_ms, 2)
                if elapsed_ms > slow_threshold_ms:
                    logger.warning("slow_operation", **extra)
                else:
                    logger.debug("operation_completed", **extra)
                return result
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1_000
                extra["elapsed_ms"] = round(elapsed_ms, 2)
                logger.error("operation_failed", **extra)
                raise

        return async_wrapper  # type: ignore[return-value]
    else:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            extra: dict[str, Any] = {"operation": label}
            if log_args and args:
                extra["args"] = [repr(a)[:120] for a in args]

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1_000
                extra["elapsed_ms"] = round(elapsed_ms, 2)
                if elapsed_ms > slow_threshold_ms:
                    logger.warning("slow_operation", **extra)
                else:
                    logger.debug("operation_completed", **extra)
                return result
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1_000
                extra["elapsed_ms"] = round(elapsed_ms, 2)
                logger.error("operation_failed", **extra)
                raise

        return sync_wrapper  # type: ignore[return-value]


def timed(
    operation: str | Callable[..., Any] | None = None,
    *,
    slow_threshold_ms: float = _DEFAULT_SLOW_THRESHOLD_MS,
    log_args: bool = False,
) -> Any:
    """
    Decorator that measures wall-clock execution time.

    Works with both ``def`` and ``async def`` functions.
    Supports both @timed and @timed("label") syntax.
    """
    if callable(operation):
        func = operation
        label = f"{func.__module__}.{func.__qualname__}"
        return _make_wrapper(func, label, slow_threshold_ms, log_args)

    def decorator(func: F) -> F:
        label = operation or f"{func.__module__}.{func.__qualname__}"
        return _make_wrapper(func, label, slow_threshold_ms, log_args)

    return decorator


def measure() -> Callable[[], float]:
    """
    Return a callable that computes elapsed milliseconds since now.

    Useful for manual timing inside functions::

        elapsed = measure()
        do_work()
        logger.info("done", elapsed_ms=elapsed())
    """
    start = time.perf_counter()

    def elapsed_ms() -> float:
        return round((time.perf_counter() - start) * 1_000, 2)

    return elapsed_ms
