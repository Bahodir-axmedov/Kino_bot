"""Data-access operations for mandatory-subscription channels."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.force_sub_channel import ForceSubChannel
from src.repositories.base import BaseRepository


class ForceSubRepository(BaseRepository[ForceSubChannel]):
    """Repository encapsulating all SQL access for ``ForceSubChannel`` rows."""

    model = ForceSubChannel

    async def get_by_chat_id(self, chat_id: int) -> ForceSubChannel | None:
        """Return the force-subscribe channel for ``chat_id``, or ``None``."""
        statement = select(ForceSubChannel).where(ForceSubChannel.chat_id == chat_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[ForceSubChannel]:
        """Return active mandatory-subscription channels ordered by position."""
        statement = (
            select(ForceSubChannel)
            .where(ForceSubChannel.is_active.is_(True))
            .order_by(ForceSubChannel.position.asc())
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def list_all(self) -> Sequence[ForceSubChannel]:
        """Return every configured mandatory-subscription channel."""
        statement = select(ForceSubChannel).order_by(ForceSubChannel.position.asc())
        result = await self._session.execute(statement)
        return result.scalars().all()
