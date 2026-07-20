"""Database Manager (V4.0): live SQLite health/optimization for the admin panel.

Uses raw ``PRAGMA`` statements against the bound session's connection --
these are SQLite-specific by design, matching the project's SQLite-first
deployment target described in the settings module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings


@dataclass(frozen=True, slots=True)
class DatabaseHealthSnapshot:
    """Everything shown on the admin Database Manager screen."""

    table_count: int
    index_count: int
    total_rows: int
    database_size_mb: float
    fragmentation_percent: float
    integrity_ok: bool
    broken_indexes: list[str]
    slow_query_count: int


class DatabaseManagerService:
    """Reports on and optimizes the live SQLite database file."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        """Bind this service to a unit-of-work session and the app settings."""
        self._session = session
        self._settings = settings

    def _database_path(self) -> str:
        """Resolve the on-disk SQLite file path from ``DATABASE_URL``."""
        return self._settings.database_url.split("///")[-1]

    async def _scalar(self, sql: str) -> object:
        """Execute a raw scalar-returning SQL/PRAGMA statement."""
        result = await self._session.execute(text(sql))
        return result.scalar()

    async def table_names(self) -> list[str]:
        """Return every user table name in the database."""
        result = await self._session.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
        )
        return [row[0] for row in result.all()]

    async def index_names(self) -> list[str]:
        """Return every user-defined index name in the database."""
        result = await self._session.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'")
        )
        return [row[0] for row in result.all()]

    async def total_row_count(self) -> int:
        """Return the sum of row counts across every user table."""
        total = 0
        for table in await self.table_names():
            count = await self._scalar(f'SELECT count(*) FROM "{table}"')
            total += int(count or 0)
        return total

    async def integrity_check(self) -> bool:
        """Run ``PRAGMA integrity_check`` and return True only if it reports "ok"."""
        value = await self._scalar("PRAGMA integrity_check")
        return str(value).lower() == "ok"

    async def check_broken_indexes(self) -> list[str]:
        """Return the names of any indexes that fail SQLite's own consistency check.

        Uses ``PRAGMA integrity_check`` first (covers all indexes at once); if it
        reports anything other than "ok", every index is treated as suspect
        since SQLite's PRAGMA does not name the specific broken structure.
        """
        if await self.integrity_check():
            return []
        return await self.index_names()

    async def fragmentation_percent(self) -> float:
        """Estimate fragmentation as the share of free pages in the file."""
        page_count = int(await self._scalar("PRAGMA page_count") or 1)
        freelist_count = int(await self._scalar("PRAGMA freelist_count") or 0)
        if page_count == 0:
            return 0.0
        return round((freelist_count / page_count) * 100, 2)

    def database_size_mb(self) -> float:
        """Return the current on-disk file size in MB (0 for non-SQLite backends)."""
        try:
            return round(os.path.getsize(self._database_path()) / (1024 * 1024), 2)
        except OSError:
            return 0.0

    async def build_snapshot(self, *, slow_query_count: int = 0) -> DatabaseHealthSnapshot:
        """Compute the full Database Manager snapshot shown in the admin panel."""
        tables = await self.table_names()
        indexes = await self.index_names()
        integrity_ok = await self.integrity_check()
        return DatabaseHealthSnapshot(
            table_count=len(tables),
            index_count=len(indexes),
            total_rows=await self.total_row_count(),
            database_size_mb=self.database_size_mb(),
            fragmentation_percent=await self.fragmentation_percent(),
            integrity_ok=integrity_ok,
            broken_indexes=[] if integrity_ok else indexes,
            slow_query_count=slow_query_count,
        )

    async def vacuum(self) -> None:
        """Reclaim free space and defragment the database file."""
        await self._session.execute(text("VACUUM"))

    async def analyze(self) -> None:
        """Refresh the query planner statistics used for index selection."""
        await self._session.execute(text("ANALYZE"))

    async def reindex(self) -> None:
        """Rebuild every index in the database."""
        await self._session.execute(text("REINDEX"))

    async def optimize(self) -> DatabaseHealthSnapshot:
        """Run the full VACUUM -> ANALYZE -> REINDEX -> integrity check pipeline.

        This is what both the "Optimize" button in the Database Manager and
        the nightly Database Optimization scheduler job call.
        """
        await self.vacuum()
        await self.analyze()
        await self.reindex()
        return await self.build_snapshot()
