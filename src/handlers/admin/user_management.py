"""Admin user management: search, history, ban/unban/mute, Premium System."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, UserActionCallback
from src.services.log_service import LogService
from src.services.premium_service import PremiumService
from src.services.user_service import UserService
from src.states.admin_states import PremiumGrantStates
from src.states.user_states import UserManagementStates
from src.utils.exceptions import InvalidInputError
from src.utils.formatters import format_user_profile

router = Router(name="admin.user_management")


def _build_user_actions_keyboard(telegram_id: int, is_banned: bool, is_premium: bool) -> InlineKeyboardMarkup:
    """Build the inline action row for a single user lookup result."""
    ban_button = InlineKeyboardButton(
        text=("✅ Unban" if is_banned else "🚫 Ban"),
        callback_data=UserActionCallback(
            action=("unban" if is_banned else "ban"), telegram_id=telegram_id
        ).pack(),
    )
    mute_button = InlineKeyboardButton(
        text="🔇 Mute",
        callback_data=UserActionCallback(action="mute", telegram_id=telegram_id).pack(),
    )
    premium_button = InlineKeyboardButton(
        text=("⭐️ Premiumni olib tashlash" if is_premium else "⭐️ Premium berish"),
        callback_data=UserActionCallback(
            action=("revoke_premium" if is_premium else "grant_premium"), telegram_id=telegram_id
        ).pack(),
    )
    return InlineKeyboardMarkup(inline_keyboard=[[ban_button, mute_button], [premium_button]])


@router.callback_query(AdminMenuCallback.filter(F.section == "users"))
async def open_user_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt for a user identifier (Telegram id or username)."""
    await state.set_state(UserManagementStates.waiting_for_identifier)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("👥 Foydalanuvchi ID yoki username yuboring:")
    await callback.answer()


@router.message(UserManagementStates.waiting_for_identifier, F.text)
async def show_user_profile(message: Message, state: FSMContext, user_service: UserService) -> None:
    """Look up a user and show their profile with moderation actions."""
    await state.clear()
    identifier = message.text.strip()
    user = await user_service.find_by_identifier(identifier)
    if user is None:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return
    await message.answer(
        format_user_profile(user),
        reply_markup=_build_user_actions_keyboard(
            user.telegram_id, user.is_banned, user.is_premium
        ),
    )


@router.callback_query(UserActionCallback.filter(F.action == "ban"))
async def ban_user(
    callback: CallbackQuery,
    callback_data: UserActionCallback,
    user_service: UserService,
    log_service: LogService,
) -> None:
    """Ban a user immediately (no reason required for the quick action)."""
    user = await user_service.ban(callback_data.telegram_id, reason="Admin tomonidan bloklandi")
    if user is None:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="user_banned",
        entity_type="user",
        entity_id=str(user.telegram_id),
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_user_profile(user),
            reply_markup=_build_user_actions_keyboard(user.telegram_id, True, user.is_premium),
        )
    await callback.answer("🚫 Bloklandi.")


@router.callback_query(UserActionCallback.filter(F.action == "unban"))
async def unban_user(
    callback: CallbackQuery,
    callback_data: UserActionCallback,
    user_service: UserService,
    log_service: LogService,
) -> None:
    """Lift a ban from a user."""
    user = await user_service.unban(callback_data.telegram_id)
    if user is None:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="user_unbanned",
        entity_type="user",
        entity_id=str(user.telegram_id),
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_user_profile(user),
            reply_markup=_build_user_actions_keyboard(user.telegram_id, False, user.is_premium),
        )
    await callback.answer("✅ Blok olib tashlandi.")


@router.callback_query(UserActionCallback.filter(F.action == "mute"))
async def toggle_mute_user(
    callback: CallbackQuery,
    callback_data: UserActionCallback,
    user_service: UserService,
    log_service: LogService,
) -> None:
    """Toggle a user's muted state."""
    user = await user_service.find_by_identifier(str(callback_data.telegram_id))
    if user is None:
        await callback.answer("Topilmadi.", show_alert=True)
        return
    user = await user_service.set_muted(user.telegram_id, not user.is_muted)
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="user_mute_toggled",
        entity_type="user",
        entity_id=str(user.telegram_id),
        new_value={"is_muted": user.is_muted},
    )
    await callback.answer("🔇 Yangilandi.")


@router.callback_query(UserActionCallback.filter(F.action == "grant_premium"))
async def prompt_grant_premium(
    callback: CallbackQuery, callback_data: UserActionCallback, state: FSMContext
) -> None:
    """Prompt the admin for the number of days to grant Premium for."""
    await state.set_state(PremiumGrantStates.waiting_for_days)
    await state.update_data(premium_target_telegram_id=callback_data.telegram_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⭐️ Necha kunlik Premium berilsin? Raqam yuboring (masalan: 30):"
        )
    await callback.answer()


@router.message(PremiumGrantStates.waiting_for_days, F.text)
async def receive_premium_days(
    message: Message,
    state: FSMContext,
    premium_service: PremiumService,
    user_service: UserService,
    log_service: LogService,
) -> None:
    """Grant Premium for the supplied number of days via the Premium System."""
    data = await state.get_data()
    await state.clear()
    telegram_id = data.get("premium_target_telegram_id")
    if telegram_id is None:
        await message.answer("❌ Sessiya eskirgan. Qaytadan urinib ko'ring.")
        return

    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam yuboring.")
        await state.set_state(PremiumGrantStates.waiting_for_days)
        await state.update_data(premium_target_telegram_id=telegram_id)
        return

    try:
        await premium_service.grant(telegram_id, days=days, granted_by=message.from_user.id if message.from_user else None)
    except InvalidInputError as error:
        await message.answer(f"❌ {error}")
        return

    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="premium_granted",
        entity_type="user",
        entity_id=str(telegram_id),
        new_value={"days": days},
    )
    user = await user_service.find_by_identifier(str(telegram_id))
    if user is None:
        await message.answer(f"✅ {days} kunlik Premium berildi.")
        return
    await message.answer(
        format_user_profile(user),
        reply_markup=_build_user_actions_keyboard(user.telegram_id, user.is_banned, True),
    )


@router.callback_query(UserActionCallback.filter(F.action == "revoke_premium"))
async def revoke_premium(
    callback: CallbackQuery,
    callback_data: UserActionCallback,
    premium_service: PremiumService,
    user_service: UserService,
    log_service: LogService,
) -> None:
    """Revoke Premium status from a user via the Premium System."""
    try:
        await premium_service.revoke(callback_data.telegram_id)
    except InvalidInputError as error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="premium_revoked",
        entity_type="user",
        entity_id=str(callback_data.telegram_id),
    )
    user = await user_service.find_by_identifier(str(callback_data.telegram_id))
    if user is None:
        await callback.answer("Premium olib tashlandi.")
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_user_profile(user),
            reply_markup=_build_user_actions_keyboard(user.telegram_id, user.is_banned, False),
        )
    await callback.answer("Premium olib tashlandi.")


register_admin_plugin(router)
