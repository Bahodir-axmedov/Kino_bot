"""Data-access operations for search analytics (#9, #10)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from src.models.search_log import SearchLog
from src.repositories.base import BaseRepository


class SearchLogRepository(BaseRepository[SearchLog]):
    """Repository encapsulating all SQL access for ``SearchLog`` rows."""

    model = SearchLog

    async def count_since(self, since: datetime, *, found: bool | None = None) -> int:
        """Count search attempts since ``since``, optionally filtered by ``found``."""
        statement = select(func.count(SearchLog.id)).where(SearchLog.created_at >= since)
        if found is not None:
            statement = statement.where(SearchLog.found.is_(found))
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def top_queries_since(
        self, since: datetime, *, found: bool | None = None, limit: int = 10
    ) -> Sequence[tuple[str, int]]:
        """Return the most frequent ``(query_text, count)`` pairs since ``since``."""
        statement = (
            select(SearchLog.query_text, func.count(SearchLog.id).label("hits"))
            .where(SearchLog.created_at >= since)
            .group_by(SearchLog.query_text)
            .order_by(func.count(SearchLog.id).desc())
            .limit(limit)
        )
        if found is not None:
            statement = statement.where(SearchLog.found.is_(found))
        result = await self._session.execute(statement)
        return [(row[0], row[1]) for row in result.all()]
