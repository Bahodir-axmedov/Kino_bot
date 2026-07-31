"""End-user model -- every Telegram account that has interacted with the bot."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """A Telegram end-user known to the bot.

    The primary key is the Telegram user id itself (not a surrogate key)
    because it is already a stable, unique, natural identifier and avoids an
    extra join on the hottest code path (movie code lookup -> user lookup).
    """

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False, default="uz")

    is_banned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    premium_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    referred_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="SET NULL"), nullable=True
    )
    invite_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    movies_received_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    searches_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- User-history / trust-signal fields -------------------------------
    start_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spam_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Telegram's Bot API never exposes device/OS info about a user; this only
    # stores a best-effort client hint (e.g. "telegram-desktop" vs "mobile")
    # when it can be inferred (client type is NOT reliably available and is
    # usually left NULL -- documented here rather than faked).
    last_known_client_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=__import__("sqlalchemy").func.now()
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    referrer: Mapped["User | None"] = relationship(
        "User", remote_side="User.telegram_id", foreign_keys=[referred_by]
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper only
        return f"User(telegram_id={self.telegram_id!r}, username={self.username!r})"
