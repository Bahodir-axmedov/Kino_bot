"""Media Collections (V4.0): curated, orderable showcase shelves."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, CollectionActionCallback
from src.keyboards.inline.admin_panel import build_collections_keyboard
from src.services.media_collection_service import MediaCollectionService
from src.states.admin_states import CollectionStates
from src.utils.exceptions import InvalidInputError

router = Router(name="admin.media_collections")


async def _render(callback: CallbackQuery, media_collection_service: MediaCollectionService) -> None:
    """Render the collections list screen."""
    collections = await media_collection_service.list_collections()
    lines = ["🗂 <b>Media Collections</b>", ""]
    if not collections:
        lines.append("Hozircha collection yo'q.")
    else:
        for collection in collections:
            state_icon = "🟢" if collection.is_active else "⚪️"
            lines.append(f"{state_icon} <b>{collection.name}</b> (#{collection.position})")
    if isinstance(callback.message, Message):
        await callback.message.edit_text("\n".join(lines), reply_markup=build_collections_keyboard(collections))


@router.callback_query(AdminMenuCallback.filter(F.section == "media_collections"))
async def open_collections(callback: CallbackQuery, media_collection_service: MediaCollectionService) -> None:
    """Show the Media Collections list."""
    await _render(callback, media_collection_service)
    await callback.answer()


@router.callback_query(CollectionActionCallback.filter(F.action == "create"))
async def prompt_create_collection(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompt the admin for the new collection's name."""
    await state.set_state(CollectionStates.waiting_for_name)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("🗂 Yangi collection nomini yuboring:")
    await callback.answer()


@router.message(CollectionStates.waiting_for_name, F.text)
async def receive_collection_name(
    message: Message, state: FSMContext, media_collection_service: MediaCollectionService
) -> None:
    """Create the new collection with the supplied name."""
    await state.clear()
    try:
        collection = await media_collection_service.create(
            name=message.text.strip(), created_by=message.from_user.id if message.from_user else None
        )
    except InvalidInputError as error:
        await message.answer(f"❌ {error}")
        return
    collections = await media_collection_service.list_collections()
    await message.answer(
        f"✅ <b>{collection.name}</b> yaratildi.", reply_markup=build_collections_keyboard(collections)
    )


@router.callback_query(CollectionActionCallback.filter(F.action == "toggle"))
async def toggle_collection(
    callback: CallbackQuery, callback_data: CollectionActionCallback, media_collection_service: MediaCollectionService
) -> None:
    """Toggle a collection's active state."""
    collections = await media_collection_service.list_collections()
    current = next((c for c in collections if c.id == callback_data.collection_id), None)
    if current is not None:
        await media_collection_service.set_active(callback_data.collection_id, not current.is_active)
    await _render(callback, media_collection_service)
    await callback.answer("✅ Yangilandi")


@router.callback_query(CollectionActionCallback.filter(F.action.in_({"up", "down"})))
async def move_collection(
    callback: CallbackQuery, callback_data: CollectionActionCallback, media_collection_service: MediaCollectionService
) -> None:
    """Move a collection up or down in the display order."""
    await media_collection_service.move(callback_data.collection_id, direction=callback_data.action)
    await _render(callback, media_collection_service)
    await callback.answer()


@router.callback_query(CollectionActionCallback.filter(F.action == "delete"))
async def delete_collection(
    callback: CallbackQuery, callback_data: CollectionActionCallback, media_collection_service: MediaCollectionService
) -> None:
    """Permanently delete a collection."""
    try:
        await media_collection_service.delete(callback_data.collection_id)
    except InvalidInputError as error:
        await callback.answer(f"❌ {error}", show_alert=True)
        return
    await _render(callback, media_collection_service)
    await callback.answer("🗑 O'chirildi")


register_admin_plugin(router)
