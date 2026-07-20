"""Admin management of the mandatory-subscription (force-subscribe) center.

Telegram-native targets (channel / group / discussion group) are added with
ZERO typing: the admin just adds the bot to the chat, then taps it from the
auto-discovered list. External platforms (Instagram/YouTube/etc.) still use a
short title -> URL -> instructions text flow because the bot cannot discover
or verify them automatically.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import (
    AdminMenuCallback,
    DiscoveredChatCallback,
    ForceSubActionCallback,
    ForceSubPlatformCallback,
)
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard
from src.keyboards.inline.discovery import build_discovered_chat_picker_keyboard
from src.keyboards.inline.force_sub import (
    build_force_sub_admin_list_keyboard,
    build_platform_selection_keyboard,
)
from src.models.discovered_chat import DiscoveredChatType
from src.models.force_sub_channel import TELEGRAM_AUTO_VERIFIABLE_PLATFORMS, ForceSubPlatform
from src.services.discovered_chat_service import DiscoveredChatService
from src.services.force_sub_service import ForceSubService
from src.services.log_service import LogService
from src.states.force_sub_states import ForceSubStates
from src.utils.validators import validate_non_empty_text

router = Router(name="admin.force_sub")

# Short callback codes (see src.keyboards.callback_data) mapped to the
# Telegram-auto-verifiable platforms they represent.
_PLATFORM_TO_CODE: dict[ForceSubPlatform, str] = {
    ForceSubPlatform.TELEGRAM_CHANNEL: "tc",
    ForceSubPlatform.TELEGRAM_GROUP: "tg",
    ForceSubPlatform.TELEGRAM_DISCUSSION_GROUP: "tdg",
}
_CODE_TO_PLATFORM: dict[str, ForceSubPlatform] = {v: k for k, v in _PLATFORM_TO_CODE.items()}


def _discovered_type_for(platform: ForceSubPlatform) -> DiscoveredChatType:
    """Map a force-sub Telegram platform to the discovered-chat kind to list."""
    if platform == ForceSubPlatform.TELEGRAM_CHANNEL:
        return DiscoveredChatType.CHANNEL
    return DiscoveredChatType.GROUP


@router.callback_query(AdminMenuCallback.filter(F.section == "force_sub"))
async def open_force_sub_menu(callback: CallbackQuery, force_sub_service: ForceSubService) -> None:
    """Show every configured mandatory-subscription target."""
    channels = await force_sub_service.list_all()
    text = (
        "Majburiy obuna markazi.\n\n1-qator: nomi. 2-qator: Aktiv/Noaktiv, "
        "Majburiy/Ixtiyoriy, O'chirish."
        if channels
        else "Hozircha majburiy obuna nishonlari yo'q."
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text, reply_markup=build_force_sub_admin_list_keyboard(channels)
        )
    await callback.answer()


@router.callback_query(ForceSubActionCallback.filter(F.action == "add"))
async def start_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the add-target flow by asking which platform to add."""
    await state.set_state(ForceSubStates.choosing_platform)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Qaysi platforma turini qo'shmoqchisiz?",
            reply_markup=build_platform_selection_keyboard(),
        )
    await callback.answer()


@router.callback_query(ForceSubActionCallback.filter(F.action == "cancel_add"))
async def cancel_add_channel(
    callback: CallbackQuery, state: FSMContext, force_sub_service: ForceSubService
) -> None:
    """Abort the add-target flow and return to the list."""
    await state.clear()
    channels = await force_sub_service.list_all()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Bekor qilindi.", reply_markup=build_force_sub_admin_list_keyboard(channels)
        )
    await callback.answer()


@router.callback_query(ForceSubStates.choosing_platform, ForceSubPlatformCallback.filter())
async def choose_platform(
    callback: CallbackQuery,
    callback_data: ForceSubPlatformCallback,
    state: FSMContext,
    discovered_chat_service: DiscoveredChatService,
) -> None:
    """Branch: Telegram platforms -> tap-to-pick list; others -> typed flow."""
    platform = ForceSubPlatform(callback_data.platform)
    if platform in TELEGRAM_AUTO_VERIFIABLE_PLATFORMS:
        # Zero-typing path: list the chats the bot was already added to.
        await state.clear()
        chat_type = _discovered_type_for(platform)
        chats = await discovered_chat_service.list_available(chat_type)
        if not chats:
            kind = "kanal" if chat_type == DiscoveredChatType.CHANNEL else "guruh"
            text = (
                f"Hali hech qanday {kind} topilmadi.\n\n"
                f"Botni kerakli {kind}ga administrator qilib qo'shing \u2014 "
                "u avtomatik ravishda shu ro'yxatda paydo bo'ladi, "
                "hech narsa yozishingiz shart emas."
            )
            if isinstance(callback.message, Message):
                await callback.message.edit_text(
                    text, reply_markup=build_back_to_admin_menu_keyboard()
                )
            await callback.answer()
            return
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "Ro'yxatdan kerakli chatni tanlang (yozish shart emas):",
                reply_markup=build_discovered_chat_picker_keyboard(
                    chats,
                    purpose="fs",
                    sub_type=_PLATFORM_TO_CODE[platform],
                    back_section="force_sub",
                ),
            )
        await callback.answer()
        return
    # External / manually verified platform: collect title -> url -> instructions.
    await state.update_data(platform=platform.value)
    await state.set_state(ForceSubStates.waiting_for_title)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("Nomini yuboring (foydalanuvchiga ko'rsatiladi):")
    await callback.answer()


