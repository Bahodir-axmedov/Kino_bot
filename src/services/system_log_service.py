"""Log Center (V4.0): structured, queryable log entries for the admin panel."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.system_log import LogCategory, LogLevel, SystemLog
from src.repositories.system_log_repository import SystemLogRepository


class SystemLogService:
    """Writes and queries the structured Log Center entries."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = SystemLogRepository(session)

    async def log(
        self,
        *,
        level: LogLevel,
        category: LogCategory,
        action: str,
        module: str,
        description: str,
        user_id: int | None = None,
        admin_id: int | None = None,
        exception: str | None = None,
        stack_trace: str | None = None,
    ) -> SystemLog:
        """Persist one structured log row for the admin Log Center."""
        entry = SystemLog(
            level=level,
            category=category,
            action=action,
            module=module,
            description=description,
            user_id=user_id,
            admin_id=admin_id,
            exception=exception,
            stack_trace=stack_trace,
        )
        return await self._repository.add(entry)

    async def list_filtered(
        self,
        *,
        level: LogLevel | None = None,
        category: LogCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SystemLog]:
        """Return log rows filtered by level/category, newest first."""
        return await self._repository.list_filtered(level=level, category=category, limit=limit, offset=offset)
