"""Whitelist Center (V4.0): exempt users/admins/channels/groups/roles from limits."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, WhitelistActionCallback, WhitelistTypeCallback
from src.keyboards.inline.admin_panel import build_whitelist_entries_keyboard, build_whitelist_type_keyboard
from src.models.whitelist_entry import WhitelistEntryType
from src.services.whitelist_service import WhitelistService
from src.states.admin_states import WhitelistStates
from src.utils.exceptions import InvalidInputError

router = Router(name="admin.whitelist_center")


@router.callback_query(AdminMenuCallback.filter(F.section == "whitelist"))
async def open_whitelist_center(callback: CallbackQuery) -> None:
    """Show the Whitelist Center entry-type picker."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "✅ <b>Whitelist markazi</b>\n\nTurni tanlang:", reply_markup=build_whitelist_type_keyboard()
        )
    await callback.answer()


@router.callback_query(WhitelistTypeCallback.filter())
async def open_whitelist_type(
    callback: CallbackQuery, callback_data: WhitelistTypeCallback, whitelist_service: WhitelistService, state: FSMContext
) -> None:
    """List entries of a chosen type and prompt to add a new one."""
    entry_type = WhitelistEntryType(callback_data.entry_type)
    entries = await whitelist_service.list_by_type(entry_type)
    await state.set_state(WhitelistStates.waiting_for_value)
    await state.update_data(whitelist_entry_type=entry_type.value)
    if isinstance(callback.message, Message):
        lines = [f"✅ <b>{entry_type.value}</b>", ""]
        lines.append("Ro'yxatdagi yozuvni bosib o'chiring, yoki yangi qiymatni matn sifatida yuboring:")
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=build_whitelist_entries_keyboard(entry_type.value, entries)
        )
    await callback.answer()


@router.message(WhitelistStates.waiting_for_value, F.text)
async def receive_whitelist_value(
    message: Message, state: FSMContext, whitelist_service: WhitelistService
) -> None:
    """Add the supplied value to the whitelist under the previously chosen type."""
    data = await state.get_data()
    entry_type_value = data.get("whitelist_entry_type")
    if entry_type_value is None:
        await message.answer("❌ Sessiya eskirgan. Qaytadan urinib ko'ring.")
        return
    entry_type = WhitelistEntryType(entry_type_value)
    try:
        await whitelist_service.add(
            entry_type, message.text.strip(), created_by=message.from_user.id if message.from_user else None
        )
    except InvalidInputError as error:
        await message.answer(f"❌ {error}")
        return
    entries = await whitelist_service.list_by_type(entry_type)
    await message.answer(
        "✅ Whitelistga qo'shildi.", reply_markup=build_whitelist_entries_keyboard(entry_type.value, entries)
    )


@router.callback_query(WhitelistActionCallback.filter())
async def remove_whitelist_entry(
    callback: CallbackQuery, callback_data: WhitelistActionCallback, whitelist_service: WhitelistService
) -> None:
    """Permanently remove the tapped whitelist entry."""
    try:
        await whitelist_service.remove(callback_data.entry_id)
    except InvalidInputError as error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return
    await callback.answer("✅ O'chirildi")


register_admin_plugin(router)
