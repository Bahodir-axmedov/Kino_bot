"""Upserts the user row and refreshes their last-active timestamp."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.services.user_service import UserService


def _extract_start_referral(event: TelegramObject) -> int | None:
    """Return the numeric referral payload from a ``/start <id>`` deep link, if any.

    This must live here -- not only in ``handlers/user/start.py`` -- because
    this middleware is what actually creates the user row: it runs before
    every handler, on every single update. If it created the row without
    ``referred_by``, the row would already exist by the time the ``/start``
    handler ran its own lookup, so the "brand-new user" branch (the only
    place ``referred_by``/``invite_count`` are ever recorded) would never be
    reached and referral tracking would be silently broken for every single
    referred signup.
    """
    if not isinstance(event, Message) or not event.text:
        return None
    parts = event.text.strip().split(maxsplit=1)
    if not parts:
        return None
    command = parts[0].split("@", 1)[0]
    if command != "/start" or len(parts) < 2:
        return None
    payload = parts[1].strip()
    return int(payload) if payload.isdigit() else None


class UserActivityMiddleware(BaseMiddleware):
    """Ensures every interacting user exists in the DB with fresh activity data."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Register/refresh the user (capturing any /start referral), then continue."""
        user = getattr(event, "from_user", None)
        user_service: UserService | None = data.get("user_service")
        if user is not None and user_service is not None:
            record, is_new = await user_service.get_or_register(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                referred_by=_extract_start_referral(event),
            )
            await user_service.touch_activity(user.id)
            data["db_user"] = record
            data["db_user_is_new"] = is_new
        return await handler(event, data)
