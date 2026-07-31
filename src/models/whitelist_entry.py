"""Whitelist Center (V4.0): exempt users/admins/channels/groups/roles from limits.

A whitelist match always overrides a blacklist match or a generic limit
(rate limit, maintenance mode, force-subscribe) -- see ``WhitelistService``.
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class WhitelistEntryType(str, enum.Enum):
    """Every kind of value the Whitelist Center can exempt."""

    USER = "user"
    ADMIN = "admin"
    CHANNEL = "channel"
    GROUP = "group"
    ROLE = "role"


class WhitelistEntry(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single exempted value of a given type."""

    __tablename__ = "whitelist_entries"

    entry_type: Mapped[WhitelistEntryType] = mapped_column(
        SAEnum(WhitelistEntryType, name="whitelist_entry_type"), nullable=False, index=True
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"WhitelistEntry(type={self.entry_type!r}, value={self.value!r})"
