"""Blacklist Center (V4.0): block users, media, words, codes, or countries.

Each entry is a (type, value) pair. Enforcement lives in
``BlacklistService``/``BlacklistMiddleware``, not here -- this module is
intentionally a pure data model so the rule set can grow without further
schema changes.
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class BlacklistEntryType(str, enum.Enum):
    """Every kind of value the Blacklist Center can block."""

    TELEGRAM_ID = "telegram_id"
    USERNAME = "username"
    PHONE = "phone"
    MEDIA = "media"
    CAPTION = "caption"
    CODE = "code"
    WORD = "word"
    REFERRAL = "referral"
    COUNTRY = "country"
    SPAM_USER = "spam_user"


class BlacklistEntry(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single blocked value of a given type."""

    __tablename__ = "blacklist_entries"

    entry_type: Mapped[BlacklistEntryType] = mapped_column(
        SAEnum(BlacklistEntryType, name="blacklist_entry_type"), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"BlacklistEntry(type={self.entry_type!r}, value={self.value!r})"
