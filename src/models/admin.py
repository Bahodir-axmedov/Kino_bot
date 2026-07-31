"""Administrator accounts and their role-based access control level."""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AdminRole(str, enum.Enum):
    """Hierarchical roles used for role-based access control (RBAC)."""

    OWNER = "owner"
    ADMIN = "admin"
    MODERATOR = "moderator"
    DEVELOPER = "developer"
    UPLOADER = "uploader"
    SUPPORT = "support"
    ANALYST = "analyst"
    BACKUP_MANAGER = "backup_manager"
    CONTENT_MANAGER = "content_manager"


class AdminUser(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """An administrator with elevated permissions inside the bot."""

    __tablename__ = "admin_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    role: Mapped[AdminRole] = mapped_column(
        SAEnum(AdminRole, name="admin_role"), nullable=False, default=AdminRole.MODERATOR
    )
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- Admin Login Protection (V4.0): PIN + optional TOTP 2FA ------------
    login_pin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    two_factor_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AdminUser(telegram_id={self.telegram_id!r}, role={self.role!r})"
