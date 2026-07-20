"""Upserts the user row and refreshes their last-active timestamp."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.services.user_service import UserService


class UserActivityMiddleware(BaseMiddleware):
    """Ensures every interacting user exists in the DB with fresh activity data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Register/refresh the user, then continue the middleware chain."""
        user = getattr(event, "from_user", None)
        user_service: UserService | None = data.get("user_service")
        if user is not None and user_service is not None:
            record, _ = await user_service.get_or_register(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
            )
            await user_service.touch_activity(user.id)
            data["db_user"] = record
        return await handler(event, data)
