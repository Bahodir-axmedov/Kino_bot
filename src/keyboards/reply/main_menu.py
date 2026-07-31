"""Main reply keyboard shown to end-users."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return the persistent bottom keyboard shown to every end-user."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Kino qidirish")],
            [KeyboardButton(text="ℹ️ Yordam"), KeyboardButton(text="👤 Profilim")],
            [KeyboardButton(text="🤝 Referral"), KeyboardButton(text="⭐️ Premium")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
