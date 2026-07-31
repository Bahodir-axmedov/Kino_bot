"""Referral System (V4.0): bonuses, top referrers, and reward history."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.referral_reward import ReferralReward
from src.models.user import User
from src.repositories.referral_reward_repository import ReferralRewardRepository
from src.repositories.user_repository import UserRepository
from src.services.premium_service import PremiumService
from src.services.settings_service import SettingsService


class ReferralRewardService:
    """Grants referral bonuses and reports referral statistics."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = ReferralRewardRepository(session)
        self._user_repository = UserRepository(session)
        self._settings = SettingsService(session)
        self._premium = PremiumService(session)

    async def grant_invite_bonus(self, referrer_id: int) -> ReferralReward:
        """Grant the standard per-invite bonus, and a Premium Bonus at the configured threshold."""
        amount = int(await self._settings.get("referral_bonus_amount"))
        reward = ReferralReward(
            user_id=referrer_id,
            reward_type="invite_bonus",
            amount=amount,
            granted_at=datetime.now(timezone.utc),
        )
        await self._repository.add(reward)

        referrer = await self._user_repository.get_by_id(referrer_id)
        threshold = int(await self._settings.get("referral_premium_bonus_threshold"))
        if referrer is not None and threshold > 0 and referrer.invite_count > 0 and referrer.invite_count % threshold == 0:
            await self._premium.grant(referrer_id, days=30, plan="referral_bonus", granted_by=None)
            await self._repository.add(
                ReferralReward(
                    user_id=referrer_id,
                    reward_type="premium_bonus",
                    amount=1,
                    note=f"{threshold} taklifga yetgani uchun Premium bonus",
                    granted_at=datetime.now(timezone.utc),
                )
            )
        return reward

    async def history_for_user(self, user_id: int) -> list[ReferralReward]:
        """Return every reward granted to a user, most recent first."""
        return await self._repository.list_for_user(user_id)

    async def total_rewards_for_user(self, user_id: int) -> int:
        """Return the total reward amount granted to a user."""
        return await self._repository.total_amount_for_user(user_id)

    async def top_referrers(self, limit: int = 10) -> list[User]:
        """Return the users with the highest ``invite_count``, descending."""
        result = await self._session.execute(
            select(User).where(User.invite_count > 0).order_by(User.invite_count.desc()).limit(limit)
        )
        return list(result.scalars().all())
