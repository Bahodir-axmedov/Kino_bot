"""Persistence for the Blacklist Center."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blacklist_entry import BlacklistEntry, BlacklistEntryType
from src.repositories.base import BaseRepository


class BlacklistRepository(BaseRepository[BlacklistEntry]):
    """CRUD and lookup helpers for :class:`BlacklistEntry`."""

    model = BlacklistEntry

    async def find(self, entry_type: BlacklistEntryType, value: str) -> BlacklistEntry | None:
        """Return the active blacklist row matching ``(entry_type, value)``, if any."""
        result = await self._session.execute(
            select(BlacklistEntry).where(
                BlacklistEntry.entry_type == entry_type,
                BlacklistEntry.value == value,
                BlacklistEntry.is_active.is_(True),
            )
        )
        return result.scalars().first()

    async def list_by_type(self, entry_type: BlacklistEntryType) -> list[BlacklistEntry]:
        """Return every entry of ``entry_type``, most recent first."""
        result = await self._session.execute(
            select(BlacklistEntry)
            .where(BlacklistEntry.entry_type == entry_type)
            .order_by(BlacklistEntry.id.desc())
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 200, offset: int = 0) -> list[BlacklistEntry]:
        """Return every blacklist entry, most recent first."""
        result = await self._session.execute(
            select(BlacklistEntry).order_by(BlacklistEntry.id.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
