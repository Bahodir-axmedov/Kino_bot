"""Mandatory-subscription (force-subscribe) center: enforcement + management.

Supports both Telegram entities (auto-verified via ``get_chat_member``) and
non-Telegram platforms (Instagram/YouTube/TikTok/Facebook/X/Website), which
can only be verified through a manual "Tasdiqlash" confirmation tap.
"""

from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.force_sub_channel import (
    TELEGRAM_AUTO_VERIFIABLE_PLATFORMS,
    ForceSubChannel,
    ForceSubPlatform,
)
from src.repositories.force_sub_confirmation_repository import ForceSubConfirmationRepository
from src.repositories.force_sub_repository import ForceSubRepository
from src.utils.cache import TTLCache

_MEMBER_STATUSES = {"member", "administrator", "creator"}

# Only the non-Telegram ("Tasdiqlash"-confirmed) targets are cached here.
# Real Telegram channels/groups are ALWAYS re-checked live against
# get_chat_member -- caching that result previously let a user who left a
# mandatory channel keep bypassing the gate for up to the cache's TTL, which
# defeats the whole point of a mandatory-subscription check. Confirmation
# taps for external platforms can't be verified live at all, so caching
# those (to save a DB round trip per channel per check) is safe: nothing
# ever needs to *revoke* a confirmation behind the user's back.
_confirmation_cache: TTLCache[str, bool] = TTLCache(ttl_seconds=30, max_size=20000)


class ForceSubService:
    """Encapsulates every business rule about mandatory-subscription gating."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = ForceSubRepository(session)
        self._confirmations = ForceSubConfirmationRepository(session)

    async def list_active(self) -> list[ForceSubChannel]:
        """Return every currently enforced mandatory-subscription channel."""
        return list(await self._repository.list_active())

    async def list_all(self) -> list[ForceSubChannel]:
        """Return every configured subscription target (mandatory + optional)."""
        return list(await self._repository.list_all())

    async def add_telegram_channel(
        self,
        *,
        platform: ForceSubPlatform,
        chat_id: int,
        title: str,
        chat_username: str | None,
        invite_link: str | None,
        is_mandatory: bool,
        added_by: int,
    ) -> ForceSubChannel:
        """Register a new Telegram-verifiable subscription target."""
        existing = await self._repository.get_by_chat_id(chat_id)
        if existing is not None:
            existing.title = title
            existing.chat_username = chat_username
            existing.invite_link = invite_link
            existing.is_active = True
            existing.is_mandatory = is_mandatory
            existing.platform = platform
            await self._repository.flush()
            return existing
        channel = ForceSubChannel(
            platform=platform,
            chat_id=chat_id,
            title=title,
            chat_username=chat_username,
            invite_link=invite_link,
            is_mandatory=is_mandatory,
            added_by=added_by,
            is_active=True,
        )
        return await self._repository.add(channel)

    async def add_external_target(
        self,
        *,
        platform: ForceSubPlatform,
        title: str,
        url: str,
        instructions: str | None,
        is_mandatory: bool,
        added_by: int,
    ) -> ForceSubChannel:
        """Register a non-Telegram subscription target (manual confirmation only)."""
        channel = ForceSubChannel(
            platform=platform,
            title=title,
            url=url,
            instructions=instructions,
            is_mandatory=is_mandatory,
            added_by=added_by,
            is_active=True,
        )
        return await self._repository.add(channel)

    async def remove_channel(self, channel_id: int) -> bool:
        """Permanently remove a subscription target."""
        channel = await self._repository.get_by_id(channel_id)
        if channel is None:
            return False
        await self._repository.delete(channel)
        return True

    async def toggle_channel(self, channel_id: int) -> ForceSubChannel | None:
        """Flip a channel's enforced/inactive state."""
        channel = await self._repository.get_by_id(channel_id)
        if channel is None:
            return None
        channel.is_active = not channel.is_active
        await self._repository.flush()
        return channel

    async def toggle_mandatory(self, channel_id: int) -> ForceSubChannel | None:
        """Flip a channel between Majburiy (mandatory) and Ixtiyoriy (optional)."""
        channel = await self._repository.get_by_id(channel_id)
        if channel is None:
            return None
        channel.is_mandatory = not channel.is_mandatory
        await self._repository.flush()
        return channel

    async def confirm_external(self, user_id: int, channel_id: int) -> None:
        """Record a user's manual "Tasdiqlash" tap for a non-Telegram channel."""
        await self._confirmations.confirm(user_id, channel_id)
        _confirmation_cache.invalidate(f"{user_id}:{channel_id}")

    async def _is_member(self, bot: Bot, channel: ForceSubChannel, telegram_id: int) -> bool:
        """Resolve membership for one channel.

        Real Telegram channels/groups/discussion-groups are always checked
        live via ``get_chat_member`` -- never cached -- so a user who leaves
        right after passing the gate is caught on their very next action
        (next /start, next code request, next "Tekshirish" tap), not only
        after some caching window expires. Non-Telegram platforms have no
        API to check live at all, so they still rely on (and cache) the
        user's own manual "Tasdiqlash" confirmation.
        """
        if channel.platform in TELEGRAM_AUTO_VERIFIABLE_PLATFORMS:
            try:
                member = await bot.get_chat_member(chat_id=channel.chat_id, user_id=telegram_id)
                return member.status in _MEMBER_STATUSES
            except TelegramAPIError:
                # Fail closed: an unreachable/misconfigured channel must not
                # silently disable the force-subscribe gate.
                return False

        # TELEGRAM_BOT ("start the bot") and every external platform can only
        # be verified through the user's own confirmation tap.
        cache_key = f"{telegram_id}:{channel.id}"
        cached = _confirmation_cache.get(cache_key)
        if cached is not None:
            return cached
        is_confirmed = await self._confirmations.has_confirmed(telegram_id, channel.id)
        _confirmation_cache.set(cache_key, is_confirmed)
        return is_confirmed

    async def get_missing_channels(
        self, bot: Bot, telegram_id: int, *, mandatory_only: bool = True
    ) -> list[ForceSubChannel]:
        """Return the subscription targets ``telegram_id`` has not completed yet.

        Checked on every /start and every code request, per spec. Telegram
        membership is always verified live (never cached), so a user who
        leaves a mandatory channel is caught immediately on their next
        action; non-Telegram platforms rely on the user's own "Tasdiqlash"
        confirmation.
        """
        channels = await self.list_active()
        if mandatory_only:
            channels = [channel for channel in channels if channel.is_mandatory]
        missing: list[ForceSubChannel] = []
        for channel in channels:
            if not await self._is_member(bot, channel, telegram_id):
                missing.append(channel)
        return missing
