"""Advertisement Center (V4.0): admin-created ads shown every N searches."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.ad_campaign import AdCampaign, AdContentType
from src.repositories.ad_campaign_repository import AdCampaignRepository
from src.utils.exceptions import InvalidInputError


class AdService:
    """Create/manage ad campaigns and decide when to show one."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = AdCampaignRepository(session)

    async def create(
        self,
        *,
        content_type: AdContentType,
        text: str | None = None,
        file_id: str | None = None,
        button_text: str | None = None,
        button_url: str | None = None,
        schedule_start: datetime | None = None,
        schedule_end: datetime | None = None,
        priority: int = 0,
        trigger_every_n_searches: int = 10,
        created_by: int | None = None,
    ) -> AdCampaign:
        """Create a new advertisement campaign."""
        if trigger_every_n_searches <= 0:
            raise InvalidInputError("Qidiruv oralig'i musbat son bo'lishi kerak.")
        campaign = AdCampaign(
            content_type=content_type,
            text=text,
            file_id=file_id,
            button_text=button_text,
            button_url=button_url,
            schedule_start=schedule_start,
            schedule_end=schedule_end,
            priority=priority,
            trigger_every_n_searches=trigger_every_n_searches,
            created_by=created_by,
        )
        return await self._repository.add(campaign)

    async def set_active(self, campaign_id: int, is_active: bool) -> AdCampaign:
        """Enable or disable an existing campaign."""
        campaign = await self._repository.get_by_id(campaign_id)
        if campaign is None:
            raise InvalidInputError("Reklama topilmadi.")
        campaign.is_active = is_active
        await self._repository.flush()
        return campaign

    async def delete(self, campaign_id: int) -> None:
        """Permanently delete a campaign."""
        campaign = await self._repository.get_by_id(campaign_id)
        if campaign is None:
            raise InvalidInputError("Reklama topilmadi.")
        await self._repository.delete(campaign)

    async def list_all(self) -> list[AdCampaign]:
        """Return every campaign, highest priority first."""
        return await self._repository.list_all()

    async def pick_campaign_for_search_count(self, search_count: int) -> AdCampaign | None:
        """Return the highest-priority active campaign whose interval divides ``search_count``.

        ``search_count`` is expected to be the user's/global running search
        counter; a campaign with ``trigger_every_n_searches=10`` fires on
        searches 10, 20, 30, ...
        """
        if search_count <= 0:
            return None
        for campaign in await self._repository.list_active_now():
            if campaign.trigger_every_n_searches > 0 and search_count % campaign.trigger_every_n_searches == 0:
                campaign.impressions_count += 1
                await self._repository.flush()
                return campaign
        return None
