"""Free-text movie search for end-users (by title/genre/year/language)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.core.plugin import register_user_plugin
from src.services.movie_service import MovieService
from src.services.search_log_service import SearchLogService
from src.states.movie_states import SearchMovieStates

router = Router(name="user.search")


@router.message(F.text == "🔍 Kino qidirish")
async def start_search(message: Message, state: FSMContext) -> None:
    """Prompt the user for a search term."""
    await state.set_state(SearchMovieStates.waiting_for_query)
    await message.answer("🔍 Kino nomi, janri, yili yoki tilini yozing:")


@router.message(SearchMovieStates.waiting_for_query)
async def run_search(
    message: Message,
    state: FSMContext,
    movie_service: MovieService,
    search_log_service: SearchLogService,
) -> None:
    """Run the search, record it to the Search History Center, and show up to 10 matches."""
    await state.clear()
    if not message.text:
        await message.answer("Qidiruv matni bo'sh bo'lishi mumkin emas.")
        return

    query = message.text.strip()
    results = await movie_service.search(title=query, limit=10)
    if not results:
        results = await movie_service.search(genre=query, limit=10)

    await search_log_service.record(
        query_text=query,
        found=bool(results),
        user_id=message.from_user.id if message.from_user else None,
        query_type="title",
    )

    if not results:
        await message.answer("❌ Hech narsa topilmadi. Boshqa so'z bilan urinib ko'ring.")
        return

    lines = ["🔍 <b>Qidiruv natijalari:</b>", ""]
    for movie in results:
        lines.append(f"🎬 {movie.title} ({movie.year or '?'}) — kod: <code>{movie.code}</code>")
    await message.answer("\n".join(lines))


register_user_plugin(router)
