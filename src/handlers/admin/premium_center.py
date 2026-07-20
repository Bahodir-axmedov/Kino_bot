"""Premium Center (admin): configure pricing & cards, review card payments.

This is the admin-facing counterpart to :mod:`src.handlers.user.premium`.
Pricing, card number and the payment on/off toggles all live in the
Settings Center under the ``premium`` category, so the "edit price / card"
button simply deep-links there. This module additionally owns the card
payment approval queue (approve -> grant Premium, reject -> notify user).
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, PaymentReviewCallback
from src.keyboards.inline.admin_panel import (
    build_admin_premium_keyboard,
    build_payment_review_keyboard,
)
from src.keyboards.inline.premium import format_amount
from src.models.payment_request import PaymentRequest, PaymentStatus
from src.services.log_service import LogService
from src.services.payment_service import PaymentService
from src.services.premium_service import PremiumService
from src.services.settings_service import SettingsService
from src.utils.exceptions import InvalidInputError

router = Router(name="admin.premium_center")


async def _summary_text(settings_service: SettingsService, pending_count: int) -> str:
    """Render the Premium Center dashboard text from current settings."""
    enabled = bool(await settings_service.get("premium_enabled"))
    stars_enabled = bool(await settings_service.get("stars_payment_enabled"))
    card_enabled = bool(await settings_service.get("card_payment_enabled"))
    stars_price = int(await settings_service.get("premium_price_stars"))
    uzs_price = int(await settings_service.get("premium_price_uzs"))
    days = int(await settings_service.get("premium_duration_days"))
    card_number = str(await settings_service.get("payment_card_number") or "\u2014")
    card_holder = str(await settings_service.get("payment_card_holder") or "\u2014")
    card_bank = str(await settings_service.get("payment_card_bank") or "\u2014")
    return (
        "\U0001F48E <b>Premium markazi</b>\n\n"
        f"Holat: {'\u2705 yoqilgan' if enabled else '\u274C o\u2018chirilgan'}\n"
        f"\U0001F4E6 Muddat: <b>{days} kun</b>\n\n"
        f"\u2B50\uFE0F Stars to\u2018lovi: {'\u2705' if stars_enabled else '\u274C'} \u2014 "
        f"<b>{stars_price}</b> yulduz\n"
        f"\U0001F4B3 Karta to\u2018lovi: {'\u2705' if card_enabled else '\u274C'} \u2014 "
        f"<b>{format_amount(uzs_price)}</b> so\u2018m\n\n"
        f"\U0001F3E6 Karta ({card_bank}): <code>{card_number}</code>\n"
        f"\U0001F464 Karta egasi: {card_holder}\n\n"
        f"\U0001F9FE Kutilayotgan to\u2018lovlar: <b>{pending_count}</b>\n\n"
        "Narx, karta raqami va to\u2018lov usullarini o\u2018zgartirish uchun "
        "\u00ABNarx va karta sozlamalari\u00BB tugmasini bosing."
    )


@router.callback_query(AdminMenuCallback.filter(F.section == "premium_center"))
async def open_premium_center(
    callback: CallbackQuery,
    settings_service: SettingsService,
    payment_service: PaymentService,
) -> None:
    """Show the Premium Center dashboard (config summary + pending count)."""
    pending_count = await payment_service.pending_count()
    text = await _summary_text(settings_service, pending_count)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text, reply_markup=build_admin_premium_keyboard(pending_count)
        )
    await callback.answer()


def _request_caption(request: PaymentRequest) -> str:
    """Render the admin-facing caption for one pending card payment."""
    return (
        "\U0001F9FE <b>Karta to\u2018lovi</b>\n\n"
        f"\U0001F194 So\u2018rov: <code>{request.id}</code>\n"
        f"\U0001F464 Foydalanuvchi: <code>{request.user_id}</code>\n"
        f"\U0001F4B0 {format_amount(request.amount)} {request.currency}\n"
        f"\U0001F4E6 {request.days} kun\n\n"
        "Tasdiqlaysizmi?"
    )


@router.callback_query(AdminMenuCallback.filter(F.section == "premium_payments"))
async def list_pending_payments(
    callback: CallbackQuery, payment_service: PaymentService
) -> None:
    """List up to 10 pending card payments, each with approve/reject buttons."""
    if not isinstance(callback.message, Message) or callback.bot is None:
        await callback.answer()
        return
    pending = await payment_service.list_pending(limit=10)
    if not pending:
        await callback.answer("Kutilayotgan to\u2018lovlar yo\u2018q.", show_alert=True)
        return
    chat_id = callback.message.chat.id
    await callback.bot.send_message(
        chat_id=chat_id, text=f"\U0001F9FE Kutilayotgan to\u2018lovlar: {len(pending)} ta"
    )
    for request in pending:
        caption = _request_caption(request)
        keyboard = build_payment_review_keyboard(request.id)
        if request.receipt_file_id:
            await callback.bot.send_photo(
                chat_id=chat_id,
                photo=request.receipt_file_id,
                caption=caption,
                reply_markup=keyboard,
            )
        else:
            await callback.bot.send_message(
                chat_id=chat_id, text=caption, reply_markup=keyboard
            )
    await callback.answer()


@router.callback_query(PaymentReviewCallback.filter(F.action == "approve"))
async def approve_payment(
    callback: CallbackQuery,
    callback_data: PaymentReviewCallback,
    payment_service: PaymentService,
    premium_service: PremiumService,
    log_service: LogService,
) -> None:
    """Approve a card payment and grant the user Premium immediately."""
    admin_id = callback.from_user.id if callback.from_user else None
    try:
        request = await payment_service.mark_reviewed(
            callback_data.request_id, status=PaymentStatus.APPROVED, reviewed_by=admin_id
        )
    except InvalidInputError as error:
        await callback.answer(str(error), show_alert=True)
        return
    try:
        await premium_service.grant(
            request.user_id, days=request.days, plan="premium_card", granted_by=admin_id
        )
    except InvalidInputError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await log_service.record(
        actor_id=admin_id or 0,
        actor_role="admin",
        action="premium_payment_approved",
        entity_type="payment_request",
        entity_id=str(request.id),
        new_value={"user_id": request.user_id, "days": request.days},
    )
    if callback.bot is not None:
        try:
            await callback.bot.send_message(
                chat_id=request.user_id,
                text=(
                    f"\u2705 To\u2018lovingiz tasdiqlandi! {request.days} kunlik Premium "
                    "faollashtirildi. Rahmat! \u2B50\uFE0F"
                ),
            )
        except TelegramAPIError:  # pragma: no cover - best effort notify
            pass
    await _mark_review_done(callback, "\u2705 <b>Tasdiqlandi</b>")
    await callback.answer("\u2705 Tasdiqlandi")


@router.callback_query(PaymentReviewCallback.filter(F.action == "reject"))
async def reject_payment(
    callback: CallbackQuery,
    callback_data: PaymentReviewCallback,
    payment_service: PaymentService,
    log_service: LogService,
) -> None:
    """Reject a card payment and notify the user."""
    admin_id = callback.from_user.id if callback.from_user else None
    try:
        request = await payment_service.mark_reviewed(
            callback_data.request_id, status=PaymentStatus.REJECTED, reviewed_by=admin_id
        )
    except InvalidInputError as error:
        await callback.answer(str(error), show_alert=True)
        return
    await log_service.record(
        actor_id=admin_id or 0,
        actor_role="admin",
        action="premium_payment_rejected",
        entity_type="payment_request",
        entity_id=str(request.id),
    )
    if callback.bot is not None:
        try:
            await callback.bot.send_message(
                chat_id=request.user_id,
                text=(
                    "\u274C To\u2018lovingiz tasdiqlanmadi. Iltimos, to\u2018lov "
                    "ma\u2019lumotlarini tekshirib qayta urinib ko\u2018ring yoki "
                    "administrator bilan bog\u2018laning."
                ),
            )
        except TelegramAPIError:  # pragma: no cover - best effort notify
            pass
    await _mark_review_done(callback, "\u274C <b>Rad etildi</b>")
    await callback.answer("\u274C Rad etildi")


async def _mark_review_done(callback: CallbackQuery, status_text: str) -> None:
    """Append a resolution note to the admin's review message and drop its buttons."""
    message = callback.message
    if not isinstance(message, Message):
        return
    try:
        if message.caption is not None:
            await message.edit_caption(
                caption=f"{message.caption}\n\n{status_text}", reply_markup=None
            )
        elif message.text is not None:
            await message.edit_text(f"{message.text}\n\n{status_text}", reply_markup=None)
        else:
            await message.answer(status_text)
    except TelegramAPIError:  # pragma: no cover - best effort edit
        pass


register_admin_plugin(router)
