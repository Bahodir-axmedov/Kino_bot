"""Movie / media-index model -- the core catalogue entity of the bot."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class MediaType(str, enum.Enum):
    """Supported Telegram media kinds that a movie entry can wrap."""

    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    PHOTO = "photo"
    ANIMATION = "animation"


class MovieCollectionType(str, enum.Enum):
    """Media Collection (#2): what kind of catalogue entry this row is."""

    MOVIE = "movie"
    SERIAL = "serial"
    ANIME = "anime"
    SEASON = "season"
    EPISODE = "episode"
    PART = "part"
    TRAILER = "trailer"
    SHORT_VIDEO = "short_video"
    CLIP = "clip"


class MovieVisibility(str, enum.Enum):
    """Who is allowed to receive a movie once its code is requested.

    Enforced in ``MovieService``/handlers, not at the database layer, so the
    rule set can grow without a schema change.
    """

    PUBLIC = "public"
    HIDDEN = "hidden"
    VIP = "vip"
    PREMIUM = "premium"
    ADMIN_ONLY = "admin_only"
    SUBSCRIBER_ONLY = "subscriber_only"
    REFERRAL_ONLY = "referral_only"


class Movie(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single movie/series entry addressable by a short numeric-friendly code.

    The bot never re-uploads media: ``telegram_file_id`` is the Telegram-issued
    file identifier captured once when the media was indexed, and is reused
    for every future delivery via ``copy_message``/``send_<media_type>`` calls
    -- no bytes are ever downloaded/re-uploaded through the bot process.
    """

    __tablename__ = "movies"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Indexed: duplicate-file lookups and broken-file audits filter by this
    # column, and it must stay a fast equality lookup even with a large catalogue.
    telegram_file_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # The chat/message the file was originally captured from. Needed so the
    # bot can re-verify (get_file) or re-fetch a fresh file_id if Telegram
    # ever invalidates the cached one (file ids can expire on the source
    # message being deleted).
    source_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    media_type: Mapped[MediaType] = mapped_column(SAEnum(MediaType, name="media_type"), nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    genre: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    language: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    views_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    downloads_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # NOTE: intentionally NOT a ForeignKey. The source chat is only a hint used
    # for optional copy_message re-verification -- media can legitimately be
    # captured from an unregistered group or uploaded directly to the bot (a
    # private chat), neither of which exists in ``media_sources``. Enforcing a
    # FK here caused every such insert to fail with "FOREIGN KEY constraint
    # failed". A plain nullable column keeps indexing robust for all sources.
    source_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    visibility: Mapped[MovieVisibility] = mapped_column(
        SAEnum(MovieVisibility, name="movie_visibility"),
        nullable=False,
        default=MovieVisibility.PUBLIC,
        server_default=MovieVisibility.PUBLIC.value,
    )
    is_broken: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Multi Media Source / Media Collection (#1, #2) ---------------------
    collection_type: Mapped[MovieCollectionType] = mapped_column(
        SAEnum(MovieCollectionType, name="movie_collection_type"),
        nullable=False,
        default=MovieCollectionType.MOVIE,
        server_default=MovieCollectionType.MOVIE.value,
    )
    series_title: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    part_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Avtomatik indekslash (#3): auto-captured technical metadata --------
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    thumbnail_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Search (#16): actor/director filters -------------------------------
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    director: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # --- Media Collections (V4.0): curated showcase shelf, e.g. Marvel/DC ---
    collection_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("media_collections.id", ondelete="SET NULL"), nullable=True, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"Movie(code={self.code!r}, title={self.title!r})"
