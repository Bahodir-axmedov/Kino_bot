"""Persistence for Admin Login Protection: attempts and sessions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin_session import AdminLoginAttempt, AdminSession
from src.repositories.base import BaseRepository


class AdminLoginAttemptRepository(BaseRepository[AdminLoginAttempt]):
    """Read/write helpers for :class:`AdminLoginAttempt` rows."""

    model = AdminLoginAttempt

    async def recent_failed_count(self, admin_telegram_id: int, since: datetime) -> int:
        """Count failed attempts by ``admin_telegram_id`` at or after ``since``."""
        result = await self._session.execute(
            select(AdminLoginAttempt).where(
                AdminLoginAttempt.admin_telegram_id == admin_telegram_id,
                AdminLoginAttempt.success.is_(False),
                AdminLoginAttempt.created_at >= since,
            )
        )
        return len(result.scalars().all())


class AdminSessionRepository(BaseRepository[AdminSession]):
    """Read/write helpers for :class:`AdminSession` rows."""

    model = AdminSession

    async def get_by_token(self, session_token: str) -> AdminSession | None:
        """Return the session row for ``session_token``, if any."""
        result = await self._session.execute(
            select(AdminSession).where(AdminSession.session_token == session_token)
        )
        return result.scalar_one_or_none()

    async def list_active(self, admin_telegram_id: int) -> list[AdminSession]:
        """Return every non-revoked, non-expired session for one admin."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(AdminSession).where(
                AdminSession.admin_telegram_id == admin_telegram_id,
                AdminSession.revoked_at.is_(None),
                AdminSession.expires_at > now,
            )
        )
        return list(result.scalars().all())

    async def revoke_all(self, admin_telegram_id: int) -> int:
        """Revoke every active session for one admin ("Logout All"). Returns count revoked."""
        sessions = await self.list_active(admin_telegram_id)
        now = datetime.now(timezone.utc)
        for session in sessions:
            session.revoked_at = now
        await self.flush()
        return len(sessions)
