"""Persistence for the Premium System audit trail."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.premium_history import PremiumHistory
from src.repositories.base import BaseRepository


class PremiumHistoryRepository(BaseRepository[PremiumHistory]):
    """Read/write helpers for :class:`PremiumHistory`."""

    model = PremiumHistory

    async def list_for_user(self, user_id: int) -> list[PremiumHistory]:
        """Return every premium history row for ``user_id``, most recent first."""
        result = await self._session.execute(
            select(PremiumHistory).where(PremiumHistory.user_id == user_id).order_by(PremiumHistory.id.desc())
        )
        return list(result.scalars().all())
