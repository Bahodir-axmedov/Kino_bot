"""Passively records every chat the bot is added to/removed from.

This is the core of the zero-typing admin UX: it needs no admin command and
no IsAdminFilter gate (any Telegram user can add a bot to a chat they
administer -- that is normal Telegram behaviour, not a privileged action,
and nothing sensitive is written here beyond 'the bot is now in chat X').
Once a channel/group shows up here, the admin panel offers it as a
tap-to-pick option for Force Subscribe and Media Sources instead of
requiring anyone to type a @username or chat id.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.types import ChatMemberUpdated

from src.core.plugin import register_admin_plugin
from src.models.discovered_chat import DiscoveredChatStatus, DiscoveredChatType
from src.services.discovered_chat_service import DiscoveredChatService

router = Router(name="admin.chat_discovery")

_STATUS_MAP: dict[str, DiscoveredChatStatus] = {
    "creator": DiscoveredChatStatus.ADMINISTRATOR,
    "administrator": DiscoveredChatStatus.ADMINISTRATOR,
    "member": DiscoveredChatStatus.MEMBER,
    "restricted": DiscoveredChatStatus.MEMBER,
    "left": DiscoveredChatStatus.LEFT,
    "kicked": DiscoveredChatStatus.KICKED,
}


@router.my_chat_member()
async def on_bot_membership_changed(
    event: ChatMemberUpdated, discovered_chat_service: DiscoveredChatService
) -> None:
    """Upsert a DiscoveredChat row whenever the bot's status in a chat changes."""
    chat = event.chat
    if chat.type not in ("channel", "group", "supergroup"):
        return
    chat_type = (
        DiscoveredChatType.CHANNEL if chat.type == "channel" else DiscoveredChatType.GROUP
    )
    status = _STATUS_MAP.get(event.new_chat_member.status, DiscoveredChatStatus.MEMBER)
    await discovered_chat_service.record_membership_change(
        chat_id=chat.id,
        title=chat.title or chat.full_name or str(chat.id),
        chat_type=chat_type,
        chat_username=chat.username,
        status=status,
        changed_by=event.from_user.id if event.from_user else None,
    )


register_admin_plugin(router)
