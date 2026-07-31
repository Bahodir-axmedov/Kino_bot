"""Premium System (V4.0): audit trail of every premium grant/extension."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class PremiumHistory(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single premium grant/extension/revocation event for a user."""

    __tablename__ = "premium_history"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    granted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    plan: Mapped[str] = mapped_column(String(64), nullable=False, default="premium")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"PremiumHistory(user_id={self.user_id!r}, plan={self.plan!r})"
