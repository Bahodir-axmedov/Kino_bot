"""Admin movie CRUD: add, edit, delete, code/caption replace, bulk ops."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Animation, Audio, CallbackQuery, Document, Message, PhotoSize, Video

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, MovieActionCallback
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard
from src.keyboards.inline.movie import build_movie_admin_actions_keyboard, build_movie_delete_confirm_keyboard
from src.models.movie import MediaType
from src.services.log_service import LogService
from src.services.movie_service import MovieService
from src.states.movie_states import (
    BulkUploadStates,
    EditCaptionStates,
    EditCodeStates,
    MovieFormStates,
    SearchMovieStates,
)
from src.utils.exceptions import MovieCodeAlreadyExistsError, MovieNotFoundError
from src.utils.formatters import format_movie_caption
from src.utils.validators import normalize_movie_code, validate_non_empty_text

router = Router(name="admin.movie_management")

_MEDIA_TYPE_BY_ATTR: list[tuple[str, MediaType]] = [
    ("video", MediaType.VIDEO),
    ("document", MediaType.DOCUMENT),
    ("audio", MediaType.AUDIO),
    ("animation", MediaType.ANIMATION),
    ("photo", MediaType.PHOTO),
]


def _extract_media(message: Message) -> tuple[str, MediaType] | None:
    """Return ``(file_id, media_type)`` for the first supported media on a message."""
    for attr, media_type in _MEDIA_TYPE_BY_ATTR:
        value = getattr(message, attr, None)
        if value is None:
            continue
        if isinstance(value, list):  # photo -> list[PhotoSize], take highest resolution
            if not value:
                continue
            return value[-1].file_id, media_type
        return value.file_id, media_type
    return None


@router.callback_query(AdminMenuCallback.filter(F.section == "movie_add"))
async def start_add_movie(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the add-movie FSM flow by asking for the media file."""
    await state.set_state(MovieFormStates.waiting_for_media)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🎬 Kino faylini (video/document/audio/animation/photo) yuboring.",
            reply_markup=build_back_to_admin_menu_keyboard(),
        )
    await callback.answer()


@router.message(MovieFormStates.waiting_for_media)
async def receive_media(message: Message, state: FSMContext, movie_service: MovieService) -> None:
    """Store the uploaded media and check for duplicates before continuing."""
    media = _extract_media(message)
    if media is None:
        await message.answer("❌ Iltimos, video, document, audio, animation yoki photo yuboring.")
        return

    file_id, media_type = media
    duplicate = await movie_service.find_duplicate(file_id)
    if duplicate is not None:
        await message.answer(
            f"⚠️ Bu fayl allaqachon <code>{duplicate.code}</code> kodi bilan mavjud."
        )
        await state.clear()
        return

    await state.update_data(
        telegram_file_id=file_id,
        media_type=media_type.value,
        source_chat_id=message.chat.id,
    )
    await state.set_state(MovieFormStates.waiting_for_title)
    await message.answer("📝 Kino nomini yuboring:")


@router.message(MovieFormStates.waiting_for_title)
async def receive_title(message: Message, state: FSMContext) -> None:
    """Capture the movie title."""
    if not message.text:
        await message.answer("Nom matn ko'rinishida bo'lishi kerak.")
        return
    title = validate_non_empty_text(message.text, field_name="Nom", max_length=256)
    await state.update_data(title=title)
    await state.set_state(MovieFormStates.waiting_for_year)
    await message.answer("📅 Chiqarilgan yilini yuboring (yoki /skip):")


@router.message(MovieFormStates.waiting_for_year)
async def receive_year(message: Message, state: FSMContext) -> None:
    """Capture the release year (optional)."""
    year: int | None = None
    if message.text and message.text.strip() != "/skip" and message.text.strip().isdigit():
        year = int(message.text.strip())
    await state.update_data(year=year)
    await state.set_state(MovieFormStates.waiting_for_genre)
    await message.answer("🎭 Janrini yuboring (yoki /skip):")


@router.message(MovieFormStates.waiting_for_genre)
async def receive_genre(message: Message, state: FSMContext) -> None:
    """Capture the genre (optional)."""
    genre = message.text.strip() if message.text and message.text.strip() != "/skip" else None
    await state.update_data(genre=genre)
    await state.set_state(MovieFormStates.waiting_for_description)
    await message.answer("📄 Tavsifini yuboring (yoki /skip):")


