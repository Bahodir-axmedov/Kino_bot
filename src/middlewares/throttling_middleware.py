"""Simple in-memory sliding-window rate limiter (flood control).

An in-memory limiter is sufficient for a single-process deployment; if the
bot is later scaled horizontally, this should be swapped for a Redis-backed
implementation using ``REDIS_URL`` (already present in configuration) --
the middleware boundary makes that a local, isolated change.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.utils.exceptions import RateLimitExceededError


class ThrottlingMiddleware(BaseMiddleware):
    """Rejects updates from a user that exceed ``rate_limit`` per second."""

    def __init__(self, rate_limit_per_second: float) -> None:
        """Store the configured per-user rate limit."""
        super().__init__()
        self._min_interval = 1.0 / rate_limit_per_second if rate_limit_per_second > 0 else 0.0
        self._last_seen: dict[int, float] = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Drop the update (without calling the handler) if the user is over rate."""
        user = getattr(event, "from_user", None)
        if user is not None and self._min_interval > 0:
            now = time.monotonic()
            elapsed = now - self._last_seen[user.id]
            if elapsed < self._min_interval:
                raise RateLimitExceededError(
                    "Iltimos, biroz kuting va qayta urinib ko'ring."
                )
            self._last_seen[user.id] = now
        return await handler(event, data)
