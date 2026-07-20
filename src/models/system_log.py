"""Log Center (V4.0): structured, queryable application log entries.

This complements (does not replace) ``structlog`` file/stdout logging: those
logs are for operators tailing files, while ``SystemLog`` rows are for the
in-bot admin Log Center screen (filter by level/category, search, paginate).
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class LogLevel(str, enum.Enum):
    """Severity of a log entry."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(str, enum.Enum):
    """Subsystem a log entry belongs to."""

    SYSTEM = "system"
    SECURITY = "security"
    DATABASE = "database"
    MEDIA = "media"
    ADMIN = "admin"
    USER = "user"
    SCHEDULER = "scheduler"
    BACKUP = "backup"


class SystemLog(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single structured log row shown in the admin Log Center."""

    __tablename__ = "system_logs"

    level: Mapped[LogLevel] = mapped_column(SAEnum(LogLevel, name="log_level"), nullable=False, index=True)
    category: Mapped[LogCategory] = mapped_column(
        SAEnum(LogCategory, name="log_category"), nullable=False, index=True
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    exception: Mapped[str | None] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"SystemLog(level={self.level!r}, category={self.category!r}, action={self.action!r})"
