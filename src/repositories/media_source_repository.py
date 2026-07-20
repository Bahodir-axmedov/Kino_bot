"""Data-access operations for configured media source channels/groups."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.media_source import MediaSource
from src.repositories.base import BaseRepository


class MediaSourceRepository(BaseRepository[MediaSource]):
    """Repository encapsulating all SQL access for ``MediaSource`` rows."""

    model = MediaSource

    async def get_by_chat_id(self, chat_id: int) -> MediaSource | None:
        """Return the media source for ``chat_id``, or ``None``."""
        statement = select(MediaSource).where(MediaSource.chat_id == chat_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_active_by_priority(self) -> Sequence[MediaSource]:
        """Return active media sources ordered by descending priority."""
        statement = (
            select(MediaSource)
            .where(MediaSource.is_active.is_(True))
            .order_by(MediaSource.priority.desc())
        )
        result = await self._session.execute(statement)
        return result.scalars().all()
