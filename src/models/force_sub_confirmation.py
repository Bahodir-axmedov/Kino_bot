"""Manual "Tasdiqlash" confirmations for non-Telegram force-sub platforms.

Instagram/YouTube/TikTok/Facebook/X/Website subscriptions cannot be verified
programmatically, so a user's tap on "Tasdiqlash" is the only signal the bot
has. One row per (user, channel) pair.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ForceSubConfirmation(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """Records that a user claimed to have completed a non-Telegram subscription."""

    __tablename__ = "force_sub_confirmations"
    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_force_sub_confirmation_user_channel"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("force_sub_channels.id", ondelete="CASCADE"), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"ForceSubConfirmation(user_id={self.user_id!r}, channel_id={self.channel_id!r})"
