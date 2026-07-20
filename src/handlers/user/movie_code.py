"""Core feature: user sends a code, bot delivers the linked media as fast as possible.

Also wires in three V4.0 platform features on the delivery path:

* Search History Center -- every attempt (found or not) is recorded via
  :class:`SearchLogService`.
* Advertisement Center -- after a successful delivery, an eligible ad
  campaign (if any) is shown right after the movie.
* Media Protection -- forward/caption protection settings from the
  Settings Center are applied to every delivery.
"""

from __future__ import annotations

import structlog
from aiogram import Bot, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.plugin import register_user_plugin
from src.filters.movie_code_filter import MovieCodeFilter
from src.keyboards.callback_data import ForceSubCheckCallback, ForceSubConfirmCallback
from src.keyboards.inline.force_sub import build_force_sub_gate_keyboard
from src.models.ad_campaign import AdCampaign, AdContentType
from src.models.movie import MediaType, Movie
from src.models.user import User
from src.services.ad_service import AdService
from src.services.admin_service import AdminService
from src.services.force_sub_service import ForceSubService
from src.services.log_service import LogService
from src.services.movie_service import MovieService
from src.services.search_log_service import SearchLogService
from src.services.settings_service import SettingsService
from src.services.user_service import UserService
from src.utils.exceptions import MovieNotFoundError, VisibilityDeniedError
from src.utils.formatters import format_force_sub_gate_message, format_movie_caption
from src.utils.validators import normalize_movie_code

logger = structlog.get_logger(__name__)
router = Router(name="user.movie_code")

_SENDERS = {
    MediaType.VIDEO: "send_video",
    MediaType.DOCUMENT: "send_document",
    MediaType.AUDIO: "send_audio",
    MediaType.PHOTO: "send_photo",
    MediaType.ANIMATION: "send_animation",
}

_FILE_KWARG = {
    "send_video": "video",
    "send_document": "document",
    "send_audio": "audio",
    "send_photo": "photo",
    "send_animation": "animation",
}

_AD_SENDERS = {
    AdContentType.PHOTO: "send_photo",
    AdContentType.VIDEO: "send_video",
    AdContentType.GIF: "send_animation",
}


async def _deliver_movie(
    bot: Bot, chat_id: int, movie: Movie, *, settings_service: SettingsService
) -> None:
    """Send the movie's media to ``chat_id`` as fast as possible, with no re-upload.

    Always prefers ``copy_message`` from the original source message -- a
    single Telegram-side copy operation that never re-downloads or
    re-uploads any bytes through the bot process, regardless of file size.
    Falls back to ``send_<type>`` with the cached ``telegram_file_id`` only
    when no source message is on record (or the source message is gone).

    Media Protection (V4.0): when enabled in the Settings Center,
    ``protect_content=True`` is passed so Telegram disables forwarding and
    saving of the delivered message; when caption protection is enabled the
    caption is stripped to prevent copy-paste redistribution of the code.
    """
    forward_protection = bool(await settings_service.get("media_forward_protection_enabled"))
    caption_protection = bool(await settings_service.get("media_caption_protection_enabled"))
    caption = None if caption_protection else format_movie_caption(movie)

    if movie.source_chat_id is not None and movie.source_message_id is not None:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=movie.source_chat_id,
                message_id=movie.source_message_id,
                caption=caption,
                protect_content=forward_protection,
            )
            return
        except TelegramBadRequest:
            logger.warning("movie.copy_message_failed", code=movie.code)
    method_name = _SENDERS.get(movie.media_type, "send_document")
    method = getattr(bot, method_name)
    await method(
        chat_id=chat_id,
        **{_FILE_KWARG[method_name]: movie.telegram_file_id},
        caption=caption,
        protect_content=forward_protection,
    )


async def _maybe_send_ad(bot: Bot, chat_id: int, campaign: AdCampaign | None) -> None:
    """Send an Advertisement Center campaign right after a movie delivery, if one was picked."""
    if campaign is None:
        return
    reply_markup = None
    if campaign.button_text and campaign.button_url:
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=campaign.button_text, url=campaign.button_url)]]
        )
    if campaign.content_type is AdContentType.TEXT:
        await bot.send_message(chat_id=chat_id, text=campaign.text or "", reply_markup=reply_markup)
        return
    method_name = _AD_SENDERS.get(campaign.content_type, "send_photo")
    method = getattr(bot, method_name)
    file_kwarg = {"send_photo": "photo", "send_video": "video", "send_animation": "animation"}[method_name]
    await method(chat_id=chat_id, **{file_kwarg: campaign.file_id}, caption=campaign.text, reply_markup=reply_markup)


