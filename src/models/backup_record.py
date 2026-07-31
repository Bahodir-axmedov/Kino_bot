"""Automatic Backup (V4.0): DB-tracked metadata for every backup file.

``BackupService`` still owns the actual file copy on disk; this model gives
the admin panel queryable metadata (checksum, integrity, size) instead of
having to stat the filesystem on every Backup Center page load.
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class BackupFrequency(str, enum.Enum):
    """How often automatic backups should be taken."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class BackupIntegrityStatus(str, enum.Enum):
    """Result of the last integrity verification for a backup file."""

    OK = "ok"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


class BackupRecord(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """Metadata row describing one on-disk backup file."""

    __tablename__ = "backup_records"

    filename: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    integrity_status: Mapped[BackupIntegrityStatus] = mapped_column(
        SAEnum(BackupIntegrityStatus, name="backup_integrity_status"),
        nullable=False,
        default=BackupIntegrityStatus.UNKNOWN,
        server_default=BackupIntegrityStatus.UNKNOWN.value,
    )
    frequency: Mapped[BackupFrequency | None] = mapped_column(
        SAEnum(BackupFrequency, name="backup_frequency"), nullable=True
    )
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"BackupRecord(filename={self.filename!r}, integrity_status={self.integrity_status!r})"
