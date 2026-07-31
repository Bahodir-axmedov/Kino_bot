"""Admin management of movie media sources (channels/groups the bot reads from).

Like Force Subscribe, adding a source requires ZERO typing: the admin adds
the bot to the channel/group, then taps it from the auto-discovered list.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import (
    AdminMenuCallback,
    DiscoveredChatCallback,
    MediaSourceActionCallback,
    MediaSourceTypeCallback,
)
from src.keyboards.inline.admin_panel import (
    build_back_to_admin_menu_keyboard,
    build_media_source_type_keyboard,
    build_media_sources_keyboard,
)
from src.keyboards.inline.discovery import build_discovered_chat_picker_keyboard
from src.models.discovered_chat import DiscoveredChatType
from src.models.media_source import MediaSourceType
from src.services.discovered_chat_service import DiscoveredChatService
from src.services.log_service import LogService
from src.services.media_source_service import MediaSourceService

router = Router(name="admin.media_sources")

# Short callback codes (see src.keyboards.callback_data).
_TYPE_TO_CODE: dict[MediaSourceType, str] = {
    MediaSourceType.CHANNEL: "ch",
    MediaSourceType.GROUP: "gr",
}
_CODE_TO_TYPE: dict[str, MediaSourceType] = {v: k for k, v in _TYPE_TO_CODE.items()}
_MEDIA_TO_DISCOVERED: dict[MediaSourceType, DiscoveredChatType] = {
    MediaSourceType.CHANNEL: DiscoveredChatType.CHANNEL,
    MediaSourceType.GROUP: DiscoveredChatType.GROUP,
}


@router.callback_query(AdminMenuCallback.filter(F.section == "media_sources"))
async def open_media_sources_menu(
    callback: CallbackQuery, media_source_service: MediaSourceService
) -> None:
    """Show every configured media source with remove buttons plus an add button."""
    sources = await media_source_service.list_active()
    text = (
        "Media manbalari (kinolar shu yerdan o'qiladi)."
        if sources
        else "Hozircha media manbalari yo'q. Botni kanal/guruhga qo'shing va tanlang."
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text, reply_markup=build_media_sources_keyboard(sources)
        )
    await callback.answer()


@router.callback_query(MediaSourceActionCallback.filter(F.action == "add"))
async def start_add_source(callback: CallbackQuery) -> None:
    """Ask whether the new source is a channel or a group."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Manba turini tanlang:", reply_markup=build_media_source_type_keyboard()
        )
    await callback.answer()


@router.callback_query(MediaSourceTypeCallback.filter())
async def choose_source_type(
    callback: CallbackQuery,
    callback_data: MediaSourceTypeCallback,
    discovered_chat_service: DiscoveredChatService,
) -> None:
    """Show the tap-to-pick list of discovered chats of the chosen type."""
    source_type = _CODE_TO_TYPE.get(callback_data.source_type, MediaSourceType.CHANNEL)
    chat_type = _MEDIA_TO_DISCOVERED[source_type]
    chats = await discovered_chat_service.list_available(chat_type)
    if not chats:
        kind = "kanal" if chat_type == DiscoveredChatType.CHANNEL else "guruh"
        text = (
            f"Hali hech qanday {kind} topilmadi.\n\n"
            f"Botni kerakli {kind}ga administrator qilib qo'shing \u2014 "
            "u avtomatik ravishda shu ro'yxatda paydo bo'ladi."
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
                purpose="ms",
                sub_type=_TYPE_TO_CODE[source_type],
                back_section="media_sources",
            ),
        )
    await callback.answer()


@router.callback_query(DiscoveredChatCallback.filter(F.purpose == "ms"))
async def pick_discovered_source(
    callback: CallbackQuery,
    callback_data: DiscoveredChatCallback,
    media_source_service: MediaSourceService,
    discovered_chat_service: DiscoveredChatService,
    log_service: LogService,
) -> None:
    """Register a tapped, already-discovered Telegram chat as a media source."""
    source_type = _CODE_TO_TYPE.get(callback_data.sub_type, MediaSourceType.CHANNEL)
    discovered = await discovered_chat_service.get_by_chat_id(callback_data.chat_id)
    if discovered is None:
        await callback.answer("Chat topilmadi.", show_alert=True)
        return
    source = await media_source_service.add_source(
        chat_id=discovered.chat_id,
        title=discovered.title,
        source_type=source_type,
    )
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="media_source_added",
        entity_type="media_source",
        entity_id=str(source.chat_id),
    )
    sources = await media_source_service.list_active()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"'{source.title}' media manbalariga qo'shildi.",
            reply_markup=build_media_sources_keyboard(sources),
        )
    await callback.answer("Qo'shildi.")


@router.callback_query(MediaSourceActionCallback.filter(F.action == "remove"))
async def remove_source(
    callback: CallbackQuery,
    callback_data: MediaSourceActionCallback,
    media_source_service: MediaSourceService,
    log_service: LogService,
) -> None:
    """Deactivate a media source and refresh the list."""
    removed = await media_source_service.remove_source(callback_data.chat_id)
    if removed:
        await log_service.record(
            actor_id=callback.from_user.id,
            actor_role="admin",
            action="media_source_removed",
            entity_type="media_source",
            entity_id=str(callback_data.chat_id),
        )
    sources = await media_source_service.list_active()
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(
            reply_markup=build_media_sources_keyboard(sources)
        )
    await callback.answer("O'chirildi." if removed else "Topilmadi.")


@router.callback_query(MediaSourceActionCallback.filter(F.action == "noop"))
async def noop(callback: CallbackQuery) -> None:
    """Absorb taps on non-interactive rows."""
    await callback.answer()


register_admin_plugin(router)
