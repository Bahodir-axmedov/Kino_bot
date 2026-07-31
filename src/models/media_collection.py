"""Curated, orderable Media Collections (V4.0) -- e.g. Marvel, DC, Anime, VIP.

Distinct from ``MediaSource.category`` (which groups *source chats* the bot
reads from) and from ``MovieCollectionType`` (which describes a *catalogue
entry kind* such as Season/Episode). A ``MediaCollection`` is an admin-curated
showcase shelf that individual ``Movie`` rows can be attached to.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class MediaCollection(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A named, orderable showcase collection (Marvel, DC, Netflix, VIP, ...)."""

    __tablename__ = "media_collections"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"MediaCollection(slug={self.slug!r}, name={self.name!r})"
