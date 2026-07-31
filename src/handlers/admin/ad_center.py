"""Advertisement Center (V4.0): admin-created ads shown every N searches."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdActionCallback, AdminMenuCallback
from src.keyboards.inline.admin_panel import build_ads_keyboard
from src.models.ad_campaign import AdContentType
from src.services.ad_service import AdService
from src.states.admin_states import AdStates
from src.utils.exceptions import InvalidInputError

router = Router(name="admin.ad_center")

_DEFAULT_INTERVAL = 10


async def _render(callback: CallbackQuery, ad_service: AdService) -> None:
    """Render the Advertisement Center campaign list."""
    campaigns = await ad_service.list_all()
    lines = ["📣 <b>Reklama markazi</b>", ""]
    if not campaigns:
        lines.append("Hozircha reklama kampaniyasi yo'q.")
    else:
        for campaign in campaigns:
            state_icon = "🟢" if campaign.is_active else "⚪️"
            preview = (campaign.text or campaign.content_type.value)[:40]
            lines.append(
                f"{state_icon} {preview} — har {campaign.trigger_every_n_searches} qidiruvda "
                f"· {campaign.impressions_count} marta ko'rsatilgan"
            )
    if isinstance(callback.message, Message):
        await callback.message.edit_text("\n".join(lines), reply_markup=build_ads_keyboard(campaigns))


@router.callback_query(AdminMenuCallback.filter(F.section == "ads"))
async def open_ad_center(callback: CallbackQuery, ad_service: AdService) -> None:
    """Show the Advertisement Center."""
    await _render(callback, ad_service)
    await callback.answer()


@router.callback_query(AdActionCallback.filter(F.action == "create"))
async def prompt_create_ad(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt the admin for the new campaign's text."""
    await state.set_state(AdStates.waiting_for_text)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("📣 Reklama matnini yuboring:")
    await callback.answer()


@router.message(AdStates.waiting_for_text, F.text)
async def receive_ad_text(message: Message, state: FSMContext) -> None:
    """Capture the campaign text and ask for the display interval."""
    await state.update_data(ad_text=message.text.strip())
    await state.set_state(AdStates.waiting_for_interval)
    await message.answer(
        f"Necha qidiruvda bir marta ko'rsatilsin? (raqam yuboring, standart: {_DEFAULT_INTERVAL})"
    )


@router.message(AdStates.waiting_for_interval, F.text)
async def receive_ad_interval(message: Message, state: FSMContext, ad_service: AdService) -> None:
    """Create the text ad campaign with the supplied interval."""
    data = await state.get_data()
    await state.clear()
    raw = message.text.strip()
    try:
        interval = int(raw) if raw else _DEFAULT_INTERVAL
    except ValueError:
        interval = _DEFAULT_INTERVAL
    try:
        await ad_service.create(
            content_type=AdContentType.TEXT,
            text=data.get("ad_text", ""),
            trigger_every_n_searches=interval,
            created_by=message.from_user.id if message.from_user else None,
        )
    except InvalidInputError as error:
        await message.answer(f"❌ {error}")
        return
    campaigns = await ad_service.list_all()
    await message.answer("✅ Reklama kampaniyasi yaratildi.", reply_markup=build_ads_keyboard(campaigns))


@router.callback_query(AdActionCallback.filter(F.action == "toggle"))
async def toggle_ad(callback: CallbackQuery, callback_data: AdActionCallback, ad_service: AdService) -> None:
    """Toggle a campaign's active state."""
    campaigns = await ad_service.list_all()
    current = next((c for c in campaigns if c.id == callback_data.campaign_id), None)
    if current is not None:
        await ad_service.set_active(callback_data.campaign_id, not current.is_active)
    await _render(callback, ad_service)
    await callback.answer("✅ Yangilandi")


@router.callback_query(AdActionCallback.filter(F.action == "delete"))
async def delete_ad(callback: CallbackQuery, callback_data: AdActionCallback, ad_service: AdService) -> None:
    """Permanently delete a campaign."""
    try:
        await ad_service.delete(callback_data.campaign_id)
    except InvalidInputError as error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return
    await _render(callback, ad_service)
    await callback.answer("🗑 O'chirildi")


register_admin_plugin(router)
