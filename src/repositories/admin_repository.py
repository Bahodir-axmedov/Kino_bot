"""Data-access operations for administrator accounts (RBAC)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.admin import AdminUser
from src.repositories.base import BaseRepository


class AdminRepository(BaseRepository[AdminUser]):
    """Repository encapsulating all SQL access for ``AdminUser`` rows."""

    model = AdminUser

    async def get_by_telegram_id(self, telegram_id: int) -> AdminUser | None:
        """Return the admin record for ``telegram_id``, or ``None``."""
        statement = select(AdminUser).where(AdminUser.telegram_id == telegram_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[AdminUser]:
        """Return every currently active administrator."""
        statement = select(AdminUser).where(AdminUser.is_active.is_(True))
        result = await self._session.execute(statement)
        return result.scalars().all()
