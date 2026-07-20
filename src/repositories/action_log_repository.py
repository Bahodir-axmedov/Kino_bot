"""Data-access operations for the audit trail (``ActionLog``)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.action_log import ActionLog
from src.repositories.base import BaseRepository


class ActionLogRepository(BaseRepository[ActionLog]):
    """Repository encapsulating all SQL access for ``ActionLog`` rows."""

    model = ActionLog

    async def list_recent(self, limit: int = 50) -> Sequence[ActionLog]:
        """Return the most recent audit log entries, descending by id."""
        statement = select(ActionLog).order_by(ActionLog.id.desc()).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def list_by_actor(self, actor_id: int, limit: int = 50) -> Sequence[ActionLog]:
        """Return the most recent audit log entries created by a given actor."""
        statement = (
            select(ActionLog)
            .where(ActionLog.actor_id == actor_id)
            .order_by(ActionLog.id.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()
