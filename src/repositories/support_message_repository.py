"""Data-access operations for the support inbox (#12)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.support_message import SupportMessage
from src.repositories.base import BaseRepository


class SupportMessageRepository(BaseRepository[SupportMessage]):
    """Repository encapsulating all SQL access for ``SupportMessage`` rows."""

    model = SupportMessage

    async def list_open(self, limit: int = 20) -> Sequence[SupportMessage]:
        """Return the most recent open (unreplied) support messages."""
        statement = (
            select(SupportMessage)
            .where(SupportMessage.status == "open")
            .order_by(SupportMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def list_by_user(self, user_id: int, limit: int = 20) -> Sequence[SupportMessage]:
        """Return the most recent support messages from a specific user."""
        statement = (
            select(SupportMessage)
            .where(SupportMessage.user_id == user_id)
            .order_by(SupportMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()
