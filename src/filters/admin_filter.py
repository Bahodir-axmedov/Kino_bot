"""Filter that only lets configured/DB-registered admins pass a handler."""

from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from src.config import Settings
from src.services.admin_service import AdminService


class IsAdminFilter(BaseFilter):
    """Passes only when the actor is an active admin (owner, admin, or moderator)."""

    async def __call__(
        self,
        event: TelegramObject,
        settings: Settings,
        admin_service: AdminService,
        **kwargs: Any,
    ) -> bool:
        """Return ``True`` when the originating user has admin privileges."""
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return await admin_service.is_admin(user.id)
