"""Whitelist Center (V4.0): exempt users/admins/channels/groups/roles from limits."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.whitelist_entry import WhitelistEntry, WhitelistEntryType
from src.repositories.whitelist_repository import WhitelistRepository
from src.utils.exceptions import InvalidInputError


class WhitelistService:
    """Create, list, and check Whitelist Center entries."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = WhitelistRepository(session)

    async def add(
        self, entry_type: WhitelistEntryType, value: str, *, note: str | None = None, created_by: int | None = None
    ) -> WhitelistEntry:
        """Exempt a new value from restrictions."""
        if await self._repository.find(entry_type, value) is not None:
            raise InvalidInputError("Bu qiymat allaqachon whitelistda.")
        entry = WhitelistEntry(entry_type=entry_type, value=value.strip(), note=note, created_by=created_by)
        return await self._repository.add(entry)

    async def remove(self, entry_id: int) -> None:
        """Permanently remove a whitelist entry."""
        entry = await self._repository.get_by_id(entry_id)
        if entry is None:
            raise InvalidInputError("Whitelist yozuvi topilmadi.")
        await self._repository.delete(entry)

    async def list_by_type(self, entry_type: WhitelistEntryType) -> list[WhitelistEntry]:
        """Return every entry of a given type."""
        return await self._repository.list_by_type(entry_type)

    async def list_all(self) -> list[WhitelistEntry]:
        """Return every whitelist entry across all types."""
        return await self._repository.list_all()

    async def is_whitelisted(self, entry_type: WhitelistEntryType, value: str) -> bool:
        """Return True when ``value`` is exempted under ``entry_type``."""
        return await self._repository.find(entry_type, value) is not None

    async def is_user_whitelisted(self, *, telegram_id: int) -> bool:
        """Convenience check for the User whitelist type."""
        return await self.is_whitelisted(WhitelistEntryType.USER, str(telegram_id))
