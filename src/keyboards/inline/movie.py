"""Inline keyboards related to a single movie entry."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.keyboards.callback_data import MovieActionCallback
from src.models.movie import Movie


def build_movie_admin_actions_keyboard(movie: Movie) -> InlineKeyboardMarkup:
    """Return inline actions available to an admin for a single movie."""
    rows = [
        [
            InlineKeyboardButton(
                text="✏️ Tahrirlash",
                callback_data=MovieActionCallback(action="edit", movie_id=movie.id).pack(),
            ),
            InlineKeyboardButton(
                text="🗑 O'chirish",
                callback_data=MovieActionCallback(action="delete", movie_id=movie.id).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text=("✅ Faollashtirish" if not movie.is_active else "🚫 O'chirib qo'yish"),
                callback_data=MovieActionCallback(action="toggle", movie_id=movie.id).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_movie_delete_confirm_keyboard(movie_id: int) -> InlineKeyboardMarkup:
    """Return a yes/no confirmation keyboard for deleting a movie."""
    rows = [
        [
            InlineKeyboardButton(
                text="✅ Ha, o'chirish",
                callback_data=MovieActionCallback(action="confirm_delete", movie_id=movie_id).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Bekor qilish",
                callback_data=MovieActionCallback(action="cancel_delete", movie_id=movie_id).pack(),
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
