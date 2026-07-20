"""Aggregated statistics for the admin dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.movie import Movie
from src.repositories.movie_repository import MovieRepository
from src.repositories.user_repository import UserRepository


@dataclass(frozen=True, slots=True)
class DashboardStats:
    """A snapshot of the numbers shown on the admin statistics screen."""

    users_today: int
    users_yesterday: int
    users_this_week: int
    users_this_month: int
    users_total: int
    active_users_7d: int
    premium_users: int
    movies_total: int
    top_movies_by_views: list[Movie]
    top_movies_by_downloads: list[Movie]


class StatsService:
    """Computes the aggregated numbers shown on the admin statistics screen."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._users = UserRepository(session)
        self._movies = MovieRepository(session)

    async def build_dashboard(self) -> DashboardStats:
        """Compute and return the full statistics dashboard snapshot."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        return DashboardStats(
            users_today=await self._users.count_joined_since(today_start),
            users_yesterday=await self._users.count_joined_between(yesterday_start, today_start),
            users_this_week=await self._users.count_joined_since(week_start),
            users_this_month=await self._users.count_joined_since(month_start),
            users_total=await self._users.count_all(),
            active_users_7d=await self._users.count_active_since(week_start),
            premium_users=await self._users.count_premium(),
            movies_total=await self._movies.count_all(include_inactive=True),
            top_movies_by_views=list(await self._movies.top_by_views(limit=5)),
            top_movies_by_downloads=list(await self._movies.top_by_downloads(limit=5)),
        )
