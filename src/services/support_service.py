"""Support inbox service -- Admin Reply (#12): users write in, admins reply."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.support_message import SupportMessage
from src.repositories.support_message_repository import SupportMessageRepository
from src.utils.exceptions import KinoBotError


class SupportMessageNotFoundError(KinoBotError):
    """Raised when a referenced support message id does not exist."""


class SupportService:
    """Coordinates the user-to-admin support inbox."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = SupportMessageRepository(session)

    async def submit(self, *, user_id: int, message: str) -> SupportMessage:
        """Record a new inbound support message from a user."""
        entry = SupportMessage(user_id=user_id, user_message=message.strip(), status="open")
        return await self._repository.add(entry)

    async def reply(self, message_id: int, *, admin_id: int, reply_text: str) -> SupportMessage:
        """Attach an admin reply and close a support message."""
        message = await self._repository.get_by_id(message_id)
        if message is None:
            raise SupportMessageNotFoundError(f"Support message {message_id} topilmadi.")
        message.admin_reply = reply_text.strip()
        message.replied_by = admin_id
        message.status = "closed"
        await self._repository.flush()
        return message

    async def list_open(self, limit: int = 20) -> list[SupportMessage]:
        """Return the most recent open (unreplied) support messages."""
        return list(await self._repository.list_open(limit=limit))

    async def list_for_user(self, user_id: int, limit: int = 20) -> list[SupportMessage]:
        """Return a user's own support message history."""
        return list(await self._repository.list_by_user(user_id, limit=limit))
