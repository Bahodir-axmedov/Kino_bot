"""Business logic for tracking chats the bot has been added to/removed from."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.discovered_chat import DiscoveredChat, DiscoveredChatStatus, DiscoveredChatType
from src.repositories.discovered_chat_repository import DiscoveredChatRepository


class DiscoveredChatService:
    """Encapsulates every business rule about bot-membership discovery."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = DiscoveredChatRepository(session)

    async def record_membership_change(
        self,
        *,
        chat_id: int,
        title: str,
        chat_type: DiscoveredChatType,
        chat_username: str | None,
        status: DiscoveredChatStatus,
        changed_by: int | None,
    ) -> DiscoveredChat:
        """Upsert the bot's current membership status for a chat.

        Called from the ``my_chat_member`` update handler whenever the bot is
        added to, promoted/demoted in, or removed from a channel/group -- this
        is what lets the admin panel offer a tap-to-pick list instead of
        requiring typed usernames/ids anywhere.
        """
        existing = await self._repository.get_by_chat_id(chat_id)
        if existing is not None:
            existing.title = title
            existing.chat_type = chat_type
            existing.chat_username = chat_username
            existing.status = status
            if changed_by is not None:
                existing.added_by = changed_by
            await self._repository.flush()
            return existing
        chat = DiscoveredChat(
            chat_id=chat_id,
            title=title,
            chat_username=chat_username,
            chat_type=chat_type,
            status=status,
            added_by=changed_by,
        )
        return await self._repository.add(chat)

    async def list_available(self, chat_type: DiscoveredChatType) -> list[DiscoveredChat]:
        """Return chats of ``chat_type`` the bot can currently act in."""
        return list(await self._repository.list_available(chat_type))

    async def get_by_chat_id(self, chat_id: int) -> DiscoveredChat | None:
        """Return the discovered chat for ``chat_id``, or ``None``."""
        return await self._repository.get_by_chat_id(chat_id)
