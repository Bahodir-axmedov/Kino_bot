"""Advertisement Center (V4.0): admin-created ads shown every N searches."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class AdContentType(str, enum.Enum):
    """Kind of media an advertisement is made of."""

    TEXT = "text"
    PHOTO = "photo"
    VIDEO = "video"
    GIF = "gif"


class AdCampaign(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single advertisement creative and its scheduling/trigger rules."""

    __tablename__ = "ad_campaigns"

    content_type: Mapped[AdContentType] = mapped_column(
        SAEnum(AdContentType, name="ad_content_type"), nullable=False, default=AdContentType.TEXT
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    button_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    button_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    schedule_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    trigger_every_n_searches: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    impressions_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"AdCampaign(id={self.id!r}, content_type={self.content_type!r})"
