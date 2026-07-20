"""Referral System (V4.0): audit trail of every referral bonus granted."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ReferralReward(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single reward granted to a user for a referral milestone."""

    __tablename__ = "referral_rewards"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    reward_type: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ReferralReward(user_id={self.user_id!r}, reward_type={self.reward_type!r})"
