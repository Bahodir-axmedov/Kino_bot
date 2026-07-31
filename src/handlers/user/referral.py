"""Referral System (V4.0) for end-users.

The "\u2B50\uFE0F Premium" main-menu button is handled separately in
:mod:`src.handlers.user.premium` (the full purchase flow). This module only
owns the "\U0001F91D Referral" screen: the user's personal invite link,
their invite stats and reward history.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from src.config import Settings
from src.core.plugin import register_user_plugin
from src.services.referral_reward_service import ReferralRewardService
from src.services.user_service import UserService
from src.utils.formatters import format_datetime

router = Router(name="user.referral")


async def _resolve_bot_username(message: Message, settings: Settings) -> str:
    """Prefer the configured bot username; fall back to a live ``getMe`` lookup."""
    if settings.bot_username:
        return settings.bot_username.lstrip("@")
    if message.bot is not None:
        me = await message.bot.get_me()
        return me.username or ""
    return ""


@router.message(F.text == "\U0001F91D Referral")
async def show_referral_screen(
    message: Message,
    settings: Settings,
    user_service: UserService,
    referral_reward_service: ReferralRewardService,
) -> None:
    """Show the requesting user's personal invite link, stats, and reward history."""
    if message.from_user is None:
        return
    user = await user_service.find_by_identifier(str(message.from_user.id))
    if user is None:
        await message.answer("Profil topilmadi. Iltimos, /start buyrug'ini yuboring.")
        return

    username = await _resolve_bot_username(message, settings)
    invite_link = (
        f"https://t.me/{username}?start={message.from_user.id}" if username else "\u2014"
    )
    total_rewards = await referral_reward_service.total_rewards_for_user(message.from_user.id)
    history = await referral_reward_service.history_for_user(message.from_user.id)

    recent_lines = "\n".join(
        f"  \u2022 {format_datetime(reward.granted_at)} \u2014 {reward.reward_type} (+{reward.amount})"
        for reward in history[:5]
    ) or "  \u2014"

    text = (
        "\U0001F91D <b>Referral tizimi</b>\n\n"
        "Do'stlaringizni taklif qiling va bonuslar oling!\n\n"
        f"\U0001F517 Sizning shaxsiy taklif havolangiz:\n<code>{invite_link}</code>\n\n"
        f"\U0001F465 Taklif qilingan foydalanuvchilar: <b>{user.invite_count}</b>\n"
        f"\U0001F381 Jami mukofotlar: <b>{total_rewards}</b>\n\n"
        f"\U0001F551 So'nggi mukofotlar:\n{recent_lines}\n\n"
        "\U0001F4A1 <b>Qanday ishlaydi?</b>\n"
        "1) Yuqoridagi havolani do'stlaringizga yuboring.\n"
        "2) Ular havola orqali botga kirib /start bossin.\n"
        "3) Har bir yangi foydalanuvchi uchun sizga bonus yoziladi.\n"
        "4) Ma'lum sondagi taklifdan so'ng qo'shimcha Premium bonusi beriladi."
    )
    await message.answer(text)


register_user_plugin(router)
