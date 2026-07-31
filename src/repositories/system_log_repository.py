"""Persistence for the structured Log Center."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.system_log import LogCategory, LogLevel, SystemLog
from src.repositories.base import BaseRepository


class SystemLogRepository(BaseRepository[SystemLog]):
    """Filtering and pagination helpers for :class:`SystemLog`."""

    model = SystemLog

    async def list_filtered(
        self,
        *,
        level: LogLevel | None = None,
        category: LogCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SystemLog]:
        """Return log rows filtered by level/category, newest first."""
        query = select(SystemLog)
        if level is not None:
            query = query.where(SystemLog.level == level)
        if category is not None:
            query = query.where(SystemLog.category == category)
        query = query.order_by(SystemLog.id.desc()).limit(limit).offset(offset)
        result = await self._session.execute(query)
        return list(result.scalars().all())
