"""Persistence for Settings Center key/value rows."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bot_setting import BotSetting
from src.repositories.base import BaseRepository


class BotSettingRepository(BaseRepository[BotSetting]):
    """CRUD helpers for :class:`BotSetting` keyed by its unique ``key``."""

    model = BotSetting

    async def get_by_key(self, key: str) -> BotSetting | None:
        """Return the setting row for ``key``, or ``None`` if unset."""
        result = await self._session.execute(select(BotSetting).where(BotSetting.key == key))
        return result.scalar_one_or_none()

    async def list_by_category(self, category: str) -> list[BotSetting]:
        """Return every setting row belonging to ``category``, ordered by key."""
        result = await self._session.execute(
            select(BotSetting).where(BotSetting.category == category).order_by(BotSetting.key)
        )
        return list(result.scalars().all())

    async def list_all(self, limit: int = 500, offset: int = 0) -> list[BotSetting]:
        """Return every setting row, ordered by category then key."""
        result = await self._session.execute(
            select(BotSetting).order_by(BotSetting.category, BotSetting.key).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
