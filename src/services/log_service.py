"""Audit logging service -- records who did what, to what, and what changed."""

from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.action_log import ActionLog
from src.repositories.action_log_repository import ActionLogRepository

logger = structlog.get_logger(__name__)


class LogService:
    """Writes structured audit entries to both the DB and the log stream."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = ActionLogRepository(session)

    async def record(
        self,
        *,
        actor_id: int,
        actor_role: str,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        ip_address: str | None = None,
    ) -> ActionLog:
        """Persist a single audit entry and mirror it to structured logs."""
        entry = ActionLog(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_value=_safe_json(old_value),
            new_value=_safe_json(new_value),
            ip_address=ip_address,
        )
        await self._repository.add(entry)
        logger.info(
            "audit.action",
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return entry

    async def list_recent(self, limit: int = 50) -> list[ActionLog]:
        """Return the most recent audit entries."""
        return list(await self._repository.list_recent(limit=limit))


def _safe_json(value: Any) -> str | None:
    """Best-effort JSON serialization for audit payloads; never raises."""
    if value is None:
        return None
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):  # pragma: no cover - defensive fallback
        return str(value)
