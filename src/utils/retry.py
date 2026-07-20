"""Async retry decorator with exponential backoff for flaky I/O calls.

Used to wrap outbound Telegram API calls (e.g. during broadcast delivery)
and transient database operations so a single dropped connection does not
cascade into a failed admin action.
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

import structlog

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def async_retry(
    *,
    attempts: int = 3,
    base_delay_seconds: float = 0.5,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Retry an async function with exponential backoff on the given exceptions."""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as error:  # noqa: BLE001 - intentionally broad, re-raised below
                    last_error = error
                    logger.warning(
                        "retry.attempt_failed",
                        func=func.__name__,
                        attempt=attempt,
                        max_attempts=attempts,
                        error=str(error),
                    )
                    if attempt < attempts:
                        await asyncio.sleep(base_delay_seconds * (2 ** (attempt - 1)))
            assert last_error is not None
            raise last_error

        return wrapper

    return decorator
