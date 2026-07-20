"""Security Center + Admin Login Protection (V4.0): PIN/2FA gate on ``/admin``."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, SecurityActionCallback
from src.keyboards.inline.admin_panel import build_admin_main_menu_keyboard, build_security_keyboard
from src.services.admin_security_service import AdminSecurityService
from src.states.admin_states import SecurityStates
from src.utils.exceptions import AdminLockedOutError, InvalidTwoFactorCodeError, PermissionDeniedError

router = Router(name="admin.security_center")


async def is_admin_logged_in(state: FSMContext) -> bool:
    """Return True once this FSM has a verified ``admin_session_token`` from the login gate."""
    data = await state.get_data()
    return bool(data.get("admin_session_token"))


async def start_login_gate(message: Message, state: FSMContext, admin_security_service: AdminSecurityService) -> None:
    """Entry point for ``/admin``: skip the gate if no PIN is set yet, else prompt for it.

    An admin who has never set a PIN is allowed straight in (first-run
    bootstrap); they are strongly encouraged to set one from the Security
    Center immediately afterwards.
    """
    admin_id = message.from_user.id if message.from_user else 0
    status = await admin_security_service.get_status(admin_id)
    if not status.pin_set:
        await state.update_data(admin_session_token="bootstrap")
        await message.answer(
            "\U0001F3E0 <b>Admin panel</b>\n\n\u26A0\uFE0F Siz hali xavfsizlik PIN kodini o'rnatmagansiz. "
            "Xavfsizlik markazidan PIN o'rnatishni tavsiya qilamiz.",
            reply_markup=build_admin_main_menu_keyboard(),
        )
        return
    await state.set_state(SecurityStates.waiting_for_login_pin)
    await message.answer("\U0001F510 Admin panelga kirish uchun PIN kodni yuboring:")


@router.message(SecurityStates.waiting_for_login_pin, F.text)
async def receive_login_pin(
    message: Message, state: FSMContext, admin_security_service: AdminSecurityService
) -> None:
    """Verify the PIN; if 2FA is also enabled, prompt for the TOTP code next."""
    admin_id = message.from_user.id if message.from_user else 0
    status = await admin_security_service.get_status(admin_id)
    await state.update_data(admin_login_pin=message.text.strip())
    if status.two_factor_enabled:
        await state.set_state(SecurityStates.waiting_for_login_two_factor)
        await message.answer("\U0001F512 Endi 2FA kodini yuboring:")
        return
    await _finish_login(message, state, admin_security_service, pin=message.text.strip(), two_factor_code=None)


@router.message(SecurityStates.waiting_for_login_two_factor, F.text)
async def receive_login_two_factor(
    message: Message, state: FSMContext, admin_security_service: AdminSecurityService
) -> None:
    """Verify PIN + 2FA together and finish the login gate."""
    data = await state.get_data()
    pin = data.get("admin_login_pin", "")
    await _finish_login(message, state, admin_security_service, pin=pin, two_factor_code=message.text.strip())


async def _finish_login(
    message: Message,
    state: FSMContext,
    admin_security_service: AdminSecurityService,
    *,
    pin: str,
    two_factor_code: str | None,
) -> None:
    """Call ``verify_login`` and either unlock the panel or report the failure."""
    admin_id = message.from_user.id if message.from_user else 0
    try:
        session_row = await admin_security_service.verify_login(admin_id, pin=pin, two_factor_code=two_factor_code)
    except AdminLockedOutError as error:
        await state.clear()
        await message.answer(f"\u26D4 {error}")
        return
    except (InvalidTwoFactorCodeError, PermissionDeniedError) as error:
        await state.set_state(SecurityStates.waiting_for_login_pin)
        await message.answer(f"\u274C {error} Qaytadan PIN kodni yuboring:")
        return

    await state.update_data(admin_session_token=session_row.session_token)
    await state.set_state(None)
    await message.answer("\u2705 Kirish tasdiqlandi.", reply_markup=build_admin_main_menu_keyboard())


@router.callback_query(AdminMenuCallback.filter(F.section == "security"))
async def open_security_center(callback: CallbackQuery, admin_security_service: AdminSecurityService) -> None:
    """Show the Security Center action menu."""
    admin_id = callback.from_user.id if callback.from_user else 0
    status = await admin_security_service.get_status(admin_id)
    text = (
        "\U0001F6E1 <b>Xavfsizlik markazi</b>\n\n"
        f"PIN o'rnatilgan: {'\u2705' if status.pin_set else '\u274C'}\n"
        f"2FA yoqilgan: {'\u2705' if status.two_factor_enabled else '\u274C'}\n"
        f"Faol sessiyalar: {status.active_sessions_count}"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text, reply_markup=build_security_keyboard(status.pin_set, status.two_factor_enabled)
        )
    await callback.answer()


@router.callback_query(SecurityActionCallback.filter(F.action == "set_pin"))
async def prompt_set_pin(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt the admin for a new panel-login PIN."""
    await state.set_state(SecurityStates.waiting_for_new_pin)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("\U0001F511 Yangi PIN kodni yuboring (kamida 4 raqam):")
    await callback.answer()


