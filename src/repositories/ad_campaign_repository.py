"""Persistence for the Advertisement Center."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ad_campaign import AdCampaign
from src.repositories.base import BaseRepository


class AdCampaignRepository(BaseRepository[AdCampaign]):
    """CRUD and scheduling helpers for :class:`AdCampaign`."""

    model = AdCampaign

    async def list_active_now(self) -> list[AdCampaign]:
        """Return active campaigns currently inside their schedule window, by priority."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(AdCampaign)
            .where(AdCampaign.is_active.is_(True))
            .order_by(AdCampaign.priority.desc(), AdCampaign.id.desc())
        )
        campaigns = list(result.scalars().all())
        return [
            campaign
            for campaign in campaigns
            if (campaign.schedule_start is None or campaign.schedule_start <= now)
            and (campaign.schedule_end is None or campaign.schedule_end >= now)
        ]

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[AdCampaign]:
        """Return every campaign ordered by priority, most recent first."""
        result = await self._session.execute(
            select(AdCampaign).order_by(AdCampaign.priority.desc(), AdCampaign.id.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
