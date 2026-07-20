"""Blacklist Center (V4.0): block users, media, words, codes, countries, etc."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blacklist_entry import BlacklistEntry, BlacklistEntryType
from src.repositories.blacklist_repository import BlacklistRepository
from src.utils.exceptions import InvalidInputError


class BlacklistService:
    """Create, list, and check Blacklist Center entries."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = BlacklistRepository(session)

    async def add(
        self, entry_type: BlacklistEntryType, value: str, *, reason: str | None = None, created_by: int | None = None
    ) -> BlacklistEntry:
        """Block a new value; reactivates an existing inactive entry instead of duplicating."""
        existing = await self._repository.find(entry_type, value)
        if existing is not None:
            raise InvalidInputError("Bu qiymat allaqachon blacklistda.")
        entry = BlacklistEntry(entry_type=entry_type, value=value.strip(), reason=reason, created_by=created_by)
        return await self._repository.add(entry)

    async def remove(self, entry_id: int) -> None:
        """Deactivate a blacklist entry (soft delete, preserves audit history)."""
        entry = await self._repository.get_by_id(entry_id)
        if entry is None:
            raise InvalidInputError("Blacklist yozuvi topilmadi.")
        entry.is_active = False
        await self._repository.flush()

    async def list_by_type(self, entry_type: BlacklistEntryType) -> list[BlacklistEntry]:
        """Return every entry of a given type (active and inactive)."""
        return await self._repository.list_by_type(entry_type)

    async def list_all(self) -> list[BlacklistEntry]:
        """Return every blacklist entry across all types."""
        return await self._repository.list_all()

    async def is_blocked(self, entry_type: BlacklistEntryType, value: str) -> bool:
        """Return True when ``value`` is actively blacklisted under ``entry_type``."""
        return await self._repository.find(entry_type, value) is not None

    async def is_user_blocked(self, *, telegram_id: int, username: str | None = None) -> bool:
        """Convenience check combining Telegram ID and username blacklist rules."""
        if await self.is_blocked(BlacklistEntryType.TELEGRAM_ID, str(telegram_id)):
            return True
        if username and await self.is_blocked(BlacklistEntryType.USERNAME, username.lstrip("@").lower()):
            return True
        return False

    async def contains_blacklisted_word(self, text: str) -> bool:
        """Return True when any active blacklisted word/phrase appears in ``text``."""
        if not text:
            return False
        lowered = text.lower()
        for entry in await self.list_by_type(BlacklistEntryType.WORD):
            if entry.is_active and entry.value.lower() in lowered:
                return True
        return False
