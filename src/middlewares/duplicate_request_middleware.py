"""Duplicate-request / replay protection.

Guards against the same Telegram update being processed twice -- e.g. from
a Telegram retry after a slow response, or a replayed webhook delivery.
Uses a short-TTL in-process cache keyed by update id, which is O(1) and
adds no database round-trip to the hot path.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from src.utils.cache import TTLCache


class DuplicateRequestMiddleware(BaseMiddleware):
    """Drops any Telegram update whose ``update_id`` was already processed recently."""

    def __init__(self, ttl_seconds: float = 120) -> None:
        """Configure how long a processed update id is remembered."""
        super().__init__()
        self._seen: TTLCache[int, bool] = TTLCache(ttl_seconds=ttl_seconds, max_size=50000)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Skip the handler entirely for an ``update_id`` seen within the TTL window."""
        if isinstance(event, Update):
            if self._seen.get(event.update_id) is not None:
                return None
            self._seen.set(event.update_id, True)
        return await handler(event, data)
