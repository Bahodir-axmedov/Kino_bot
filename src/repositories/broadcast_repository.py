"""Data-access operations for broadcast campaigns and their failures."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.broadcast import Broadcast, BroadcastFailedUser
from src.repositories.base import BaseRepository


class BroadcastRepository(BaseRepository[Broadcast]):
    """Repository encapsulating all SQL access for ``Broadcast`` rows."""

    model = Broadcast

    async def add_failed_user(
        self, broadcast_id: int, telegram_id: int, error_message: str
    ) -> BroadcastFailedUser:
        """Record a single failed delivery for a broadcast campaign."""
        failed_user = BroadcastFailedUser(
            broadcast_id=broadcast_id, telegram_id=telegram_id, error_message=error_message
        )
        self._session.add(failed_user)
        await self._session.flush()
        return failed_user

    async def list_failed_users(self, broadcast_id: int) -> Sequence[BroadcastFailedUser]:
        """Return every failed delivery recorded for a broadcast campaign."""
        statement = select(BroadcastFailedUser).where(
            BroadcastFailedUser.broadcast_id == broadcast_id
        )
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def list_recent(self, limit: int = 10) -> Sequence[Broadcast]:
        """Return the most recent broadcast campaigns, descending by id."""
        statement = select(Broadcast).order_by(Broadcast.id.desc()).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()
