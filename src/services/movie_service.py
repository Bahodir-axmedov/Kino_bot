"""Movie catalogue management -- the core business logic of the bot.

Performance notes (see TEZLIK requirements):
- ``get_by_code`` is the hottest path in the whole bot (every code lookup
  goes through it) so its result is cached in a short-TTL in-process cache.
  A write-through invalidation happens on every mutation of that code so the
  cache can never serve stale data for longer than the TTL.
- ``code`` already has a unique index at the database layer (see
  ``Movie.code``), so even an uncached lookup is an O(log n) index seek, not
  a table scan.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.movie import MediaType, Movie, MovieCollectionType, MovieVisibility
from src.models.reserved_code import ReservedCode
from src.repositories.movie_repository import MovieRepository
from src.repositories.reserved_code_repository import ReservedCodeRepository
from src.utils.cache import TTLCache
from src.utils.code_generator import generate_sequential_movie_code, generate_unique_movie_code
from src.utils.exceptions import (
    CodeReservationConflictError,
    CodeReservedError,
    MovieCodeAlreadyExistsError,
    MovieNotFoundError,
    VisibilityDeniedError,
)

# One shared cache per process (not per-request): the hot path is read-mostly
# and a 60s TTL keeps staleness bounded while still absorbing the overwhelming
# majority of repeated lookups for a popular code under bursty traffic.
_movie_code_cache: TTLCache[str, Movie] = TTLCache(ttl_seconds=60, max_size=5000)


class MovieService:
    """Encapsulates every business rule about the movie catalogue."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = MovieRepository(session)
        self._reserved = ReservedCodeRepository(session)

    async def get_by_code(self, code: str, *, use_cache: bool = True) -> Movie:
        """Return the active movie for ``code``, raising if it is missing.

        Cached for ``use_cache=True`` callers (the default, used by the user
        delivery path). Admin-facing edit flows should pass ``use_cache=False``
        to always see the latest committed row.
        """
        if use_cache:
            cached = _movie_code_cache.get(code)
            if cached is not None:
                return cached
        movie = await self._repository.get_by_code(code)
        if movie is None or not movie.is_active:
            raise MovieNotFoundError(f"'{code}' kodli kino topilmadi.")
        if use_cache:
            _movie_code_cache.set(code, movie)
        return movie

    async def get_by_id(self, movie_id: int) -> Movie:
        """Return a movie by its surrogate id, raising if it is missing."""
        movie = await self._repository.get_by_id(movie_id)
        if movie is None:
            raise MovieNotFoundError(f"ID={movie_id} kino topilmadi.")
        return movie

    async def find_duplicate(self, telegram_file_id: str) -> Movie | None:
        """Return an existing movie sharing the same Telegram file id, if any."""
        return await self._repository.find_duplicate_by_file_id(telegram_file_id)

    async def create_movie(
        self,
        *,
        code: str | None,
        title: str,
        telegram_file_id: str,
        media_type: MediaType,
        caption: str | None = None,
        description: str | None = None,
        genre: str | None = None,
        language: str | None = None,
        country: str | None = None,
        year: int | None = None,
        quality: str | None = None,
        duration_minutes: int | None = None,
        source_chat_id: int | None = None,
        source_message_id: int | None = None,
        added_by: int | None = None,
        visibility: MovieVisibility = MovieVisibility.PUBLIC,
        use_sequential_code: bool = False,
        collection_type: MovieCollectionType = MovieCollectionType.MOVIE,
        series_title: str | None = None,
        season_number: int | None = None,
        episode_number: int | None = None,
        part_number: int | None = None,
        file_size_bytes: int | None = None,
        resolution: str | None = None,
        thumbnail_file_id: str | None = None,
        actor: str | None = None,
        director: str | None = None,
    ) -> Movie:
        """Create and persist a new movie entry.

        When ``code`` is omitted, a unique code is generated automatically
        (random by default, or sequential/auto-increment when
        ``use_sequential_code`` is set). Passing an explicit ``code`` that is
        currently reserved by an admin, or already taken, raises instead of
        silently overwriting the previous entry/reservation.
        """
        if code:
            reservation = await self._reserved.get_active_by_code(code)
            if reservation is not None and reservation.reserved_by != added_by:
                raise CodeReservedError(f"'{code}' kodi hozircha boshqa admin tomonidan band qilingan.")
            if await self._repository.code_exists(code):
                raise MovieCodeAlreadyExistsError(f"'{code}' kodi allaqachon band.")
            resolved_code = code
        elif use_sequential_code:
            current_max = await self._repository.max_numeric_code()
            resolved_code = await generate_sequential_movie_code(
                self._repository.code_exists, current_max=current_max
            )
        else:
            resolved_code = await generate_unique_movie_code(self._repository.code_exists)

        movie = Movie(
            code=resolved_code,
            title=title,
            telegram_file_id=telegram_file_id,
            media_type=media_type,
            caption=caption,
            description=description,
            genre=genre,
            language=language,
            country=country,
            year=year,
            quality=quality,
            duration_minutes=duration_minutes,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            added_by=added_by,
            is_active=True,
            visibility=visibility,
            collection_type=collection_type,
            series_title=series_title,
            season_number=season_number,
            episode_number=episode_number,
            part_number=part_number,
            file_size_bytes=file_size_bytes,
            resolution=resolution,
            thumbnail_file_id=thumbnail_file_id,
            actor=actor,
            director=director,
        )
        created = await self._repository.add(movie)
        await self.release_reservation(resolved_code)
        return created

    async def update_fields(self, movie_id: int, **fields: object) -> Movie:
        """Update arbitrary scalar fields on an existing movie."""
        movie = await self.get_by_id(movie_id)
        old_code = movie.code
        for field_name, value in fields.items():
            if not hasattr(movie, field_name):
                raise AttributeError(f"Movie has no field '{field_name}'")
            setattr(movie, field_name, value)
        await self._repository.flush()
        _movie_code_cache.invalidate(old_code)
        _movie_code_cache.invalidate(movie.code)
        return movie

    async def replace_code(self, code: str, new_code: str) -> Movie:
        """Replace a movie's public code with a new, unique one."""
        movie = await self.get_by_code(code, use_cache=False)
        if new_code != movie.code and await self._repository.code_exists(new_code):
            raise MovieCodeAlreadyExistsError(f"'{new_code}' kodi allaqachon band.")
        movie.code = new_code
        await self._repository.flush()
        _movie_code_cache.invalidate(code)
        _movie_code_cache.invalidate(new_code)
        return movie

    async def replace_caption(self, code: str, new_caption: str) -> Movie:
        """Replace a movie's caption text."""
        movie = await self.get_by_code(code, use_cache=False)
        movie.caption = new_caption
        await self._repository.flush()
        _movie_code_cache.invalidate(code)
        return movie

    async def set_active(self, movie_id: int, is_active: bool) -> Movie:
        """Activate or soft-disable a movie without deleting its row."""
        movie = await self.get_by_id(movie_id)
        movie.is_active = is_active
        await self._repository.flush()
        _movie_code_cache.invalidate(movie.code)
        return movie

    async def set_visibility(self, movie_id: int, visibility: MovieVisibility) -> Movie:
        """Change who is allowed to receive this movie once requested."""
        movie = await self.get_by_id(movie_id)
        movie.visibility = visibility
        await self._repository.flush()
        _movie_code_cache.invalidate(movie.code)
        return movie

    def assert_visible_to(
        self, movie: Movie, *, is_admin: bool, is_subscribed: bool, has_referral: bool, is_premium: bool
    ) -> None:
        """Enforce a movie's visibility rule, raising ``VisibilityDeniedError`` if blocked."""
        rule = movie.visibility
        if rule in (MovieVisibility.PUBLIC, MovieVisibility.VIP):
            return
        if rule == MovieVisibility.HIDDEN:
            raise VisibilityDeniedError("Bu kino hozircha yopiq.")
        if rule == MovieVisibility.ADMIN_ONLY and not is_admin:
            raise VisibilityDeniedError("Bu kino faqat administratorlar uchun.")
        if rule == MovieVisibility.PREMIUM and not (is_premium or is_admin):
            raise VisibilityDeniedError("Bu kino faqat Premium foydalanuvchilar uchun.")
        if rule == MovieVisibility.SUBSCRIBER_ONLY and not (is_subscribed or is_admin):
            raise VisibilityDeniedError("Bu kino faqat obunachilar uchun.")
        if rule == MovieVisibility.REFERRAL_ONLY and not (has_referral or is_admin):
            raise VisibilityDeniedError("Bu kino faqat referral orqali taklif qilinganlar uchun.")

    async def verify_file(self, bot: Bot, movie: Movie) -> bool:
        """Best-effort check that ``telegram_file_id`` is still usable by Telegram.

        Telegram file ids can become invalid if the original source message
        was deleted. There is no read-only "does this file_id still work"
        call, so this performs a lightweight ``copy_message`` probe against
        the bot's own chat_id when a source message is known, otherwise falls
        back to trusting the stored id. Marks/unmarks ``is_broken`` accordingly.
        """
        movie.last_verified_at = datetime.now(timezone.utc)
        if movie.source_chat_id is None or movie.source_message_id is None:
            await self._repository.flush()
            return not movie.is_broken
        try:
            me = await bot.get_me()
            sent = await bot.copy_message(
                chat_id=me.id,
                from_chat_id=movie.source_chat_id,
                message_id=movie.source_message_id,
            )
            await bot.delete_message(chat_id=me.id, message_id=sent.message_id)
            movie.is_broken = False
            ok = True
        except TelegramBadRequest:
            movie.is_broken = True
            ok = False
        await self._repository.flush()
        _movie_code_cache.invalidate(movie.code)
        return ok

    async def list_broken(self, limit: int = 50) -> list[Movie]:
        """Return movies currently flagged as broken."""
        return list(await self._repository.list_broken(limit=limit))

    async def reserve_code(self, code: str, *, reserved_by: int) -> ReservedCode:
        """Lock a code so only ``reserved_by`` can create a movie under it."""
        if await self._repository.code_exists(code):
            raise MovieCodeAlreadyExistsError(f"'{code}' kodi allaqachon band.")
        existing = await self._reserved.get_active_by_code(code)
        if existing is not None and existing.reserved_by != reserved_by:
            raise CodeReservationConflictError(
                f"'{code}' kodi allaqachon boshqa admin tomonidan rezerv qilingan."
            )
        if existing is not None:
            return existing
        reservation = ReservedCode(code=code, reserved_by=reserved_by)
        return await self._reserved.add(reservation)

    async def release_reservation(self, code: str) -> None:
        """Release a code reservation (idempotent no-op if none exists)."""
        reservation = await self._reserved.get_active_by_code(code)
        if reservation is not None:
            reservation.released = True
            await self._reserved.flush()

    async def delete(self, movie_id: int) -> None:
        """Permanently delete a movie entry."""
        movie = await self.get_by_id(movie_id)
        _movie_code_cache.invalidate(movie.code)
        await self._repository.delete(movie)

    async def search(
        self,
        *,
        title: str | None = None,
        genre: str | None = None,
        year: int | None = None,
        language: str | None = None,
        country: str | None = None,
        actor: str | None = None,
        director: str | None = None,
        include_inactive: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Movie]:
        """Search the catalogue by any combination of filters (#16: Kod/Nom/Janr/Til/Yil/Actor/Director/Country)."""
        return list(
            await self._repository.search(
                title=title,
                genre=genre,
                year=year,
                language=language,
                country=country,
                actor=actor,
                director=director,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
            )
        )

    async def register_delivery(self, movie: Movie) -> None:
        """Record that a movie was viewed/delivered once (views + downloads)."""
        await self._repository.increment_views(movie)
        await self._repository.increment_downloads(movie)

    async def count_all(self, *, include_inactive: bool = False) -> int:
        """Return the total number of movies in the catalogue."""
        return await self._repository.count_all(include_inactive=include_inactive)

    async def top_by_views(self, limit: int = 10) -> list[Movie]:
        """Return the most-viewed movies, descending."""
        return list(await self._repository.top_by_views(limit=limit))

    async def top_by_downloads(self, limit: int = 10) -> list[Movie]:
        """Return the most-downloaded movies, descending."""
        return list(await self._repository.top_by_downloads(limit=limit))

    async def least_by_views(self, limit: int = 10) -> list[Movie]:
        """Return the least-used movies, ascending -- for the Media Center."""
        return list(await self._repository.least_by_views(limit=limit))

    async def export_csv(self) -> str:
        """Return the full movie catalogue as CSV text (Media eksport)."""
        movies = await self._repository.list_all_for_export()
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["code", "title", "telegram_file_id", "media_type", "genre", "language", "year", "quality", "visibility", "is_active", "views_count", "downloads_count"]
        )
        for movie in movies:
            writer.writerow(
                [
                    movie.code,
                    movie.title,
                    movie.telegram_file_id,
                    movie.media_type.value,
                    movie.genre or "",
                    movie.language or "",
                    movie.year or "",
                    movie.quality or "",
                    movie.visibility.value,
                    movie.is_active,
                    movie.views_count,
                    movie.downloads_count,
                ]
            )
        return buffer.getvalue()

    def _export_rows(self, movies: list[Movie]) -> list[dict[str, object]]:
        """Build a shared dict-row shape (all fields) reused by JSON/Excel export."""
        rows: list[dict[str, object]] = []
        for movie in movies:
            rows.append(
                {
                    "code": movie.code,
                    "title": movie.title,
                    "telegram_file_id": movie.telegram_file_id,
                    "media_type": movie.media_type.value,
                    "collection_type": movie.collection_type.value,
                    "series_title": movie.series_title or "",
                    "season_number": movie.season_number,
                    "episode_number": movie.episode_number,
                    "part_number": movie.part_number,
                    "genre": movie.genre or "",
                    "language": movie.language or "",
                    "country": movie.country or "",
                    "actor": movie.actor or "",
                    "director": movie.director or "",
                    "year": movie.year,
                    "quality": movie.quality or "",
                    "resolution": movie.resolution or "",
                    "file_size_bytes": movie.file_size_bytes,
                    "duration_minutes": movie.duration_minutes,
                    "visibility": movie.visibility.value,
                    "is_active": movie.is_active,
                    "views_count": movie.views_count,
                    "downloads_count": movie.downloads_count,
                }
            )
        return rows

    async def export_json(self) -> str:
        """Return the full movie catalogue as a JSON array string (Media Export #6)."""
        movies = await self._repository.list_all_for_export()
        return json.dumps(self._export_rows(list(movies)), ensure_ascii=False, indent=2)

    async def export_excel_rows(self) -> list[dict[str, object]]:
        """Return export rows for the caller to render into an .xlsx workbook.

        Kept as plain dict rows here (no hard ``openpyxl`` dependency in the
        service layer); the handler builds the actual workbook.
        """
        movies = await self._repository.list_all_for_export()
        return self._export_rows(list(movies))

    async def import_json(self, json_text: str, *, added_by: int | None) -> tuple[int, list[str]]:
        """Bulk-import movies from a JSON array (Media Import #5). Returns (created_count, errors).

        Each object must include at least ``code``, ``title``, and
        ``telegram_file_id``. Unknown/omitted fields default sensibly; rows
        with a code that already exists are skipped and reported as errors.
        """
        try:
            rows = json.loads(json_text)
        except (ValueError, TypeError) as error:
            return 0, [f"JSON formatida xato: {error}"]
        if not isinstance(rows, list):
            return 0, ["JSON fayl massiv (array) bo'lishi kerak."]

        created = 0
        errors: list[str] = []
        for row_number, row in enumerate(rows, start=1):
            if not isinstance(row, dict):
                errors.append(f"Qator {row_number}: obyekt emas.")
                continue
            code = str(row.get("code") or "").strip()
            title = str(row.get("title") or "").strip()
            file_id = str(row.get("telegram_file_id") or "").strip()
            if not code or not title or not file_id:
                errors.append(f"Qator {row_number}: code/title/telegram_file_id yetishmayapti.")
                continue
            try:
                media_type = MediaType(str(row.get("media_type") or "video").strip().lower())
            except ValueError:
                errors.append(f"Qator {row_number}: noto'g'ri media_type.")
                continue
            try:
                collection_type = MovieCollectionType(
                    str(row.get("collection_type") or "movie").strip().lower()
                )
            except ValueError:
                collection_type = MovieCollectionType.MOVIE
            try:
                await self.create_movie(
                    code=code,
                    title=title,
                    telegram_file_id=file_id,
                    media_type=media_type,
                    genre=(row.get("genre") or None),
                    language=(row.get("language") or None),
                    country=(row.get("country") or None),
                    actor=(row.get("actor") or None),
                    director=(row.get("director") or None),
                    year=int(row["year"]) if row.get("year") else None,
                    quality=(row.get("quality") or None),
                    resolution=(row.get("resolution") or None),
                    collection_type=collection_type,
                    series_title=(row.get("series_title") or None),
                    season_number=int(row["season_number"]) if row.get("season_number") else None,
                    episode_number=int(row["episode_number"]) if row.get("episode_number") else None,
                    part_number=int(row["part_number"]) if row.get("part_number") else None,
                    added_by=added_by,
                )
                created += 1
            except (MovieCodeAlreadyExistsError, CodeReservedError) as error:
                errors.append(f"Qator {row_number}: {error}")
        return created, errors

    async def import_csv(self, csv_text: str, *, added_by: int | None) -> tuple[int, list[str]]:
        """Bulk-import movies from CSV (Media import). Returns (created_count, errors).

        Expected columns: code,title,telegram_file_id,media_type,genre,language,year,quality
        Rows with a code that already exists are skipped (reported as an error),
        never silently overwritten.
        """
        reader = csv.DictReader(io.StringIO(csv_text))
        created = 0
        errors: list[str] = []
        for row_number, row in enumerate(reader, start=2):
            code = (row.get("code") or "").strip()
            title = (row.get("title") or "").strip()
            file_id = (row.get("telegram_file_id") or "").strip()
            media_type_raw = (row.get("media_type") or "video").strip().lower()
            if not code or not title or not file_id:
                errors.append(f"Qator {row_number}: code/title/telegram_file_id yetishmayapti.")
                continue
            try:
                media_type = MediaType(media_type_raw)
            except ValueError:
                errors.append(f"Qator {row_number}: noto'g'ri media_type '{media_type_raw}'.")
                continue
            try:
                await self.create_movie(
                    code=code,
                    title=title,
                    telegram_file_id=file_id,
                    media_type=media_type,
                    genre=(row.get("genre") or None),
                    language=(row.get("language") or None),
                    year=int(row["year"]) if row.get("year") else None,
                    quality=(row.get("quality") or None),
                    added_by=added_by,
                )
                created += 1
            except (MovieCodeAlreadyExistsError, CodeReservedError) as error:
                errors.append(f"Qator {row_number}: {error}")
        return created, errors
