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

# Telegram membership checks are a network round-trip per channel per user.
# Caching a short-TTL "is a member" result keeps the force-sub gate (checked
# on every /start AND every code request, per spec) fast for the very common
# case of a user who checks their subscription repeatedly in a short burst.
_membership_cache: TTLCache[str, bool] = TTLCache(ttl_seconds=30, max_size=20000)


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
        _membership_cache.invalidate(f"{user_id}:{channel_id}")

    async def _is_member(self, bot: Bot, channel: ForceSubChannel, telegram_id: int) -> bool:
        """Resolve membership for one channel, via cache -> Telegram API/confirmation."""
        cache_key = f"{telegram_id}:{channel.id}"
        cached = _membership_cache.get(cache_key)
        if cached is not None:
            return cached

        if channel.platform in TELEGRAM_AUTO_VERIFIABLE_PLATFORMS:
            try:
                member = await bot.get_chat_member(chat_id=channel.chat_id, user_id=telegram_id)
                is_member = member.status in _MEMBER_STATUSES
            except TelegramAPIError:
                # Fail closed: an unreachable/misconfigured channel must not
                # silently disable the force-subscribe gate.
                is_member = False
        elif channel.platform == ForceSubPlatform.TELEGRAM_BOT:
            # A "start the bot" requirement cannot be checked via get_chat_member;
            # treat it the same as an external platform (manual confirmation).
            is_member = await self._confirmations.has_confirmed(telegram_id, channel.id)
        else:
            is_member = await self._confirmations.has_confirmed(telegram_id, channel.id)

        _membership_cache.set(cache_key, is_member)
        return is_member

    async def get_missing_channels(
        self, bot: Bot, telegram_id: int, *, mandatory_only: bool = True
    ) -> list[ForceSubChannel]:
        """Return the subscription targets ``telegram_id`` has not completed yet.

        Checked on every /start and every code request, per spec. Telegram
        membership is verified live (through a short cache); non-Telegram
        platforms rely on the user's own "Tasdiqlash" confirmation.
        """
        channels = await self.list_active()
        if mandatory_only:
            channels = [channel for channel in channels if channel.is_mandatory]
        missing: list[ForceSubChannel] = []
        for channel in channels:
            if not await self._is_member(bot, channel, telegram_id):
                missing.append(channel)
        return missing
