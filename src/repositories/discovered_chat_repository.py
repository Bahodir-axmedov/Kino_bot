"""Data-access operations for discovered (bot-membership) chats."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select

from src.models.discovered_chat import DiscoveredChat, DiscoveredChatStatus, DiscoveredChatType
from src.repositories.base import BaseRepository

_AVAILABLE_STATUSES = (DiscoveredChatStatus.ADMINISTRATOR, DiscoveredChatStatus.MEMBER)


class DiscoveredChatRepository(BaseRepository[DiscoveredChat]):
    """Repository encapsulating all SQL access for ``DiscoveredChat`` rows."""

    model = DiscoveredChat

    async def get_by_chat_id(self, chat_id: int) -> DiscoveredChat | None:
        """Return the discovered chat for ``chat_id``, or ``None``."""
        statement = select(DiscoveredChat).where(DiscoveredChat.chat_id == chat_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_available(self, chat_type: DiscoveredChatType) -> Sequence[DiscoveredChat]:
        """Return chats of ``chat_type`` the bot can currently act in, by title."""
        statement = (
            select(DiscoveredChat)
            .where(
                DiscoveredChat.chat_type == chat_type,
                DiscoveredChat.status.in_(_AVAILABLE_STATUSES),
            )
            .order_by(DiscoveredChat.title)
        )
        result = await self._session.execute(statement)
        return result.scalars().all()
