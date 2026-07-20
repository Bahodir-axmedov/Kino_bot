"""Media Center: preview, duplicate/broken checks, code reserve/release, export/import."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard
from src.keyboards.inline.movie import build_movie_admin_actions_keyboard
from src.services.log_service import LogService
from src.services.movie_service import MovieService
from src.states.movie_states import CodeManagementStates, MediaCenterStates
from src.utils.exceptions import (
    CodeReservationConflictError,
    MovieCodeAlreadyExistsError,
    MovieNotFoundError,
)
from src.utils.formatters import format_movie_caption
from src.utils.validators import normalize_movie_code

router = Router(name="admin.media_center")


@router.callback_query(AdminMenuCallback.filter(F.section == "media_center"))
async def open_media_center(callback: CallbackQuery, movie_service: MovieService) -> None:
    """Show the Media Center overview: totals, top, least-used, broken."""
    total = await movie_service.count_all(include_inactive=True)
    top = await movie_service.top_by_views(limit=5)
    least = await movie_service.least_by_views(limit=5)
    broken = await movie_service.list_broken(limit=5)

    top_lines = "\n".join(f"  • {m.title} — {m.views_count} 👁" for m in top) or "  —"
    least_lines = "\n".join(f"  • {m.title} — {m.views_count} 👁" for m in least) or "  —"
    broken_lines = "\n".join(f"  • {m.title} — <code>{m.code}</code>" for m in broken) or "  —"

    text = (
        "\U0001F3AC <b>Media Center</b>\n\n"
        f"Jami media: {total}\n\n"
        f"\U0001F3C6 Eng ko'p ko'rilgan:\n{top_lines}\n\n"
        f"\U0001F4C9 Eng kam ishlatilgan:\n{least_lines}\n\n"
        f"\u26A0\uFE0F Broken fayllar:\n{broken_lines}\n\n"
        "Kodni oddiy matn qilib yuborsangiz, uning preview'i ko'rsatiladi.\n"
        "/reserve &lt;kod&gt; — kodni band qilish\n"
        "/release &lt;kod&gt; — kodni bo'shatish\n"
        "/export_media — to'liq katalogni CSV qilib olish"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=build_back_to_admin_menu_keyboard())
        await callback.message.answer("Preview uchun kodni yuboring:")
    await callback.answer()


@router.callback_query(AdminMenuCallback.filter(F.section == "media_preview"))
async def start_preview(callback: CallbackQuery, state: FSMContext) -> None:
    """Ask for a code to preview (media + full metadata + admin actions)."""
    await state.set_state(MediaCenterStates.waiting_for_preview_code)
    if isinstance(callback.message, Message):
        await callback.message.edit_text("\U0001F441 Preview qilish uchun kodni yuboring:")
    await callback.answer()


@router.message(MediaCenterStates.waiting_for_preview_code, F.text)
async def show_preview(message: Message, state: FSMContext, movie_service: MovieService) -> None:
    """Show the full media preview: caption, stats, file-id check, admin actions."""
    await state.clear()
    if not message.text:
        return
    code = normalize_movie_code(message.text)
    try:
        movie = await movie_service.get_by_code(code, use_cache=False)
    except MovieNotFoundError as error:
        await message.answer(str(error))
        return

    is_ok = True
    if message.bot is not None:
        is_ok = await movie_service.verify_file(message.bot, movie)

    file_status = "\u2705 Fayl ishlaydi" if is_ok else "\u274C Fayl BUZILGAN (broken)"
    await message.answer(
        f"{format_movie_caption(movie)}\n\n{file_status}",
        reply_markup=build_movie_admin_actions_keyboard(movie),
    )


@router.message(F.text.startswith("/reserve"))
async def reserve_code_command(
    message: Message, movie_service: MovieService, log_service: LogService
) -> None:
    """Reserve (lock) a code so no one else can create a movie under it."""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /reserve &lt;kod&gt;")
        return
    code = normalize_movie_code(parts[1])
    try:
        await movie_service.reserve_code(code, reserved_by=message.from_user.id if message.from_user else 0)
    except (MovieCodeAlreadyExistsError, CodeReservationConflictError) as error:
        await message.answer(str(error))
        return
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="code_reserved",
        entity_type="reserved_code",
        entity_id=code,
    )
    await message.answer(f"\U0001F512 '{code}' kodi band qilindi.")


@router.message(F.text.startswith("/release"))
async def release_code_command(
    message: Message, movie_service: MovieService, log_service: LogService
) -> None:
    """Release a previously reserved code."""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /release &lt;kod&gt;")
        return
    code = normalize_movie_code(parts[1])
    await movie_service.release_reservation(code)
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="code_released",
        entity_type="reserved_code",
        entity_id=code,
    )
    await message.answer(f"\U0001F513 '{code}' kodi bo'shatildi.")


@router.message(F.text == "/export_media")
async def export_media_command(message: Message, movie_service: MovieService) -> None:
    """Export the full movie catalogue as a downloadable CSV file."""
    csv_text = await movie_service.export_csv()
    document = BufferedInputFile(csv_text.encode("utf-8"), filename="media_export.csv")
    await message.answer_document(document, caption="\U0001F4E4 Media eksport (CSV)")


@router.message(F.document, F.caption == "/import_media")
async def import_media_command(
    message: Message, movie_service: MovieService, log_service: LogService
) -> None:
    """Bulk-import movies from an uploaded CSV file (caption ``/import_media``)."""
    if message.document is None or message.bot is None:
        return
    buffer = await message.bot.download(message.document)
    if buffer is None:
        await message.answer("Faylni yuklab bo'lmadi.")
        return
    csv_text = buffer.read().decode("utf-8")
    created, errors = await movie_service.import_csv(
        csv_text, added_by=message.from_user.id if message.from_user else None
    )
    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="media_imported",
        entity_type="movie",
        new_value={"created": created, "errors": len(errors)},
    )
    summary = f"\u2705 {created} ta media import qilindi."
    if errors:
        summary += "\n\n\u26A0\uFE0F Xatolar:\n" + "\n".join(errors[:10])
    await message.answer(summary)


register_admin_plugin(router)
