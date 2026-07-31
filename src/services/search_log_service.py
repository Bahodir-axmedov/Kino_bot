"""Search analytics service -- Kino statistikasi (#9) and Empty Search (#10)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.search_log import SearchLog
from src.repositories.search_log_repository import SearchLogRepository

_PERIODS: dict[str, timedelta] = {
    "today": timedelta(days=1),
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "year": timedelta(days=365),
}


class SearchLogService:
    """Records every code/title search and reports on it."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = SearchLogRepository(session)

    async def record(
        self,
        *,
        query_text: str,
        found: bool,
        user_id: int | None,
        query_type: str = "code",
        platform: str = "bot",
    ) -> SearchLog:
        """Persist a single search attempt (#9: statistika, #10: empty search)."""
        entry = SearchLog(
            query_text=query_text.strip(),
            found=found,
            user_id=user_id,
            query_type=query_type,
            platform=platform,
        )
        return await self._repository.add(entry)

    async def period_summary(self, period: str) -> dict[str, int | list[tuple[str, int]]]:
        """Return counts + top queries for one of today/week/month/year (#9)."""
        delta = _PERIODS.get(period, _PERIODS["today"])
        since = datetime.now(timezone.utc) - delta
        total = await self._repository.count_since(since)
        found = await self._repository.count_since(since, found=True)
        missed = await self._repository.count_since(since, found=False)
        top_found = await self._repository.top_queries_since(since, found=True, limit=10)
        top_missing = await self._repository.top_queries_since(since, found=False, limit=10)
        return {
            "total": total,
            "found": found,
            "missed": missed,
            "top_found": top_found,
            "top_missing": top_missing,
        }

    async def top_missing_codes(self, limit: int = 10) -> list[tuple[str, int]]:
        """Return the most frequently searched-but-never-found codes (#10)."""
        since = datetime.now(timezone.utc) - timedelta(days=365)
        return list(await self._repository.top_queries_since(since, found=False, limit=limit))
