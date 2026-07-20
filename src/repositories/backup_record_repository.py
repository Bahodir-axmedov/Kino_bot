"""Persistence for Automatic Backup metadata rows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.backup_record import BackupRecord
from src.repositories.base import BaseRepository


class BackupRecordRepository(BaseRepository[BackupRecord]):
    """CRUD helpers for :class:`BackupRecord`."""

    model = BackupRecord

    async def get_by_filename(self, filename: str) -> BackupRecord | None:
        """Return the metadata row for ``filename``, if any."""
        result = await self._session.execute(select(BackupRecord).where(BackupRecord.filename == filename))
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[BackupRecord]:
        """Return every backup record, most recent first."""
        result = await self._session.execute(
            select(BackupRecord).order_by(BackupRecord.id.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
