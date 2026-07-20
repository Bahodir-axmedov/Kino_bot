"""Channels/pages users must subscribe to/confirm before receiving media.

This is the "majburiy obuna markazi": a mandatory-subscription center that
supports both Telegram entities (auto-verified via ``get_chat_member``) and
non-Telegram platforms (verified only via a manual "Tasdiqlash" confirmation,
since the bot has no API access to those platforms' membership).
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ForceSubPlatform(str, enum.Enum):
    """Every subscription-source kind the force-sub center can manage."""

    TELEGRAM_CHANNEL = "telegram_channel"
    TELEGRAM_GROUP = "telegram_group"
    TELEGRAM_DISCUSSION_GROUP = "telegram_discussion_group"
    TELEGRAM_BOT = "telegram_bot"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    TWITTER_X = "twitter_x"
    WEBSITE = "website"


# Platforms Telegram's Bot API can auto-verify membership for via
# get_chat_member. Every other platform requires a manual "Tasdiqlash" tap.
TELEGRAM_AUTO_VERIFIABLE_PLATFORMS = frozenset(
    {
        ForceSubPlatform.TELEGRAM_CHANNEL,
        ForceSubPlatform.TELEGRAM_GROUP,
        ForceSubPlatform.TELEGRAM_DISCUSSION_GROUP,
    }
)


class ForceSubChannel(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single mandatory or optional subscription target."""

    __tablename__ = "force_sub_channels"

    platform: Mapped[ForceSubPlatform] = mapped_column(
        SAEnum(ForceSubPlatform, name="force_sub_platform"),
        nullable=False,
        default=ForceSubPlatform.TELEGRAM_CHANNEL,
        server_default=ForceSubPlatform.TELEGRAM_CHANNEL.value,
    )
    # Only populated (and only meaningful) for Telegram platforms -- this is
    # what get_chat_member is called with. Nullable because non-Telegram
    # platforms have no chat id.
    chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    chat_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The public link/URL shown to the user: Telegram invite link, or the
    # Instagram/YouTube/TikTok/Facebook/X/website URL for non-Telegram platforms.
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(512), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    @property
    def is_telegram_auto_verifiable(self) -> bool:
        """True if the bot can verify this via get_chat_member (no manual confirm needed)."""
        return self.platform in TELEGRAM_AUTO_VERIFIABLE_PLATFORMS

    def __repr__(self) -> str:  # pragma: no cover
        return f"ForceSubChannel(platform={self.platform!r}, title={self.title!r})"
