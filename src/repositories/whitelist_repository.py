"""Persistence for the Whitelist Center."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.whitelist_entry import WhitelistEntry, WhitelistEntryType
from src.repositories.base import BaseRepository


class WhitelistRepository(BaseRepository[WhitelistEntry]):
    """CRUD and lookup helpers for :class:`WhitelistEntry`."""

    model = WhitelistEntry

    async def find(self, entry_type: WhitelistEntryType, value: str) -> WhitelistEntry | None:
        """Return the whitelist row matching ``(entry_type, value)``, if any."""
        result = await self._session.execute(
            select(WhitelistEntry).where(
                WhitelistEntry.entry_type == entry_type,
                WhitelistEntry.value == value,
            )
        )
        return result.scalars().first()

    async def list_by_type(self, entry_type: WhitelistEntryType) -> list[WhitelistEntry]:
        """Return every entry of ``entry_type``, most recent first."""
        result = await self._session.execute(
            select(WhitelistEntry)
            .where(WhitelistEntry.entry_type == entry_type)
            .order_by(WhitelistEntry.id.desc())
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 200, offset: int = 0) -> list[WhitelistEntry]:
        """Return every whitelist entry, most recent first."""
        result = await self._session.execute(
            select(WhitelistEntry).order_by(WhitelistEntry.id.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
