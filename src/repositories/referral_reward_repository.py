"""Persistence for the Referral System reward ledger."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.referral_reward import ReferralReward
from src.repositories.base import BaseRepository


class ReferralRewardRepository(BaseRepository[ReferralReward]):
    """Read/write helpers for :class:`ReferralReward`."""

    model = ReferralReward

    async def list_for_user(self, user_id: int) -> list[ReferralReward]:
        """Return every reward row for ``user_id``, most recent first."""
        result = await self._session.execute(
            select(ReferralReward).where(ReferralReward.user_id == user_id).order_by(ReferralReward.id.desc())
        )
        return list(result.scalars().all())

    async def total_amount_for_user(self, user_id: int) -> int:
        """Return the sum of all reward amounts granted to ``user_id``."""
        result = await self._session.execute(
            select(func.coalesce(func.sum(ReferralReward.amount), 0)).where(ReferralReward.user_id == user_id)
        )
        return int(result.scalar_one())
