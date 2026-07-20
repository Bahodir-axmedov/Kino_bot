"""Blacklist Center (V4.0): block users, media, words, codes, countries, etc."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, BlacklistActionCallback, BlacklistTypeCallback
from src.keyboards.inline.admin_panel import build_blacklist_entries_keyboard, build_blacklist_type_keyboard
from src.models.blacklist_entry import BlacklistEntryType
from src.services.blacklist_service import BlacklistService
from src.states.admin_states import BlacklistStates
from src.utils.exceptions import InvalidInputError

router = Router(name="admin.blacklist_center")


@router.callback_query(AdminMenuCallback.filter(F.section == "blacklist"))
async def open_blacklist_center(callback: CallbackQuery) -> None:
    """Show the Blacklist Center entry-type picker."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⛔ <b>Blacklist markazi</b>\n\nTurni tanlang:", reply_markup=build_blacklist_type_keyboard()
        )
    await callback.answer()


@router.callback_query(BlacklistTypeCallback.filter())
async def open_blacklist_type(
    callback: CallbackQuery, callback_data: BlacklistTypeCallback, blacklist_service: BlacklistService, state: FSMContext
) -> None:
    """List entries of a chosen type, or prompt to add a new one if none rendered yet."""
    entry_type = BlacklistEntryType(callback_data.entry_type)
    entries = await blacklist_service.list_by_type(entry_type)
    await state.set_state(BlacklistStates.waiting_for_value)
    await state.update_data(blacklist_entry_type=entry_type.value)
    if isinstance(callback.message, Message):
        lines = [f"⛔ <b>{entry_type.value}</b>", ""]
        lines.append("Ro'yxatdagi yozuvni bosib o'chiring, yoki yangi qiymatni matn sifatida yuboring:")
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=build_blacklist_entries_keyboard(entry_type.value, entries)
        )
    await callback.answer()


@router.message(BlacklistStates.waiting_for_value, F.text)
async def receive_blacklist_value(
    message: Message, state: FSMContext, blacklist_service: BlacklistService
) -> None:
    """Add the supplied value to the blacklist under the previously chosen type."""
    data = await state.get_data()
    entry_type_value = data.get("blacklist_entry_type")
    if entry_type_value is None:
        await message.answer("❌ Sessiya eskirgan. Qaytadan urinib ko'ring.")
        return
    entry_type = BlacklistEntryType(entry_type_value)
    try:
        await blacklist_service.add(
            entry_type, message.text.strip(), created_by=message.from_user.id if message.from_user else None
        )
    except InvalidInputError as error:
        await message.answer(f"❌ {error}")
        return
    entries = await blacklist_service.list_by_type(entry_type)
    await message.answer(
        "✅ Blacklistga qo'shildi.", reply_markup=build_blacklist_entries_keyboard(entry_type.value, entries)
    )


@router.callback_query(BlacklistActionCallback.filter())
async def remove_blacklist_entry(
    callback: CallbackQuery, callback_data: BlacklistActionCallback, blacklist_service: BlacklistService
) -> None:
    """Deactivate the tapped blacklist entry."""
    try:
        await blacklist_service.remove(callback_data.entry_id)
    except InvalidInputError as error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return
    await callback.answer("✅ O'chirildi")


register_admin_plugin(router)