@router.callback_query(DiscoveredChatCallback.filter(F.purpose == "fs"))
async def pick_discovered_channel(
    callback: CallbackQuery,
    callback_data: DiscoveredChatCallback,
    state: FSMContext,
    force_sub_service: ForceSubService,
    discovered_chat_service: DiscoveredChatService,
    log_service: LogService,
) -> None:
    """Register a tapped, already-discovered Telegram chat as a force-sub target."""
    await state.clear()
    platform = _CODE_TO_PLATFORM.get(callback_data.sub_type, ForceSubPlatform.TELEGRAM_CHANNEL)
    discovered = await discovered_chat_service.get_by_chat_id(callback_data.chat_id)
    if discovered is None:
        await callback.answer("Chat topilmadi.", show_alert=True)
        return
    channel = await force_sub_service.add_telegram_channel(
        platform=platform,
        chat_id=discovered.chat_id,
        title=discovered.title,
        chat_username=discovered.chat_username,
        invite_link=None,
        is_mandatory=True,
        added_by=callback.from_user.id,
    )
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="force_sub_channel_added",
        entity_type="force_sub_channel",
        entity_id=str(channel.chat_id),
    )
    channels = await force_sub_service.list_all()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"'{channel.title}' majburiy obuna ro'yxatiga qo'shildi.",
            reply_markup=build_force_sub_admin_list_keyboard(channels),
        )
    await callback.answer("Qo'shildi.")


@router.message(ForceSubStates.waiting_for_title, F.text)
async def receive_title(message: Message, state: FSMContext) -> None:
    """Capture the display title for a non-Telegram subscription target."""
    if not message.text:
        return
    title = validate_non_empty_text(message.text, field_name="Nom", max_length=128)
    await state.update_data(title=title)
    await state.set_state(ForceSubStates.waiting_for_url)
    await message.answer("Havolasini (URL) yuboring:")


@router.message(ForceSubStates.waiting_for_url, F.text)
async def receive_url(message: Message, state: FSMContext) -> None:
    """Capture the join/profile URL for a non-Telegram subscription target."""
    if not message.text:
        return
    url = validate_non_empty_text(message.text, field_name="URL", max_length=512)
    await state.update_data(url=url)
    await state.set_state(ForceSubStates.waiting_for_instructions)
    await message.answer(
        "Foydalanuvchi uchun ko'rsatma matnini yuboring "
        "(masalan: 'Follow qiling, keyin tugmani bosing'), yoki /skip yuboring:"
    )


@router.message(ForceSubStates.waiting_for_instructions, F.text)
async def receive_instructions(
    message: Message,
    state: FSMContext,
    force_sub_service: ForceSubService,
    log_service: LogService,
) -> None:
    """Capture optional instructions and persist the new external target."""
    data = await state.get_data()
    await state.clear()
    if not message.text:
        return
    instructions = None if message.text.strip() == "/skip" else message.text.strip()
    platform = ForceSubPlatform(data["platform"])
    channel = await force_sub_service.add_external_target(
        platform=platform,
        title=data["title"],
        url=data["url"],
        instructions=instructions,
        is_mandatory=True,
        added_by=message.from_user.id if message.from_user else 0,
    )
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="force_sub_channel_added",
        entity_type="force_sub_channel",
        entity_id=str(channel.id),
    )
    await message.answer(f"'{channel.title}' majburiy obuna ro'yxatiga qo'shildi.")


@router.callback_query(ForceSubActionCallback.filter(F.action == "toggle"))
async def toggle_channel(
    callback: CallbackQuery,
    callback_data: ForceSubActionCallback,
    force_sub_service: ForceSubService,
) -> None:
    """Toggle a target's Aktiv/Noaktiv state and refresh the list."""
    await force_sub_service.toggle_channel(callback_data.channel_id)
    channels = await force_sub_service.list_all()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(
            reply_markup=build_force_sub_admin_list_keyboard(channels)
        )
    await callback.answer("Yangilandi.")


@router.callback_query(ForceSubActionCallback.filter(F.action == "toggle_mandatory"))
async def toggle_mandatory(
    callback: CallbackQuery,
    callback_data: ForceSubActionCallback,
    force_sub_service: ForceSubService,
) -> None:
    """Toggle a target between Majburiy (mandatory) and Ixtiyoriy (optional)."""
    await force_sub_service.toggle_mandatory(callback_data.channel_id)
    channels = await force_sub_service.list_all()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(
            reply_markup=build_force_sub_admin_list_keyboard(channels)
        )
    await callback.answer("Yangilandi.")


@router.callback_query(ForceSubActionCallback.filter(F.action == "remove"))
async def remove_channel(
    callback: CallbackQuery,
    callback_data: ForceSubActionCallback,
    force_sub_service: ForceSubService,
    log_service: LogService,
) -> None:
    """Permanently remove a mandatory-subscription target."""
    removed = await force_sub_service.remove_channel(callback_data.channel_id)
    if removed:
        await log_service.record(
            actor_id=callback.from_user.id,
            actor_role="admin",
            action="force_sub_channel_removed",
            entity_type="force_sub_channel",
            entity_id=str(callback_data.channel_id),
        )
    channels = await force_sub_service.list_all()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(
            reply_markup=build_force_sub_admin_list_keyboard(channels)
        )
    await callback.answer("O'chirildi." if removed else "Topilmadi.")


@router.callback_query(ForceSubActionCallback.filter(F.action == "noop"))
async def noop(callback: CallbackQuery) -> None:
    """Absorb taps on the non-interactive title row."""
    await callback.answer()


register_admin_plugin(router)
