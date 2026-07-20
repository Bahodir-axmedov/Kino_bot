"""``/help`` and profile screen for end-users."""

from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from src.core.plugin import register_user_plugin
from src.services.user_service import UserService
from src.utils.formatters import format_user_profile

router = Router(name="user.help")


@router.message(Command("help"))
@router.message(F.text == "ℹ️ Yordam")
async def handle_help(message: Message) -> None:
    """Explain how to use the bot."""
    await message.answer(
        "🎥 <b>Qanday foydalanish mumkin?</b>\n\n"
        "1. Kino kodini yuboring (masalan: <code>1055</code>)\n"
        "2. Agar kod to'g'ri bo'lsa, botdan filmni olasiz\n\n"
        "🔍 Nom, janr, yil yoki til bo'yicha qidirish uchun "
        "\"🔍 Kino qidirish\" tugmasini bosing."
    )


@router.message(Command("profile"))
@router.message(F.text == "👤 Profilim")
async def handle_profile(message: Message, user_service: UserService) -> None:
    """Show the requesting user's own profile summary."""
    if message.from_user is None:
        return
    user = await user_service.find_by_identifier(str(message.from_user.id))
    if user is None:
        await message.answer("Profil topilmadi. Iltimos, /start buyrug'ini yuboring.")
        return
    await message.answer(format_user_profile(user))


register_user_plugin(router)