@router.message(SecurityStates.waiting_for_new_pin, F.text)
async def receive_new_pin(
    message: Message, state: FSMContext, admin_security_service: AdminSecurityService
) -> None:
    """Persist the new PIN."""
    await state.clear()
    pin = message.text.strip()
    if len(pin) < 4 or not pin.isdigit():
        await message.answer("\u274C PIN kamida 4 ta raqamdan iborat bo'lishi kerak.")
        return
    admin_id = message.from_user.id if message.from_user else 0
    await admin_security_service.set_pin(admin_id, pin)
    await message.answer("\u2705 PIN muvaffaqiyatli o'rnatildi.")


@router.callback_query(SecurityActionCallback.filter(F.action == "enable_2fa"))
async def enable_two_factor(callback: CallbackQuery, admin_security_service: AdminSecurityService) -> None:
    """Enable 2FA and show the provisioning URI for the admin's TOTP app."""
    admin_id = callback.from_user.id if callback.from_user else 0
    uri = await admin_security_service.enable_two_factor(admin_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\U0001F512 2FA yoqildi. Quyidagi havolani autentifikator ilovangizga qo'shing:\n\n"
            f"<code>{uri}</code>",
            reply_markup=build_security_keyboard(True, True),
        )
    await callback.answer("\u2705 2FA yoqildi")


@router.callback_query(SecurityActionCallback.filter(F.action == "disable_2fa"))
async def disable_two_factor(callback: CallbackQuery, admin_security_service: AdminSecurityService) -> None:
    """Disable 2FA for the current admin."""
    admin_id = callback.from_user.id if callback.from_user else 0
    await admin_security_service.disable_two_factor(admin_id)
    status = await admin_security_service.get_status(admin_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\U0001F513 2FA o'chirildi.", reply_markup=build_security_keyboard(status.pin_set, False)
        )
    await callback.answer("\u2705 2FA o'chirildi")


@router.callback_query(SecurityActionCallback.filter(F.action == "list_sessions"))
async def list_sessions(callback: CallbackQuery, admin_security_service: AdminSecurityService) -> None:
    """List every active session for the current admin."""
    admin_id = callback.from_user.id if callback.from_user else 0
    sessions = await admin_security_service.list_active_sessions(admin_id)
    status = await admin_security_service.get_status(admin_id)
    lines = ["\U0001F4CB <b>Faol sessiyalar</b>", ""]
    if not sessions:
        lines.append("Faol sessiya yo'q.")
    for session_row in sessions:
        lines.append(
            f"\u2022 {session_row.last_seen_at:%Y-%m-%d %H:%M} \u2014 tugaydi: {session_row.expires_at:%Y-%m-%d %H:%M}"
        )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=build_security_keyboard(status.pin_set, status.two_factor_enabled)
        )
    await callback.answer()


@router.callback_query(SecurityActionCallback.filter(F.action == "logout_all"))
async def logout_all_sessions(callback: CallbackQuery, admin_security_service: AdminSecurityService) -> None:
    """Revoke every active session for the current admin."""
    admin_id = callback.from_user.id if callback.from_user else 0
    revoked = await admin_security_service.logout_all(admin_id)
    status = await admin_security_service.get_status(admin_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"\U0001F6AA {revoked} ta sessiya yopildi.",
            reply_markup=build_security_keyboard(status.pin_set, status.two_factor_enabled),
        )
    await callback.answer()


register_admin_plugin(router)
