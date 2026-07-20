"""Admin broadcast/advertisement composition and delivery."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, BroadcastConfirmCallback
from src.services.broadcast_service import BroadcastService
from src.services.log_service import LogService
from src.states.broadcast_states import BroadcastStates

router = Router(name="admin.broadcast")

_CONTENT_TYPE_ATTRS = ("photo", "video", "animation", "document", "audio")


@router.callback_query(AdminMenuCallback.filter(F.section == "broadcast"))
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the broadcast composition FSM flow."""
    await state.set_state(BroadcastStates.waiting_for_content)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "📢 Yubormoqchi bo'lgan xabarni yuboring "
            "(matn, rasm, video, animatsiya, hujjat yoki audio):"
        )
    await callback.answer()


@router.message(BroadcastStates.waiting_for_content)
async def receive_content(message: Message, state: FSMContext) -> None:
    """Capture the composed message and ask about an optional inline button."""
    content_type = "text"
    for attr in _CONTENT_TYPE_ATTRS:
        if getattr(message, attr, None):
            content_type = attr
            break

    await state.update_data(
        content_type=content_type,
        source_chat_id=message.chat.id,
        source_message_id=message.message_id,
        message_text=message.text or message.caption,
    )
    await state.set_state(BroadcastStates.waiting_for_buttons)
    await message.answer(
        "🔗 Inline tugma qo'shmoqchimisiz? \"Matn|URL\" formatida yuboring yoki /skip:"
    )


@router.message(BroadcastStates.waiting_for_buttons, F.text)
async def receive_buttons(message: Message, state: FSMContext) -> None:
    """Capture an optional inline button, then ask for final confirmation."""
    reply_markup: InlineKeyboardMarkup | None = None
    if message.text.strip() != "/skip" and "|" in message.text:
        label, url = (part.strip() for part in message.text.split("|", 1))
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=label, url=url)]]
        )

    await state.update_data(
        reply_markup_json=reply_markup.model_dump_json() if reply_markup else None
    )
    await state.set_state(BroadcastStates.confirm)
    await message.answer(
        "✅ Tayyor. Yuborishni tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Yuborish",
                        callback_data=BroadcastConfirmCallback(action="send").pack(),
                    ),
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data=BroadcastConfirmCallback(action="cancel").pack(),
                    ),
                ]
            ]
        ),
    )


@router.callback_query(BroadcastStates.confirm, BroadcastConfirmCallback.filter(F.action == "cancel"))
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the pending broadcast composition."""
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.edit_text("❌ Broadcast bekor qilindi.")
    await callback.answer()


@router.callback_query(BroadcastStates.confirm, BroadcastConfirmCallback.filter(F.action == "send"))
async def confirm_broadcast(
    callback: CallbackQuery,
    state: FSMContext,
    broadcast_service: BroadcastService,
    log_service: LogService,
) -> None:
    """Persist the campaign and dispatch it to every non-banned user."""
    data = await state.get_data()
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup as _Markup

    reply_markup = (
        _Markup.model_validate_json(data["reply_markup_json"])
        if data.get("reply_markup_json")
        else None
    )

    campaign = await broadcast_service.create_campaign(
        admin_id=callback.from_user.id,
        content_type=data["content_type"],
        source_chat_id=data["source_chat_id"],
        source_message_id=data["source_message_id"],
        message_text=data.get("message_text"),
        reply_markup=reply_markup,
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text("📢 Yuborilmoqda... Bu biroz vaqt olishi mumkin.")

    if callback.bot is not None:
        campaign = await broadcast_service.send_campaign(callback.bot, campaign)

    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="broadcast_sent",
        entity_type="broadcast",
        entity_id=str(campaign.id),
        new_value={"sent": campaign.sent_count, "failed": campaign.failed_count},
    )

    if isinstance(callback.message, Message):
        await callback.message.answer(
            f"✅ Yuborildi: {campaign.sent_count}\n❌ Xato: {campaign.failed_count}\n"
            f"👥 Jami: {campaign.total_users}"
        )
    await callback.answer()


register_admin_plugin(router)
