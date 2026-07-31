"""Inline keyboards for the mandatory-subscription (force-sub) center.

Supports Telegram-native targets (auto-verified) and external platforms
(Instagram/YouTube/TikTok/Facebook/X/Website/Telegram Bot), which show a
manual "Tasdiqlash" confirmation button instead of relying on get_chat_member.
"""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.keyboards.callback_data import (
    ForceSubActionCallback,
    ForceSubCheckCallback,
    ForceSubConfirmCallback,
    ForceSubPlatformCallback,
)
from src.models.force_sub_channel import (
    TELEGRAM_AUTO_VERIFIABLE_PLATFORMS,
    ForceSubChannel,
    ForceSubPlatform,
)

_PLATFORM_LABELS: dict[ForceSubPlatform, str] = {
    ForceSubPlatform.TELEGRAM_CHANNEL: "Telegram kanal",
    ForceSubPlatform.TELEGRAM_GROUP: "Telegram guruh",
    ForceSubPlatform.TELEGRAM_DISCUSSION_GROUP: "Muhokama guruhi",
    ForceSubPlatform.TELEGRAM_BOT: "Telegram bot",
    ForceSubPlatform.INSTAGRAM: "Instagram",
    ForceSubPlatform.YOUTUBE: "YouTube",
    ForceSubPlatform.TIKTOK: "TikTok",
    ForceSubPlatform.FACEBOOK: "Facebook",
    ForceSubPlatform.TWITTER_X: "Twitter slash X",
    ForceSubPlatform.WEBSITE: "Website",
}


def _resolve_channel_url(channel: ForceSubChannel) -> str | None:
    """Return the best available join/profile URL for a subscription target."""
    if channel.url:
        return channel.url
    if channel.invite_link:
        return channel.invite_link
    if channel.chat_username:
        return "https://t.me/" + channel.chat_username.lstrip("@")
    return None


def build_platform_selection_keyboard() -> InlineKeyboardMarkup:
    """Return one button per supported platform type, for the add-target flow."""
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for platform in ForceSubPlatform:
        row.append(
            InlineKeyboardButton(
                text=_PLATFORM_LABELS[platform],
                callback_data=ForceSubPlatformCallback(platform=platform.value).pack(),
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Bekor qilish", callback_data=ForceSubActionCallback(action="cancel_add", channel_id=0).pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_force_sub_gate_keyboard(
    channels: Sequence[ForceSubChannel], movie_code: str
) -> InlineKeyboardMarkup:
    """Return join/confirm buttons for every outstanding target plus a recheck button.

    Telegram-auto-verifiable targets only need a join-link button (membership
    is checked live via get_chat_member). Every other platform also gets a
    Tasdiqlash confirmation button, since the bot has no API access to
    verify membership there.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for channel in channels:
        url = _resolve_channel_url(channel)
        row: list[InlineKeyboardButton] = []
        if url:
            row.append(InlineKeyboardButton(text="+ " + channel.title, url=url))
        if channel.platform not in TELEGRAM_AUTO_VERIFIABLE_PLATFORMS:
            row.append(
                InlineKeyboardButton(
                    text="Tasdiqlash",
                    callback_data=ForceSubConfirmCallback(
                        channel_id=channel.id, movie_code=movie_code
                    ).pack(),
                )
            )
        if row:
            rows.append(row)
    rows.append(
        [
            InlineKeyboardButton(
                text="Tekshirish",
                callback_data=ForceSubCheckCallback(movie_code=movie_code).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_force_sub_admin_list_keyboard(
    channels: Sequence[ForceSubChannel],
) -> InlineKeyboardMarkup:
    """Return an admin-facing list of every target with status/mandatory toggles."""
    rows: list[list[InlineKeyboardButton]] = []
    for channel in channels:
        status_icon = "Aktiv" if channel.is_active else "Noaktiv"
        mandatory_icon = "Majburiy" if channel.is_mandatory else "Ixtiyoriy"
        label = _PLATFORM_LABELS.get(channel.platform, "")
        rows.append(
            [
                InlineKeyboardButton(
                    text=(label + " " + channel.title)[:64],
                    callback_data=ForceSubActionCallback(action="noop", channel_id=channel.id).pack(),
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=status_icon,
                    callback_data=ForceSubActionCallback(action="toggle", channel_id=channel.id).pack(),
                ),
                InlineKeyboardButton(
                    text=mandatory_icon,
                    callback_data=ForceSubActionCallback(
                        action="toggle_mandatory", channel_id=channel.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="O'chirish",
                    callback_data=ForceSubActionCallback(action="remove", channel_id=channel.id).pack(),
                ),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="Kanal/Platforma qo'shish",
                callback_data=ForceSubActionCallback(action="add", channel_id=0).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
