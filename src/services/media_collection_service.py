"""Media Collections (V4.0): curated, orderable showcase shelves (Marvel, DC, ...)."""

from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.media_collection import MediaCollection
from src.repositories.media_collection_repository import MediaCollectionRepository
from src.utils.exceptions import InvalidInputError

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Derive a URL/callback-safe slug from a display name (e.g. ``"18+"`` -> ``"18"``)."""
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    if not slug:
        raise InvalidInputError("Collection nomidan slug yaratib bo'lmadi.")
    return slug


class MediaCollectionService:
    """Create, edit, delete, and reorder Media Collections."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = MediaCollectionRepository(session)

    async def list_collections(self, *, active_only: bool = False) -> list[MediaCollection]:
        """Return every collection ordered by admin-defined position."""
        return await self._repository.list_ordered(active_only=active_only)

    async def create(
        self, *, name: str, icon: str | None = None, description: str | None = None, created_by: int | None = None
    ) -> MediaCollection:
        """Create a new collection, appended to the end of the display order."""
        slug = slugify(name)
        if await self._repository.get_by_slug(slug) is not None:
            raise InvalidInputError(f"'{name}' nomli Collection allaqachon mavjud.")
        position = await self._repository.max_position()
        collection = MediaCollection(
            name=name.strip(), slug=slug, icon=icon, description=description, position=position, created_by=created_by
        )
        return await self._repository.add(collection)

    async def rename(self, collection_id: int, *, name: str) -> MediaCollection:
        """Rename an existing collection (slug is kept stable)."""
        collection = await self._repository.get_by_id(collection_id)
        if collection is None:
            raise InvalidInputError("Collection topilmadi.")
        collection.name = name.strip()
        await self._repository.flush()
        return collection

    async def set_active(self, collection_id: int, is_active: bool) -> MediaCollection:
        """Activate or deactivate a collection without deleting it."""
        collection = await self._repository.get_by_id(collection_id)
        if collection is None:
            raise InvalidInputError("Collection topilmadi.")
        collection.is_active = is_active
        await self._repository.flush()
        return collection

    async def delete(self, collection_id: int) -> None:
        """Permanently delete a collection."""
        collection = await self._repository.get_by_id(collection_id)
        if collection is None:
            raise InvalidInputError("Collection topilmadi.")
        await self._repository.delete(collection)

    async def reorder(self, ordered_collection_ids: list[int]) -> None:
        """Persist a new display order given the full list of collection IDs in order."""
        for position, collection_id in enumerate(ordered_collection_ids):
            collection = await self._repository.get_by_id(collection_id)
            if collection is not None:
                collection.position = position
        await self._repository.flush()

    async def move(self, collection_id: int, *, direction: str) -> None:
        """Move one collection up or down by swapping its position with its neighbor."""
        collections = await self._repository.list_ordered()
        index = next((i for i, c in enumerate(collections) if c.id == collection_id), None)
        if index is None:
            raise InvalidInputError("Collection topilmadi.")
        target = index - 1 if direction == "up" else index + 1
        if target < 0 or target >= len(collections):
            return
        collections[index].position, collections[target].position = (
            collections[target].position,
            collections[index].position,
        )
        await self._repository.flush()
