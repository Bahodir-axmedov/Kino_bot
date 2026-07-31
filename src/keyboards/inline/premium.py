"""Inline keyboards for the end-user Premium purchase flow."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.keyboards.callback_data import PremiumBuyCallback


def format_amount(amount: int) -> str:
    """Render an integer with space thousands separators (e.g. 20000 -> "20 000")."""
    return f"{amount:,}".replace(",", " ")


def build_premium_purchase_keyboard(
    *,
    stars_enabled: bool,
    card_enabled: bool,
    stars_price: int,
    uzs_price: int,
) -> InlineKeyboardMarkup:
    """Return the buy-Premium keyboard with only the enabled payment methods."""
    rows: list[list[InlineKeyboardButton]] = []
    if stars_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"\u2B50\uFE0F Telegram Stars ({stars_price} \u2B50\uFE0F)",
                    callback_data=PremiumBuyCallback(method="stars").pack(),
                )
            ]
        )
    if card_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"\U0001F4B3 Uzcard / Humo ({format_amount(uzs_price)} so'm)",
                    callback_data=PremiumBuyCallback(method="card").pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_card_paid_keyboard() -> InlineKeyboardMarkup:
    """Return the "I have paid, here is my receipt" button shown after card details."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u2705 To'lovni amalga oshirdim (chek yuborish)",
                    callback_data=PremiumBuyCallback(method="card_paid").pack(),
                )
            ]
        ]
    )
