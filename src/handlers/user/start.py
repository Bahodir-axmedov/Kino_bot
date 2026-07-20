"""``/start`` registration, mandatory force-subscribe gate, referral capture, menu."""

from __future__ import annotations

import structlog
from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from src.core.plugin import register_user_plugin
from src.keyboards.inline.force_sub import build_force_sub_gate_keyboard
from src.keyboards.reply.main_menu import build_main_menu_keyboard
from src.services.admin_service import AdminService
from src.services.blacklist_service import BlacklistService
from src.services.force_sub_service import ForceSubService
from src.services.log_service import LogService
from src.services.settings_service import SettingsService
from src.services.user_service import UserService
from src.utils.formatters import format_force_sub_gate_message

logger = structlog.get_logger(__name__)
router = Router(name="user.start")


@router.message(CommandStart())
async def handle_start(
    message: Message,
    command: CommandObject,
    user_service: UserService,
    force_sub_service: ForceSubService,
    log_service: LogService,
    settings_service: SettingsService,
    blacklist_service: BlacklistService,
    admin_service: AdminService,
) -> None:
    """Register the user, enforce Maintenance Mode / Blacklist / force-subscribe gates, then greet them.

    Per spec, the force-subscribe gate is checked on every /start (in addition
    to every code request in movie_code.py) and blocks every other bot
    function until the user has joined/confirmed every mandatory target.
    Maintenance Mode and Blacklist are checked first: only active admins may
    use the bot while Maintenance Mode is ON, and blacklisted users are
    always rejected regardless of mode.
    """
    if message.from_user is None or message.bot is None:
        return

    if await blacklist_service.is_user_blocked(
        telegram_id=message.from_user.id, username=message.from_user.username
    ):
        await message.answer("Siz botdan foydalanishdan bloklangansiz.")
        return

    if await settings_service.is_maintenance_mode() and not await admin_service.is_admin(
        message.from_user.id
    ):
        await message.answer(await settings_service.maintenance_message())
        return

    referred_by: int | None = None
    if command.args and command.args.isdigit():
        referred_by = int(command.args)

    user, is_new = await user_service.get_or_register(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code,
        referred_by=referred_by,
    )

    if is_new:
        await log_service.record(
            actor_id=message.from_user.id,
            actor_role="user",
            action="user_registered",
            entity_type="user",
            entity_id=str(message.from_user.id),
            new_value={"referred_by": referred_by},
        )

    missing_channels = await force_sub_service.get_missing_channels(
        message.bot, message.from_user.id
    )
    if missing_channels:
        await message.answer(
            format_force_sub_gate_message(missing_channels),
            reply_markup=build_force_sub_gate_keyboard(missing_channels, "-"),
        )
        return

    await user_service.record_start(message.from_user.id)
    await message.answer(
        "Kino Bot ga xush kelibsiz!\n\n"
        "Kino kodini yuboring va men sizga filmni yuboraman.\n"
        "Masalan: 1055",
        reply_markup=build_main_menu_keyboard(),
    )


register_user_plugin(router)
