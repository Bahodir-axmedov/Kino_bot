"""Persistence for Media Collections (Marvel, DC, VIP, ...)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.media_collection import MediaCollection
from src.repositories.base import BaseRepository


class MediaCollectionRepository(BaseRepository[MediaCollection]):
    """CRUD and ordering helpers for :class:`MediaCollection`."""

    model = MediaCollection

    async def get_by_slug(self, slug: str) -> MediaCollection | None:
        """Return the collection with the given unique ``slug``, if any."""
        result = await self._session.execute(select(MediaCollection).where(MediaCollection.slug == slug))
        return result.scalar_one_or_none()

    async def list_ordered(self, *, active_only: bool = False) -> list[MediaCollection]:
        """Return every collection ordered by admin-defined ``position``."""
        query = select(MediaCollection).order_by(MediaCollection.position, MediaCollection.id)
        if active_only:
            query = query.where(MediaCollection.is_active.is_(True))
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def max_position(self) -> int:
        """Return the highest ``position`` currently assigned (0 if none exist)."""
        collections = await self.list_ordered()
        return max((c.position for c in collections), default=-1) + 1
