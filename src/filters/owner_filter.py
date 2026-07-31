"""Filter that only lets the single configured bot owner pass a handler."""

from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from src.config import Settings


class IsOwnerFilter(BaseFilter):
    """Passes only when the actor's Telegram id matches ``OWNER_ID``."""

    async def __call__(self, event: TelegramObject, settings: Settings, **kwargs: Any) -> bool:
        """Return ``True`` when the originating user is the configured owner."""
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return user.id == settings.owner_id
