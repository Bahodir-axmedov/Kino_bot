"""Global catch-all: translates domain errors into friendly replies and logs the rest."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from src.utils.exceptions import (
    CodeReservationConflictError,
    CodeReservedError,
    DuplicateRequestError,
    InvalidInputError,
    KinoBotError,
    MovieCodeAlreadyExistsError,
    MovieNotFoundError,
    NotSubscribedError,
    PermissionDeniedError,
    RateLimitExceededError,
    UserBannedError,
    UserMutedError,
    VisibilityDeniedError,
)

logger = structlog.get_logger(__name__)

_USER_FACING_ERRORS: tuple[type[KinoBotError], ...] = (
    MovieNotFoundError,
    MovieCodeAlreadyExistsError,
    UserBannedError,
    UserMutedError,
    NotSubscribedError,
    PermissionDeniedError,
    InvalidInputError,
    RateLimitExceededError,
    CodeReservedError,
    CodeReservationConflictError,
    VisibilityDeniedError,
    DuplicateRequestError,
)


class ErrorHandlingMiddleware(BaseMiddleware):
    """Ensures no single update can crash the dispatcher or leak a stack trace."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Run the handler, converting known errors to replies and logging the rest."""
        try:
            return await handler(event, data)
        except _USER_FACING_ERRORS as error:
            await self._reply(event, str(error))
        except Exception as error:  # noqa: BLE001 - last line of defense
            logger.error("handler.unexpected_error", error=str(error), exc_info=True)
            await self._reply(event, "Kutilmagan xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")
        return None

    @staticmethod
    async def _reply(event: TelegramObject, text: str) -> None:
        """Best-effort user-facing reply; swallows secondary send failures.

        This middleware is registered on the ``update`` observer, so ``event``
        is almost always an :class:`~aiogram.types.Update` wrapper rather than
        a bare ``Message``/``CallbackQuery``. We unwrap it first; otherwise the
        ``isinstance`` checks would never match and every error would be
        swallowed silently, leaving the user with no response at all.
        """
        target: TelegramObject = event
        if isinstance(event, Update):
            target = event.message or event.callback_query or event.edited_message
        try:
            if isinstance(target, Message):
                await target.answer(text)
            elif isinstance(target, CallbackQuery):
                await target.answer(text, show_alert=True)
        except Exception:  # noqa: BLE001 - never let error reporting itself crash
            logger.warning("handler.error_reply_failed")
