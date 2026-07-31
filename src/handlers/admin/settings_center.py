"""Settings Center (V4.0): browse and edit every DB-backed bot setting."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, SettingsCategoryCallback, SettingsEditCallback
from src.keyboards.inline.admin_panel import (
    build_back_to_admin_menu_keyboard,
    build_settings_categories_keyboard,
    build_settings_category_keyboard,
    category_label,
    key_label,
)
from src.services.settings_service import DEFAULT_SETTINGS, SettingsService
from src.states.admin_states import SettingsEditStates

router = Router(name="admin.settings_center")


def _categories() -> list[str]:
    """Return every distinct category key, in first-seen order."""
    seen: list[str] = []
    for spec in DEFAULT_SETTINGS.values():
        category = spec["category"]
        if category not in seen:
            seen.append(category)
    return seen


@router.callback_query(AdminMenuCallback.filter(F.section == "settings"))
async def open_settings_center(callback: CallbackQuery) -> None:
    """Show the list of Settings Center categories."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⚙️ <b>Sozlamalar markazi</b>\n\nKategoriyani tanlang:",
            reply_markup=build_settings_categories_keyboard(_categories()),
        )
    await callback.answer()


@router.callback_query(SettingsCategoryCallback.filter())
async def open_settings_category(
    callback: CallbackQuery, callback_data: SettingsCategoryCallback, settings_service: SettingsService
) -> None:
    """Show every setting key within one category, with current effective values."""
    values = await settings_service.list_by_category(callback_data.category)
    entries = {
        key: {"value": value, "is_boolean": DEFAULT_SETTINGS[key]["type"].value == "boolean"}
        for key, value in values.items()
    }
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"⚙️ <b>{category_label(callback_data.category)}</b>\n\n"
            "Qiymatni almashtirish uchun tugmani bosing.",
            reply_markup=build_settings_category_keyboard(callback_data.category, entries),
        )
    await callback.answer()


@router.callback_query(SettingsEditCallback.filter())
async def edit_setting(
    callback: CallbackQuery,
    callback_data: SettingsEditCallback,
    settings_service: SettingsService,
    state: FSMContext,
) -> None:
    """Toggle a boolean setting immediately, or prompt for a new value otherwise."""
    key = callback_data.key
    spec = DEFAULT_SETTINGS.get(key)
    if spec is None:
        await callback.answer("❌ Noma'lum sozlama.", show_alert=True)
        return

    admin_id = callback.from_user.id if callback.from_user else None

    if spec["type"].value == "boolean":
        current = bool(await settings_service.get(key))
        await settings_service.set(key, not current, updated_by=admin_id)
        values = await settings_service.list_by_category(spec["category"])
        entries = {
            k: {"value": v, "is_boolean": DEFAULT_SETTINGS[k]["type"].value == "boolean"}
            for k, v in values.items()
        }
        if isinstance(callback.message, Message):
            await callback.message.edit_reply_markup(
                reply_markup=build_settings_category_keyboard(spec["category"], entries)
            )
        await callback.answer("✅ Yangilandi")
        return

    await state.set_state(SettingsEditStates.waiting_for_value)
    await state.update_data(settings_key=key, settings_category=spec["category"])
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"✏️ <b>{key_label(key)}</b> uchun yangi qiymatni yuboring:",
            reply_markup=build_back_to_admin_menu_keyboard(),
        )
    await callback.answer()


@router.message(SettingsEditStates.waiting_for_value, F.text)
async def receive_setting_value(
    message: Message, state: FSMContext, settings_service: SettingsService
) -> None:
    """Persist the admin-supplied value, converting it to the setting's declared type."""
    data = await state.get_data()
    key = data.get("settings_key")
    category = data.get("settings_category", "general")
    await state.clear()
    if key is None or key not in DEFAULT_SETTINGS:
        await message.answer("❌ Sessiya eskirgan. Qaytadan urinib ko'ring.")
        return

    spec = DEFAULT_SETTINGS[key]
    raw = message.text.strip()
    try:
        if spec["type"].value == "integer":
            value: object = int(raw)
        elif spec["type"].value == "float":
            value = float(raw)
        else:
            value = raw
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Qaytadan yuboring.")
        await state.set_state(SettingsEditStates.waiting_for_value)
        await state.update_data(settings_key=key, settings_category=category)
        return

    await settings_service.set(key, value, updated_by=message.from_user.id if message.from_user else None)
    values = await settings_service.list_by_category(category)
    entries = {
        k: {"value": v, "is_boolean": DEFAULT_SETTINGS[k]["type"].value == "boolean"}
        for k, v in values.items()
    }
    await message.answer(
        f"✅ <b>{key_label(key)}</b> yangilandi: {raw}",
        reply_markup=build_settings_category_keyboard(category, entries),
    )


register_admin_plugin(router)