@router.message(MovieFormStates.waiting_for_description)
async def receive_description_and_save(
    message: Message,
    state: FSMContext,
    movie_service: MovieService,
    log_service: LogService,
) -> None:
    """Capture the description and persist the new movie entry."""
    description = (
        message.text.strip() if message.text and message.text.strip() != "/skip" else None
    )
    data = await state.get_data()
    await state.clear()

    movie = await movie_service.create_movie(
        code=None,
        title=data["title"],
        telegram_file_id=data["telegram_file_id"],
        media_type=MediaType(data["media_type"]),
        description=description,
        genre=data.get("genre"),
        year=data.get("year"),
        source_chat_id=data.get("source_chat_id"),
        added_by=message.from_user.id if message.from_user else None,
    )
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="movie_created",
        entity_type="movie",
        entity_id=movie.code,
        new_value={"title": movie.title, "code": movie.code},
    )
    await message.answer(
        f"✅ Kino qo'shildi!\n\n{format_movie_caption(movie)}",
        reply_markup=build_movie_admin_actions_keyboard(movie),
    )


@router.callback_query(AdminMenuCallback.filter(F.section == "movie_search"))
async def start_movie_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin an admin full-catalogue search (including inactive movies)."""
    await state.set_state(SearchMovieStates.waiting_for_query)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("🔍 Qidiruv so'zini yuboring (nom/janr):")
    await callback.answer()


@router.message(SearchMovieStates.waiting_for_query, F.text)
async def run_admin_search(
    message: Message, state: FSMContext, movie_service: MovieService
) -> None:
    """Run a full admin search including inactive/disabled movies."""
    await state.clear()
    query = message.text.strip() if message.text else ""
    results = await movie_service.search(title=query, include_inactive=True, limit=15)
    if not results:
        await message.answer("❌ Hech narsa topilmadi.")
        return
    for movie in results:
        status = "✅" if movie.is_active else "🚫"
        await message.answer(
            f"{status} <b>{movie.title}</b> — <code>{movie.code}</code> "
            f"(👁 {movie.views_count} / ⬇️ {movie.downloads_count})",
            reply_markup=build_movie_admin_actions_keyboard(movie),
        )


@router.callback_query(MovieActionCallback.filter(F.action == "delete"))
async def confirm_delete(callback: CallbackQuery, callback_data: MovieActionCallback) -> None:
    """Ask for confirmation before permanently deleting a movie."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⚠️ Ushbu kinoni butunlay o'chirishni tasdiqlaysizmi?",
            reply_markup=build_movie_delete_confirm_keyboard(callback_data.movie_id),
        )
    await callback.answer()


@router.callback_query(MovieActionCallback.filter(F.action == "confirm_delete"))
async def do_delete(
    callback: CallbackQuery,
    callback_data: MovieActionCallback,
    movie_service: MovieService,
    log_service: LogService,
) -> None:
    """Permanently delete the movie after confirmation."""
    movie = await movie_service.get_by_id(callback_data.movie_id)
    await movie_service.delete(callback_data.movie_id)
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="movie_deleted",
        entity_type="movie",
        entity_id=movie.code,
        old_value={"title": movie.title},
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text("🗑 Kino o'chirildi.")
    await callback.answer()


@router.callback_query(MovieActionCallback.filter(F.action == "cancel_delete"))
async def cancel_delete(callback: CallbackQuery, callback_data: MovieActionCallback, movie_service: MovieService) -> None:
    """Cancel the delete confirmation and restore the movie action menu."""
    movie = await movie_service.get_by_id(callback_data.movie_id)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_movie_caption(movie), reply_markup=build_movie_admin_actions_keyboard(movie)
        )
    await callback.answer("Bekor qilindi.")


@router.callback_query(MovieActionCallback.filter(F.action == "toggle"))
async def toggle_active(
    callback: CallbackQuery,
    callback_data: MovieActionCallback,
    movie_service: MovieService,
    log_service: LogService,
) -> None:
    """Toggle a movie's active/disabled state."""
    movie = await movie_service.get_by_id(callback_data.movie_id)
    movie = await movie_service.set_active(movie.id, not movie.is_active)
    await log_service.record(
        actor_id=callback.from_user.id,
        actor_role="admin",
        action="movie_toggled",
        entity_type="movie",
        entity_id=movie.code,
        new_value={"is_active": movie.is_active},
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_movie_caption(movie), reply_markup=build_movie_admin_actions_keyboard(movie)
        )
    await callback.answer("✅ Yangilandi.")


