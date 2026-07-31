"""Owner-only administrator management (add/remove/roles) and settings view."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.config import Settings
from src.core.plugin import register_admin_plugin
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.filters.owner_filter import IsOwnerFilter
from src.keyboards.callback_data import AdminMenuCallback, AdminRemoveCallback
from src.models.admin import AdminRole
from src.services.admin_service import AdminService
from src.services.log_service import LogService
from src.states.admin_states import AddAdminStates
from src.utils.exceptions import InvalidInputError
from src.utils.validators import validate_telegram_id

router = Router(name="admin.admins")


def _build_admins_keyboard(admins: list, settings: Settings) -> InlineKeyboardMarkup:
    """Return one remove button per non-owner admin, plus a back button."""
    rows: list[list[InlineKeyboardButton]] = []
    for admin in admins:
        if admin.telegram_id == settings.owner_id:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🗑 {admin.telegram_id} ({admin.role.value}) ni olib tashlash",
                    callback_data=AdminRemoveCallback(telegram_id=admin.telegram_id).pack(),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=AdminMenuCallback(section="root").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(AdminMenuCallback.filter(F.section == "admins"), IsOwnerFilter())
async def open_admins_menu(
    callback: CallbackQuery, admin_service: AdminService, state: FSMContext, settings: Settings
) -> None:
    """List current administrators and prompt to add a new one (owner only)."""
    admins = await admin_service.list_admins()
    lines = ["🛡 <b>Adminlar</b>", ""]
    for admin in admins:
        lines.append(f"• <code>{admin.telegram_id}</code> — {admin.role.value}")
    lines.append("")
    lines.append("Yangi admin qo'shish uchun Telegram ID yuboring, yoki quyidagi ro'yxatdan birini olib tashlang:")
    await state.set_state(AddAdminStates.waiting_for_telegram_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("\n".join(lines), reply_markup=_build_admins_keyboard(admins, settings))
    await callback.answer()


@router.callback_query(AdminMenuCallback.filter(F.section == "admins"))
async def admins_access_denied(callback: CallbackQuery) -> None:
    """Reject taps from non-owner admins with visible feedback (previously a dead button)."""
    await callback.answer("⛔ Bu bo'lim faqat bot egasi uchun.", show_alert=True)


@router.callback_query(AdminRemoveCallback.filter(), IsOwnerFilter())
async def remove_admin(
    callback: CallbackQuery,
    callback_data: AdminRemoveCallback,
    admin_service: AdminService,
    log_service: LogService,
    settings: Settings,
) -> None:
    """Remove an existing administrator (owner only)."""
    removed = await admin_service.remove_admin(callback_data.telegram_id)
    if removed:
        await log_service.record(
            actor_id=callback.from_user.id,
            actor_role="owner",
            action="admin_removed",
            entity_type="admin",
            entity_id=str(callback_data.telegram_id),
        )
    admins = await admin_service.list_admins()
    lines = ["🛡 <b>Adminlar</b>", ""]
    for admin in admins:
        lines.append(f"• <code>{admin.telegram_id}</code> — {admin.role.value}")
    lines.append("")
    lines.append("Yangi admin qo'shish uchun Telegram ID yuboring, yoki quyidagi ro'yxatdan birini olib tashlang:")
    if isinstance(callback.message, Message):
        await callback.message.edit_text("\n".join(lines), reply_markup=_build_admins_keyboard(admins, settings))
    await callback.answer("✅ Olib tashlandi." if removed else "Topilmadi.")


@router.message(AddAdminStates.waiting_for_telegram_id, F.text)
async def receive_new_admin_id(message: Message, state: FSMContext) -> None:
    """Capture the candidate admin's Telegram id and ask for a role."""
    try:
        telegram_id = validate_telegram_id(message.text)
    except InvalidInputError as error:
        await message.answer(f"❌ {error}")
        return
    await state.update_data(telegram_id=telegram_id)
    await state.set_state(AddAdminStates.waiting_for_role)
    await message.answer("Rolni yuboring: admin yoki moderator")


@router.message(AddAdminStates.waiting_for_role, F.text)
async def receive_new_admin_role(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
    log_service: LogService,
) -> None:
    """Persist the new administrator with the chosen role."""
    data = await state.get_data()
    await state.clear()
    role_text = message.text.strip().lower()
    role_map = {"admin": AdminRole.ADMIN, "moderator": AdminRole.MODERATOR}
    role = role_map.get(role_text)
    if role is None:
        await message.answer("❌ Noto'g'ri rol. 'admin' yoki 'moderator' yuboring.")
        return

    admin = await admin_service.add_admin(
        telegram_id=data["telegram_id"],
        role=role,
        added_by=message.from_user.id if message.from_user else 0,
    )
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="owner",
        action="admin_added",
        entity_type="admin",
        entity_id=str(admin.telegram_id),
        new_value={"role": role.value},
    )
    await message.answer(f"✅ <code>{admin.telegram_id}</code> {role.value} qilib qo'shildi.")


register_admin_plugin(router)