async def _try_deliver(
    message: Message,
    code: str,
    movie_service: MovieService,
    user_service: UserService,
    force_sub_service: ForceSubService,
    admin_service: AdminService,
    log_service: LogService,
    search_log_service: SearchLogService,
    ad_service: AdService,
    settings_service: SettingsService,
    db_user: User | None,
) -> None:
    """Shared delivery flow used by both the plain-text and gate-recheck paths.

    Enforces the mandatory-subscription gate and per-movie visibility rule
    before ever touching Telegram's file-delivery API, per spec ("Obuna
    bo'lmagan foydalanuvchi hech qanday funksiyadan foydalana olmasin").
    Every attempt -- found or not -- is recorded to the Search History
    Center once the force-sub gate has been cleared.
    """
    if message.from_user is None or message.bot is None:
        return

    missing_channels = await force_sub_service.get_missing_channels(
        message.bot, message.from_user.id
    )
    if missing_channels:
        await message.answer(
            format_force_sub_gate_message(missing_channels),
            reply_markup=build_force_sub_gate_keyboard(missing_channels, code),
        )
        return

    try:
        movie = await movie_service.get_by_code(code)
    except MovieNotFoundError:
        await search_log_service.record(query_text=code, found=False, user_id=message.from_user.id)
        raise

    is_admin = await admin_service.is_admin(message.from_user.id)
    try:
        movie_service.assert_visible_to(
            movie,
            is_admin=is_admin,
            is_subscribed=True,
            has_referral=bool(db_user and db_user.referred_by is not None),
            is_premium=bool(db_user and db_user.is_premium),
        )
    except VisibilityDeniedError:
        await search_log_service.record(query_text=code, found=False, user_id=message.from_user.id)
        raise

    await search_log_service.record(query_text=code, found=True, user_id=message.from_user.id)
    await _deliver_movie(message.bot, message.chat.id, movie, settings_service=settings_service)
    await movie_service.register_delivery(movie)
    await user_service.increment_movies_received(message.from_user.id)
    await log_service.record(
        actor_id=message.from_user.id,
        actor_role="user",
        action="movie_delivered",
        entity_type="movie",
        entity_id=movie.code,
    )

    search_count = db_user.searches_count if db_user is not None else 0
    campaign = await ad_service.pick_campaign_for_search_count(search_count)
    await _maybe_send_ad(message.bot, message.chat.id, campaign)


@router.message(MovieCodeFilter())
async def handle_movie_code(
    message: Message,
    movie_service: MovieService,
    user_service: UserService,
    force_sub_service: ForceSubService,
    admin_service: AdminService,
    log_service: LogService,
    search_log_service: SearchLogService,
    ad_service: AdService,
    settings_service: SettingsService,
    db_user: User | None = None,
) -> None:
    """Handle a plain-text message that looks like a movie code."""
    if message.from_user is None or not message.text:
        return

    if db_user is not None:
        await user_service.assert_not_restricted(db_user)

    code = normalize_movie_code(message.text)
    await user_service.increment_search_count(message.from_user.id)

    try:
        await _try_deliver(
            message,
            code,
            movie_service,
            user_service,
            force_sub_service,
            admin_service,
            log_service,
            search_log_service,
            ad_service,
            settings_service,
            db_user,
        )
    except MovieNotFoundError:
        await message.answer(
            f"<code>{code}</code> kodli kino topilmadi. Kodni tekshirib qayta yuboring."
        )
    except VisibilityDeniedError as error:
        await message.answer(str(error))


@router.callback_query(ForceSubCheckCallback.filter())
async def handle_force_sub_recheck(
    callback: CallbackQuery,
    callback_data: ForceSubCheckCallback,
    movie_service: MovieService,
    user_service: UserService,
    force_sub_service: ForceSubService,
    admin_service: AdminService,
    log_service: LogService,
    search_log_service: SearchLogService,
    ad_service: AdService,
    settings_service: SettingsService,
    db_user: User | None = None,
) -> None:
    """Re-check subscription status after the user taps the recheck button.

    ``movie_code == "-"`` means this recheck originated from the /start gate
    (no pending delivery -- just unblock the main menu on success).
    """
    if callback.from_user is None or not isinstance(callback.message, Message) or callback.bot is None:
        await callback.answer()
        return

    if callback_data.movie_code == "-":
        missing = await force_sub_service.get_missing_channels(callback.bot, callback.from_user.id)
        if missing:
            await callback.message.edit_text(
                format_force_sub_gate_message(missing),
                reply_markup=build_force_sub_gate_keyboard(missing, "-"),
            )
            await callback.answer()
            return
        await user_service.record_start(callback.from_user.id)
        await callback.message.edit_text(
            "Obuna tasdiqlandi! Endi kino kodini yuboring, masalan: 1055"
        )
        await callback.answer("OK")
        return

    try:
        await _try_deliver(
            callback.message,
            callback_data.movie_code,
            movie_service,
            user_service,
            force_sub_service,
            admin_service,
            log_service,
            search_log_service,
            ad_service,
            settings_service,
            db_user,
        )
        await callback.answer("OK")
    except MovieNotFoundError:
        await callback.answer("Kino topilmadi.", show_alert=True)
    except VisibilityDeniedError as error:
        await callback.answer(str(error), show_alert=True)


@router.callback_query(ForceSubConfirmCallback.filter())
async def handle_force_sub_confirm(
    callback: CallbackQuery,
    callback_data: ForceSubConfirmCallback,
    force_sub_service: ForceSubService,
) -> None:
    """Record a user's manual "Tasdiqlash" tap for a non-Telegram platform."""
    if callback.from_user is None:
        await callback.answer()
        return
    await force_sub_service.confirm_external(callback.from_user.id, callback_data.channel_id)
    await callback.answer("Tasdiqlandi. Endi 'Tekshirish' tugmasini bosing.")


register_user_plugin(router)