@router.callback_query(AdminMenuCallback.filter(F.section == "movie_edit_code"))
async def start_edit_code(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the replace-code FSM flow."""
    await state.set_state(EditCodeStates.waiting_for_movie_code)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("✏️ Hozirgi kino kodini yuboring:")
    await callback.answer()


@router.message(EditCodeStates.waiting_for_movie_code, F.text)
async def receive_code_to_edit(message: Message, state: FSMContext) -> None:
    """Capture the existing code and ask for the replacement."""
    await state.update_data(code=normalize_movie_code(message.text))
    await state.set_state(EditCodeStates.waiting_for_new_code)
    await message.answer("🆕 Yangi kodni yuboring:")


@router.message(EditCodeStates.waiting_for_new_code, F.text)
async def apply_code_replace(
    message: Message, state: FSMContext, movie_service: MovieService, log_service: LogService
) -> None:
    """Apply the new code to the movie, if it is not already taken."""
    data = await state.get_data()
    await state.clear()
    new_code = normalize_movie_code(message.text)
    try:
        movie = await movie_service.replace_code(data["code"], new_code)
    except (MovieNotFoundError, MovieCodeAlreadyExistsError) as error:
        await message.answer(f"❌ {error}")
        return
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="movie_code_replaced",
        entity_type="movie",
        entity_id=movie.code,
        old_value={"code": data["code"]},
        new_value={"code": new_code},
    )
    await message.answer(f"✅ Kod yangilandi: <code>{new_code}</code>")


@router.callback_query(AdminMenuCallback.filter(F.section == "movie_edit_caption"))
async def start_edit_caption(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the replace-caption FSM flow."""
    await state.set_state(EditCaptionStates.waiting_for_movie_code)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("📝 Kino kodini yuboring:")
    await callback.answer()


@router.message(EditCaptionStates.waiting_for_movie_code, F.text)
async def receive_code_for_caption(message: Message, state: FSMContext) -> None:
    """Capture the target code and ask for the new caption."""
    await state.update_data(code=normalize_movie_code(message.text))
    await state.set_state(EditCaptionStates.waiting_for_new_caption)
    await message.answer("📝 Yangi caption matnini yuboring:")


@router.message(EditCaptionStates.waiting_for_new_caption, F.text)
async def apply_caption_replace(
    message: Message, state: FSMContext, movie_service: MovieService, log_service: LogService
) -> None:
    """Apply the new caption text to the movie."""
    data = await state.get_data()
    await state.clear()
    new_caption = validate_non_empty_text(message.text, field_name="Caption", max_length=1024)
    try:
        movie = await movie_service.replace_caption(data["code"], new_caption)
    except MovieNotFoundError as error:
        await message.answer(f"❌ {error}")
        return
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="movie_caption_replaced",
        entity_type="movie",
        entity_id=movie.code,
    )
    await message.answer("✅ Caption yangilandi.")


@router.callback_query(AdminMenuCallback.filter(F.section == "movie_bulk_upload"))
async def start_bulk_upload(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin bulk-upload mode: every following media message is auto-indexed."""
    await state.set_state(BulkUploadStates.collecting)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "📦 Bulk upload rejimi yoqildi. Fayllarni birma-bir yuboring.\n"
            "Tugatish uchun /done buyrug'ini yuboring."
        )
    await callback.answer()


@router.message(BulkUploadStates.collecting, F.text == "/done")
async def finish_bulk_upload(message: Message, state: FSMContext) -> None:
    """End bulk-upload mode."""
    await state.clear()
    await message.answer("✅ Bulk upload tugatildi.")


@router.message(BulkUploadStates.collecting)
async def collect_bulk_media(
    message: Message, movie_service: MovieService, log_service: LogService
) -> None:
    """Auto-index one media message with an auto-generated code and title."""
    media = _extract_media(message)
    if media is None:
        await message.answer("❌ Qo'llab-quvvatlanmaydigan fayl turi. O'tkazib yuborildi.")
        return
    file_id, media_type = media
    if await movie_service.find_duplicate(file_id) is not None:
        await message.answer("⚠️ Bu fayl allaqachon mavjud, o'tkazib yuborildi.")
        return

    title = (message.caption or f"Kino {file_id[:8]}").strip()
    movie = await movie_service.create_movie(
        code=None,
        title=title,
        telegram_file_id=file_id,
        media_type=media_type,
        source_chat_id=message.chat.id,
        added_by=message.from_user.id if message.from_user else None,
    )
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="movie_bulk_created",
        entity_type="movie",
        entity_id=movie.code,
    )
    await message.answer(f"✅ Qo'shildi: <code>{movie.code}</code> — {movie.title}")


@router.callback_query(AdminMenuCallback.filter(F.section == "movie_bulk_delete"))
async def bulk_delete_hint(callback: CallbackQuery) -> None:
    """Explain how to bulk-delete via the per-movie toggle/delete actions.

    Bulk delete is performed by searching (🔍 Kino qidirish -> admin search)
    and deleting the desired entries one by one via their action keyboard --
    this avoids irreversible, unreviewed mass deletions.
    """
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "🗑 Bulk delete: qidiruv orqali kinolarni toping va har birini "
            "\"🗑 O'chirish\" tugmasi orqali o'chiring. Bu tasodifiy ommaviy "
            "o'chirishlarning oldini oladi.",
            reply_markup=build_back_to_admin_menu_keyboard(),
        )
    await callback.answer()


register_admin_plugin(router)
