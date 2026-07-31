"""End-user Premium screen + purchase flow (Telegram Stars & Uzcard/Humo card).

Two payment methods are offered, both driven by admin-editable settings
(price, card number, on/off toggles) from the Settings Center:

* **Telegram Stars (XTR)** -- fully automatic. We send a native Telegram
  invoice; on ``successful_payment`` Premium is granted instantly.
* **Uzcard / Humo card** -- manual. The user is shown the admin's card
  number, transfers the money, then uploads a receipt screenshot. That
  creates a PENDING payment request which an admin approves from the panel.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from src.config import Settings
from src.core.plugin import register_user_plugin
from src.keyboards.callback_data import PremiumBuyCallback
from src.keyboards.inline.admin_panel import build_payment_review_keyboard
from src.keyboards.inline.premium import (
    build_card_paid_keyboard,
    build_premium_purchase_keyboard,
    format_amount,
)
from src.models.payment_request import PaymentMethod, PaymentRequest, PaymentStatus
from src.services.log_service import LogService
from src.services.payment_service import PaymentService
from src.services.premium_service import PremiumService
from src.services.settings_service import SettingsService
from src.services.user_service import UserService
from src.states.user_states import PremiumPurchaseStates
from src.utils.exceptions import InvalidInputError
from src.utils.formatters import format_datetime

router = Router(name="user.premium")


async def _load_config(settings_service: SettingsService) -> dict[str, object]:
    """Read every admin-configurable Premium/payment value in one place."""
    return {
        "enabled": bool(await settings_service.get("premium_enabled")),
        "stars_enabled": bool(await settings_service.get("stars_payment_enabled")),
        "card_enabled": bool(await settings_service.get("card_payment_enabled")),
        "stars_price": int(await settings_service.get("premium_price_stars")),
        "uzs_price": int(await settings_service.get("premium_price_uzs")),
        "days": int(await settings_service.get("premium_duration_days")),
        "card_number": str(await settings_service.get("payment_card_number") or ""),
        "card_holder": str(await settings_service.get("payment_card_holder") or ""),
        "card_bank": str(await settings_service.get("payment_card_bank") or ""),
        "features": str(await settings_service.get("premium_features_text") or ""),
    }


def _default_features() -> str:
    """Return the default Premium benefits blurb when admin has not set one."""
    return (
        "\u2705 Yopiq (Premium-only) kinolarga to'liq kirish\n"
        "\u2705 Reklamasiz foydalanish\n"
        "\u2705 Tezkor va imtiyozli qo'llab-quvvatlash"
    )


@router.message(F.text == "\u2B50\uFE0F Premium")
async def show_premium(
    message: Message,
    settings_service: SettingsService,
    premium_service: PremiumService,
    user_service: UserService,
) -> None:
    """Show Premium status plus the (admin-configured) purchase options."""
    if message.from_user is None:
        return
    config = await _load_config(settings_service)
    if not config["enabled"]:
        await message.answer("\u2B50\uFE0F Premium hozircha vaqtincha o'chirilgan.")
        return

    user = await user_service.find_by_identifier(str(message.from_user.id))
    if user is None:
        await message.answer("Profil topilmadi. Iltimos, /start buyrug'ini yuboring.")
        return

    features = str(config["features"]).strip() or _default_features()
    days = int(config["days"])

    if PremiumService.is_active(user):
        expiry = format_datetime(user.premium_expires_at) if user.premium_expires_at else "muddatsiz"
        header = (
            "\u2B50\uFE0F <b>Premium holati</b>\n\n"
            "\u2705 Sizda Premium faol.\n"
            f"\u23F3 Tugash sanasi: <b>{expiry}</b>\n\n"
            "Muddatni uzaytirish uchun quyidagi to'lov usullaridan birini tanlang:"
        )
    else:
        header = (
            "\u2B50\uFE0F <b>Premium</b>\n\n"
            f"{features}\n\n"
            f"\U0001F4E6 Obuna muddati: <b>{days} kun</b>\n\n"
            "To'lov usulini tanlang:"
        )

    price_lines = []
    if config["stars_enabled"]:
        price_lines.append(f"\u2B50\uFE0F Telegram Stars: <b>{config['stars_price']}</b> yulduz")
    if config["card_enabled"]:
        price_lines.append(
            f"\U0001F4B3 Uzcard / Humo: <b>{format_amount(int(config['uzs_price']))}</b> so'm"
        )

    if not price_lines:
        await message.answer(
            f"{header}\n\n\u2139\uFE0F Hozircha to'lov usullari mavjud emas. "
            "Iltimos, administrator bilan bog'laning."
        )
        return

    keyboard = build_premium_purchase_keyboard(
        stars_enabled=bool(config["stars_enabled"]),
        card_enabled=bool(config["card_enabled"]),
        stars_price=int(config["stars_price"]),
        uzs_price=int(config["uzs_price"]),
    )
    await message.answer(f"{header}\n\n" + "\n".join(price_lines), reply_markup=keyboard)


@router.callback_query(PremiumBuyCallback.filter(F.method == "stars"))
async def buy_with_stars(
    callback: CallbackQuery, settings_service: SettingsService
) -> None:
    """Send a native Telegram Stars (XTR) invoice for a Premium subscription."""
    config = await _load_config(settings_service)
    if not config["enabled"] or not config["stars_enabled"]:
        await callback.answer("\u2B50\uFE0F Stars to'lovi o'chirilgan.", show_alert=True)
        return
    price = int(config["stars_price"])
    days = int(config["days"])
    if price <= 0:
        await callback.answer("Narx sozlanmagan. Administrator bilan bog'laning.", show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.answer_invoice(
            title=f"{days} kunlik Premium",
            description=f"{days} kunlik Premium obuna. To'lov Telegram Stars orqali amalga oshiriladi.",
            payload=f"premium:{days}",
            currency="XTR",
            prices=[LabeledPrice(label=f"{days} kunlik Premium", amount=price)],
            provider_token="",
        )
    await callback.answer()


@router.callback_query(PremiumBuyCallback.filter(F.method == "card"))
async def buy_with_card(
    callback: CallbackQuery, settings_service: SettingsService
) -> None:
    """Show the admin's card details and how to submit a receipt."""
    config = await _load_config(settings_service)
    if not config["enabled"] or not config["card_enabled"]:
        await callback.answer("\U0001F4B3 Karta to'lovi o'chirilgan.", show_alert=True)
        return
    card_number = str(config["card_number"]).strip()
    if not card_number:
        await callback.answer(
            "Karta raqami hali sozlanmagan. Administrator bilan bog'laning.", show_alert=True
        )
        return

    days = int(config["days"])
    holder = str(config["card_holder"]).strip()
    bank = str(config["card_bank"]).strip() or "Uzcard / Humo"
    lines = [
        "\U0001F4B3 <b>Karta orqali to'lov</b>\n",
        f"\U0001F4B0 To'lov summasi: <b>{format_amount(int(config['uzs_price']))}</b> so'm",
        f"\U0001F4E6 Muddat: <b>{days} kun</b>\n",
        f"\U0001F3E6 Karta ({bank}):",
        f"<code>{card_number}</code>",
    ]
    if holder:
        lines.append(f"\U0001F464 Karta egasi: <b>{holder}</b>")
    lines.append(
        "\n\U0001F4DD <b>Qadamlar:</b>\n"
        f"1) Yuqoridagi kartaga <b>{format_amount(int(config['uzs_price']))}</b> so'm o'tkazing.\n"
        "2) To'lov chekining <b>skrinshotini</b> saqlang.\n"
        "3) Pastdagi tugmani bosib, chekni yuboring.\n\n"
        "Admin tekshirgach Premium avtomatik faollashtiriladi."
    )
    if isinstance(callback.message, Message):
        await callback.message.answer("\n".join(lines), reply_markup=build_card_paid_keyboard())
    await callback.answer()


