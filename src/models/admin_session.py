"""Admin Login Protection (V4.0): failed-attempt lockout, sessions, 2FA secret.

Telegram already authenticates *who* is talking (the Telegram account), so
this is a *second* factor guarding the admin panel itself: a short numeric
PIN (and optionally TOTP 2FA) an admin must additionally confirm, plus
brute-force lockout and revocable sessions, in case an admin's Telegram
account is ever compromised.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AdminLoginAttempt(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single admin-panel PIN/2FA verification attempt, used for lockout."""

    __tablename__ = "admin_login_attempts"

    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AdminLoginAttempt(admin_telegram_id={self.admin_telegram_id!r}, success={self.success!r})"


class AdminSession(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """An active, revocable admin-panel session issued after PIN/2FA success."""

    __tablename__ = "admin_sessions"

    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:
        """True when this session has not been revoked (expiry is checked by the caller)."""
        return self.revoked_at is None

    def __repr__(self) -> str:  # pragma: no cover
        return f"AdminSession(admin_telegram_id={self.admin_telegram_id!r})"
