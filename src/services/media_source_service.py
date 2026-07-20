"""Management of Telegram channels/groups used as movie media sources."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.media_source import MediaSource, MediaSourceType
from src.repositories.media_source_repository import MediaSourceRepository


class MediaSourceService:
    """Encapsulates every business rule about configured media sources."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = MediaSourceRepository(session)

    async def add_source(
        self,
        *,
        chat_id: int,
        title: str,
        source_type: MediaSourceType,
        priority: int = 0,
        category: str | None = None,
    ) -> MediaSource:
        """Register a new media source, or reactivate/update an existing one.

        ``category`` implements Multi Media Source (#1): an admin-defined free
        text label ("Marvel kinolari", "Anime", "VIP", ...) grouping any
        number of sources. Passing ``None`` leaves an existing category as-is.
        """
        existing = await self._repository.get_by_chat_id(chat_id)
        if existing is not None:
            existing.title = title
            existing.type = source_type
            existing.priority = priority
            existing.is_active = True
            if category is not None:
                existing.category = category
            await self._repository.flush()
            return existing
        source = MediaSource(
            chat_id=chat_id,
            title=title,
            type=source_type,
            priority=priority,
            is_active=True,
            category=category,
        )
        return await self._repository.add(source)

    async def set_category(self, chat_id: int, category: str | None) -> MediaSource | None:
        """Assign/clear the category label of an existing media source."""
        source = await self._repository.get_by_chat_id(chat_id)
        if source is None:
            return None
        source.category = category
        await self._repository.flush()
        return source

    async def list_categories(self) -> list[str]:
        """Return every distinct, non-empty category label currently in use."""
        sources = await self._repository.list_active_by_priority()
        return sorted({source.category for source in sources if source.category})

    async def list_by_category(self, category: str) -> list[MediaSource]:
        """Return active media sources belonging to a given category."""
        sources = await self._repository.list_active_by_priority()
        return [source for source in sources if source.category == category]

    async def remove_source(self, chat_id: int) -> bool:
        """Deactivate a media source. Returns ``False`` if not found."""
        source = await self._repository.get_by_chat_id(chat_id)
        if source is None:
            return False
        source.is_active = False
        await self._repository.flush()
        return True

    async def set_priority(self, chat_id: int, priority: int) -> MediaSource | None:
        """Update the priority of a media source."""
        source = await self._repository.get_by_chat_id(chat_id)
        if source is None:
            return None
        source.priority = priority
        await self._repository.flush()
        return source

    async def list_active(self) -> list[MediaSource]:
        """Return all active media sources ordered by priority."""
        return list(await self._repository.list_active_by_priority())