@router.callback_query(PremiumBuyCallback.filter(F.method == "card_paid"))
async def prompt_receipt(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask the user to upload the payment receipt screenshot."""
    await state.set_state(PremiumPurchaseStates.waiting_for_receipt)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "\U0001F4F8 To'lov chekining rasmini (skrinshot) yuboring.\n"
            "Bekor qilish uchun /start bosing."
        )
    await callback.answer()


@router.message(PremiumPurchaseStates.waiting_for_receipt)
async def receive_receipt(
    message: Message,
    state: FSMContext,
    settings: Settings,
    settings_service: SettingsService,
    payment_service: PaymentService,
) -> None:
    """Store the receipt, create a PENDING request, and alert every admin."""
    if message.from_user is None:
        return
    receipt_file_id = message.photo[-1].file_id if message.photo else None
    if receipt_file_id is None and not (message.text or message.caption):
        await message.answer("\u274C Iltimos, to'lov chekining rasmini yuboring.")
        return

    await state.clear()
    config = await _load_config(settings_service)
    request = await payment_service.create_request(
        user_id=message.from_user.id,
        method=PaymentMethod.CARD,
        amount=int(config["uzs_price"]),
        currency="UZS",
        days=int(config["days"]),
        receipt_file_id=receipt_file_id,
        status=PaymentStatus.PENDING,
    )
    await _notify_admins_new_card_payment(message, settings, request)
    await message.answer(
        "\u2705 Chek qabul qilindi! Administrator tez orada tekshiradi.\n"
        "Tasdiqlangach Premium avtomatik faollashadi va sizga xabar keladi."
    )


async def _notify_admins_new_card_payment(
    message: Message, settings: Settings, request: PaymentRequest
) -> None:
    """Fan out the new card payment to every admin with approve/reject buttons."""
    if message.bot is None or message.from_user is None:
        return
    user = message.from_user
    caption = (
        "\U0001F9FE <b>Yangi karta to'lovi</b>\n\n"
        f"\U0001F464 {user.full_name} (@{user.username or '-'})\n"
        f"\U0001F194 <code>{user.id}</code>\n"
        f"\U0001F4B0 {format_amount(request.amount)} so'm\n"
        f"\U0001F4E6 {request.days} kun\n\n"
        "Tasdiqlaysizmi?"
    )
    keyboard = build_payment_review_keyboard(request.id)
    for admin_id in settings.admin_ids:
        try:
            if request.receipt_file_id:
                await message.bot.send_photo(
                    chat_id=admin_id,
                    photo=request.receipt_file_id,
                    caption=caption,
                    reply_markup=keyboard,
                )
            else:
                await message.bot.send_message(
                    chat_id=admin_id, text=caption, reply_markup=keyboard
                )
        except TelegramAPIError:  # pragma: no cover - best effort fan-out
            continue


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    """Approve every Telegram Stars pre-checkout (nothing to validate server-side)."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message,
    premium_service: PremiumService,
    payment_service: PaymentService,
    log_service: LogService,
) -> None:
    """Grant Premium instantly once Telegram confirms the Stars payment."""
    if message.from_user is None or message.successful_payment is None:
        return
    payment = message.successful_payment
    days = 30
    payload = payment.invoice_payload or ""
    if payload.startswith("premium:"):
        try:
            days = int(payload.split(":", 1)[1])
        except (ValueError, IndexError):
            days = 30

    user_id = message.from_user.id
    try:
        await premium_service.grant(user_id, days=days, plan="premium_stars", granted_by=None)
    except InvalidInputError:
        await message.answer(
            "\u2705 To'lov qabul qilindi, ammo profil topilmadi. "
            "Iltimos /start bosing yoki administrator bilan bog'laning."
        )
        return

    await payment_service.create_request(
        user_id=user_id,
        method=PaymentMethod.STARS,
        amount=payment.total_amount,
        currency=payment.currency,
        days=days,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        status=PaymentStatus.APPROVED,
    )
    await log_service.record(
        actor_id=user_id,
        actor_role="user",
        action="premium_purchased_stars",
        entity_type="user",
        entity_id=str(user_id),
        new_value={"days": days, "stars": payment.total_amount},
    )
    await message.answer(
        f"\u2705 To'lov muvaffaqiyatli! {days} kunlik Premium faollashtirildi. Rahmat! \u2B50\uFE0F"
    )


register_user_plugin(router)
