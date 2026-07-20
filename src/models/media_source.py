"""Telegram channels/groups the bot reads movie media from."""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class MediaSourceType(str, enum.Enum):
    """Kind of Telegram chat used as a media source."""

    CHANNEL = "channel"
    GROUP = "group"


class MediaSource(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A channel or group configured as a source of movie media."""

    __tablename__ = "media_sources"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[MediaSourceType] = mapped_column(
        SAEnum(MediaSourceType, name="media_source_type"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Multi Media Source (#1): free-text grouping label, e.g. "Marvel kinolari",
    # "Turk seriallari", "Anime", "VIP", "Premium". Admin can create any number
    # of named categories; this column is intentionally not an enum.
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"MediaSource(chat_id={self.chat_id!r}, title={self.title!r})"
