"""Generic repository providing common, injection-safe CRUD operations.

Every query in this codebase goes through SQLAlchemy's expression language
with bound parameters. Raw/hardcoded SQL string concatenation is never used,
which is the primary defence against SQL injection.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic repository offering CRUD primitives for a single ORM model."""

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        """Store the unit-of-work session this repository will operate on."""
        self._session = session

    async def get_by_id(self, entity_id: object) -> ModelType | None:
        """Return the entity matching the given primary key, or ``None``."""
        return await self._session.get(self.model, entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelType]:
        """Return a page of entities ordered by insertion order."""
        statement = select(self.model).limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def add(self, entity: ModelType) -> ModelType:
        """Stage a new entity for insertion and flush to obtain its identity."""
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Stage an entity for deletion and flush immediately."""
        await self._session.delete(entity)
        await self._session.flush()

    async def flush(self) -> None:
        """Flush pending changes without committing the outer transaction."""
        await self._session.flush()
