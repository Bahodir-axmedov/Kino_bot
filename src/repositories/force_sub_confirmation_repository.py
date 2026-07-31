"""Data-access operations for manual (non-Telegram) force-sub confirmations."""

from __future__ import annotations

from sqlalchemy import select

from src.models.force_sub_confirmation import ForceSubConfirmation
from src.repositories.base import BaseRepository


class ForceSubConfirmationRepository(BaseRepository[ForceSubConfirmation]):
    """Repository encapsulating all SQL access for ``ForceSubConfirmation`` rows."""

    model = ForceSubConfirmation

    async def has_confirmed(self, user_id: int, channel_id: int) -> bool:
        """Return ``True`` if ``user_id`` has already tapped Tasdiqlash for ``channel_id``."""
        statement = select(ForceSubConfirmation.id).where(
            ForceSubConfirmation.user_id == user_id,
            ForceSubConfirmation.channel_id == channel_id,
        )
        result = await self._session.execute(statement)
        return result.first() is not None

    async def confirm(self, user_id: int, channel_id: int) -> ForceSubConfirmation:
        """Idempotently record that ``user_id`` confirmed ``channel_id``."""
        if await self.has_confirmed(user_id, channel_id):
            statement = select(ForceSubConfirmation).where(
                ForceSubConfirmation.user_id == user_id,
                ForceSubConfirmation.channel_id == channel_id,
            )
            result = await self._session.execute(statement)
            existing = result.scalar_one()
            return existing
        entry = ForceSubConfirmation(user_id=user_id, channel_id=channel_id)
        return await self.add(entry)
