"""Chats (channels/groups) the bot has been added to.

Powers a zero-typing admin UX: instead of asking an admin to type a
@username or numeric chat id anywhere, the bot listens for ``my_chat_member``
updates (see :mod:`src.handlers.admin.chat_discovery`) and records every
channel/group it is added to here. The admin panel then offers a simple
tap-to-pick list built from this table for Force Subscribe and Media
Sources.
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class DiscoveredChatType(str, enum.Enum):
    """Coarse kind of a discovered Telegram chat."""

    CHANNEL = "channel"
    GROUP = "group"


class DiscoveredChatStatus(str, enum.Enum):
    """The bot's own membership status in the chat, per ``my_chat_member``."""

    ADMINISTRATOR = "administrator"
    MEMBER = "member"
    LEFT = "left"
    KICKED = "kicked"


class DiscoveredChat(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A channel/group the bot currently is (or previously was) a member of."""

    __tablename__ = "discovered_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    chat_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    chat_type: Mapped[DiscoveredChatType] = mapped_column(
        SAEnum(DiscoveredChatType, name="discovered_chat_type"), nullable=False
    )
    status: Mapped[DiscoveredChatStatus] = mapped_column(
        SAEnum(DiscoveredChatStatus, name="discovered_chat_status"),
        nullable=False,
        default=DiscoveredChatStatus.MEMBER,
        server_default=DiscoveredChatStatus.MEMBER.value,
    )
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"DiscoveredChat(chat_id={self.chat_id!r}, title={self.title!r})"
