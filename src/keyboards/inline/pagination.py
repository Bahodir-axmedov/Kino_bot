"""Reusable pagination inline keyboard row."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton

from src.keyboards.callback_data import PaginationCallback


def build_pagination_row(
    scope: str, current_index: int, has_next: bool
) -> list[InlineKeyboardButton]:
    """Return a single row of prev/next pagination buttons.

    Buttons are omitted at the boundaries (no "previous" on page 0, no
    "next" when the current page is not full) rather than being shown
    disabled, which keeps the keyboard state always actionable.
    """
    row: list[InlineKeyboardButton] = []
    if current_index > 0:
        row.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=PaginationCallback(scope=scope, index=current_index - 1).pack(),
            )
        )
    if has_next:
        row.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=PaginationCallback(scope=scope, index=current_index + 1).pack(),
            )
        )
    return row
