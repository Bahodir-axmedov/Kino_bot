"""Tap-to-pick keyboard for bot-discovered channels/groups.

Used by both the Force Subscribe and Media Sources admin flows so neither
ever requires the admin to type a @username or chat id.
"""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.keyboards.callback_data import AdminMenuCallback, DiscoveredChatCallback
from src.models.discovered_chat import DiscoveredChat


def _button_label(chat: DiscoveredChat) -> str:
    """Return a short, readable label for a discovered chat button."""
    label = f"@{chat.chat_username} \u2022 {chat.title}" if chat.chat_username else chat.title
    return label[:64]


def build_discovered_chat_picker_keyboard(
    chats: Sequence[DiscoveredChat],
    *,
    purpose: str,
    sub_type: str,
    back_section: str,
) -> InlineKeyboardMarkup:
    """Return one button per discovered chat the admin can tap to register.

    ``purpose``/``sub_type`` are the short codes documented in
    :mod:`src.keyboards.callback_data` (e.g. purpose="fs", sub_type="tc").
    """
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=_button_label(chat),
                callback_data=DiscoveredChatCallback(
                    purpose=purpose, sub_type=sub_type, chat_id=chat.chat_id
                ).pack(),
            )
        ]
        for chat in chats
    ]
    rows.append(
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section=back_section).pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
