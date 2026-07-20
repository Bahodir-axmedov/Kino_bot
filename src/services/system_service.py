"""Real-time system metrics for the admin Dashboard section.

Uses ``psutil`` (a new, small, pure-operational dependency) for CPU/RAM/disk
numbers; everything else is sourced from existing repositories/services or
the lightweight ``src.utils.metrics`` in-process counters.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psutil
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.repositories.movie_repository import MovieRepository
from src.repositories.user_repository import UserRepository
from src.utils import metrics

_PROCESS = psutil.Process(os.getpid())


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Everything shown on the real-time admin Dashboard screen."""

    cpu_percent: float
    ram_used_mb: float
    ram_percent: float
    disk_used_percent: float
    database_size_mb: float
    media_count: int
    users_today: int
    users_yesterday: int
    users_online_5m: int
    average_response_ms: float
    requests_per_second: float
    total_requests: int
    errors_today: int
    uptime_seconds: float


class SystemService:
    """Computes the real-time numbers shown on the admin Dashboard."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        """Bind this service to a unit-of-work session and the app settings."""
        self._session = session
        self._settings = settings
        self._movies = MovieRepository(session)
        self._users = UserRepository(session)

    def _database_size_mb(self) -> float:
        """Return the on-disk size of the SQLite file in MB, or 0 for other backends."""
        if not self._settings.is_sqlite:
            return 0.0
        path = self._settings.database_url.split("///")[-1]
        try:
            return round(os.path.getsize(path) / (1024 * 1024), 2)
        except OSError:
            return 0.0

    def _disk_used_percent(self) -> float:
        """Return disk usage percent for the Railway Volume (or local disk)."""
        path = self._settings.backup_path if os.path.isdir(self._settings.backup_path) else "/"
        try:
            return psutil.disk_usage(path).percent
        except OSError:
            return 0.0

    async def build_dashboard(self) -> DashboardSnapshot:
        """Compute and return the full real-time dashboard snapshot."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        five_minutes_ago = now - timedelta(minutes=5)

        mem_info = _PROCESS.memory_info()
        metrics_snapshot = metrics.snapshot()

        return DashboardSnapshot(
            cpu_percent=psutil.cpu_percent(interval=0.1),
            ram_used_mb=round(mem_info.rss / (1024 * 1024), 2),
            ram_percent=psutil.virtual_memory().percent,
            disk_used_percent=self._disk_used_percent(),
            database_size_mb=self._database_size_mb(),
            media_count=await self._movies.count_all(include_inactive=True),
            users_today=await self._users.count_joined_since(today_start),
            users_yesterday=await self._users.count_joined_between(yesterday_start, today_start),
            users_online_5m=await self._users.count_active_since(five_minutes_ago),
            average_response_ms=float(metrics_snapshot["average_response_ms"]),
            requests_per_second=float(metrics_snapshot["requests_per_second"]),
            total_requests=int(metrics_snapshot["total_requests"]),
            errors_today=metrics.errors_since(86400),
            uptime_seconds=float(metrics_snapshot["uptime_seconds"]),
        )


async def measure_bot_ping(bot) -> float:  # noqa: ANN001 - aiogram Bot, kept untyped to avoid import cycle
    """Return the round-trip latency (ms) of a cheap Telegram API call."""
    started = time.monotonic()
    await bot.get_me()
    return round((time.monotonic() - started) * 1000, 1)
