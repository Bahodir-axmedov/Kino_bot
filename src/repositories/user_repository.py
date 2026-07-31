"""Data-access operations for the ``User`` aggregate."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select

from src.models.user import User
from src.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository encapsulating all SQL access for ``User`` rows."""

    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Return the user with the given Telegram id, or ``None``."""
        return await self._session.get(User, telegram_id)

    async def search_by_username_or_id(self, query: str, limit: int = 20) -> Sequence[User]:
        """Search users by exact Telegram id or partial username match."""
        statement = select(User)
        if query.lstrip("-").isdigit():
            statement = statement.where(User.telegram_id == int(query))
        else:
            needle = query.lstrip("@")
            statement = statement.where(User.username.ilike(f"%{needle}%"))
        statement = statement.limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def count_all(self) -> int:
        """Return the total number of registered users."""
        result = await self._session.execute(select(func.count(User.telegram_id)))
        return int(result.scalar_one())

    async def count_premium(self) -> int:
        """Return the number of currently premium users."""
        result = await self._session.execute(
            select(func.count(User.telegram_id)).where(User.is_premium.is_(True))
        )
        return int(result.scalar_one())

    async def count_joined_since(self, since: datetime) -> int:
        """Return the number of users who joined on/after the given timestamp."""
        result = await self._session.execute(
            select(func.count(User.telegram_id)).where(User.joined_at >= since)
        )
        return int(result.scalar_one())

    async def count_joined_between(self, start: datetime, end: datetime) -> int:
        """Return the number of users who joined within ``[start, end)``."""
        result = await self._session.execute(
            select(func.count(User.telegram_id)).where(
                User.joined_at >= start, User.joined_at < end
            )
        )
        return int(result.scalar_one())

    async def count_active_since(self, since: datetime) -> int:
        """Return the number of users active on/after the given timestamp."""
        result = await self._session.execute(
            select(func.count(User.telegram_id)).where(User.last_active_at >= since)
        )
        return int(result.scalar_one())

    async def list_all_ids(self, *, exclude_banned: bool = True) -> Sequence[int]:
        """Return the Telegram ids of every user, optionally excluding banned ones.

        Used by the broadcast service to build its recipient list.
        """
        statement = select(User.telegram_id)
        if exclude_banned:
            statement = statement.where(User.is_banned.is_(False))
        result = await self._session.execute(statement)
        return result.scalars().all()
