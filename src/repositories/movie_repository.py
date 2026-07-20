"""Data-access operations for the ``Movie`` catalogue aggregate."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select

from src.models.movie import Movie
from src.repositories.base import BaseRepository


class MovieRepository(BaseRepository[Movie]):
    """Repository encapsulating all SQL access for ``Movie`` rows."""

    model = Movie

    async def get_by_code(self, code: str) -> Movie | None:
        """Return the active movie matching ``code``, or ``None``."""
        statement = select(Movie).where(Movie.code == code)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def code_exists(self, code: str) -> bool:
        """Return ``True`` if a movie with ``code`` already exists (any status)."""
        statement = select(func.count(Movie.id)).where(Movie.code == code)
        result = await self._session.execute(statement)
        return int(result.scalar_one()) > 0

    async def find_duplicate_by_file_id(self, telegram_file_id: str) -> Movie | None:
        """Return an existing movie sharing the same Telegram file id, if any."""
        statement = select(Movie).where(Movie.telegram_file_id == telegram_file_id)
        result = await self._session.execute(statement)
        return result.scalars().first()

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
    ) -> Sequence[Movie]:
        """Search movies by any combination of title/genre/year/language/country/actor/director."""
        statement = select(Movie)
        if not include_inactive:
            statement = statement.where(Movie.is_active.is_(True))
        if title:
            statement = statement.where(
                or_(Movie.title.ilike(f"%{title}%"), Movie.code.ilike(f"%{title}%"))
            )
        if genre:
            statement = statement.where(Movie.genre.ilike(f"%{genre}%"))
        if year:
            statement = statement.where(Movie.year == year)
        if language:
            statement = statement.where(Movie.language.ilike(f"%{language}%"))
        if country:
            statement = statement.where(Movie.country.ilike(f"%{country}%"))
        if actor:
            statement = statement.where(Movie.actor.ilike(f"%{actor}%"))
        if director:
            statement = statement.where(Movie.director.ilike(f"%{director}%"))
        statement = statement.order_by(Movie.id.desc()).limit(limit).offset(offset)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def count_all(self, *, include_inactive: bool = False) -> int:
        """Return the total number of movies in the catalogue."""
        statement = select(func.count(Movie.id))
        if not include_inactive:
            statement = statement.where(Movie.is_active.is_(True))
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def top_by_views(self, limit: int = 10) -> Sequence[Movie]:
        """Return the most-viewed movies, descending."""
        statement = select(Movie).order_by(Movie.views_count.desc()).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def top_by_downloads(self, limit: int = 10) -> Sequence[Movie]:
        """Return the most-downloaded movies, descending."""
        statement = select(Movie).order_by(Movie.downloads_count.desc()).limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def increment_views(self, movie: Movie) -> None:
        """Atomically increment the view counter for a movie."""
        movie.views_count += 1
        await self.flush()

    async def increment_downloads(self, movie: Movie) -> None:
        """Atomically increment the download counter for a movie."""
        movie.downloads_count += 1
        await self.flush()

    async def list_all_for_export(self) -> Sequence[Movie]:
        """Return every movie row (active and inactive) for Media Export (#6)."""
        statement = select(Movie).order_by(Movie.id.asc())
        result = await self._session.execute(statement)
        return result.scalars().all()
