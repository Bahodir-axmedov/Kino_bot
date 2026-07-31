"""Broadcast/advertisement delivery to every registered user."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.broadcast import Broadcast, BroadcastStatus
from src.repositories.broadcast_repository import BroadcastRepository
from src.repositories.user_repository import UserRepository
from src.utils.retry import async_retry

logger = structlog.get_logger(__name__)

_BATCH_SIZE = 25
_BATCH_DELAY_SECONDS = 1.0


class BroadcastService:
    """Encapsulates composing, sending, and tracking broadcast campaigns."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = BroadcastRepository(session)
        self._users = UserRepository(session)

    async def create_campaign(
        self,
        *,
        admin_id: int,
        content_type: str,
        source_chat_id: int | None,
        source_message_id: int | None,
        message_text: str | None,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> Broadcast:
        """Persist a new, not-yet-sent broadcast campaign row."""
        campaign = Broadcast(
            admin_id=admin_id,
            content_type=content_type,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            message_text=message_text,
            reply_markup_json=(
                reply_markup.model_dump_json() if reply_markup is not None else None
            ),
            status=BroadcastStatus.PENDING,
        )
        return await self._repository.add(campaign)

    async def send_campaign(self, bot: Bot, campaign: Broadcast) -> Broadcast:
        """Send a campaign to every non-banned user in controlled batches.

        Delivery is throttled in small batches with a short delay to respect
        Telegram's flood limits, and every per-user failure is captured
        instead of aborting the whole run.
        """
        recipient_ids = await self._users.list_all_ids(exclude_banned=True)
        campaign.total_users = len(recipient_ids)
        campaign.status = BroadcastStatus.RUNNING
        campaign.started_at = datetime.now(timezone.utc)
        await self._repository.flush()

        reply_markup = (
            InlineKeyboardMarkup.model_validate_json(campaign.reply_markup_json)
            if campaign.reply_markup_json
            else None
        )

        for start in range(0, len(recipient_ids), _BATCH_SIZE):
            batch = recipient_ids[start : start + _BATCH_SIZE]
            await asyncio.gather(
                *(
                    self._deliver_one(bot, campaign, telegram_id, reply_markup)
                    for telegram_id in batch
                )
            )
            await self._repository.flush()
            await asyncio.sleep(_BATCH_DELAY_SECONDS)

        campaign.status = BroadcastStatus.COMPLETED
        campaign.finished_at = datetime.now(timezone.utc)
        await self._repository.flush()
        return campaign

    async def _deliver_one(
        self,
        bot: Bot,
        campaign: Broadcast,
        telegram_id: int,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> None:
        """Deliver a single broadcast message, recording success or failure."""
        try:
            await self._send_with_retry(bot, campaign, telegram_id, reply_markup)
            campaign.sent_count += 1
        except TelegramForbiddenError:
            campaign.failed_count += 1
            await self._repository.add_failed_user(
                campaign.id, telegram_id, "Foydalanuvchi botni bloklagan"
            )
        except TelegramAPIError as error:
            campaign.failed_count += 1
            await self._repository.add_failed_user(campaign.id, telegram_id, str(error))
        except Exception as error:  # noqa: BLE001 - captured for the failed-user log
            logger.error("broadcast.unexpected_error", telegram_id=telegram_id, error=str(error))
            campaign.failed_count += 1
            await self._repository.add_failed_user(campaign.id, telegram_id, str(error))

    @async_retry(attempts=3, base_delay_seconds=0.5, exceptions=(TelegramRetryAfter,))
    async def _send_with_retry(
        self,
        bot: Bot,
        campaign: Broadcast,
        telegram_id: int,
        reply_markup: InlineKeyboardMarkup | None,
    ) -> None:
        """Send one message, retrying automatically on flood-control waits."""
        if campaign.source_chat_id and campaign.source_message_id:
            await bot.copy_message(
                chat_id=telegram_id,
                from_chat_id=campaign.source_chat_id,
                message_id=campaign.source_message_id,
                reply_markup=reply_markup,
            )
        else:
            await bot.send_message(
                chat_id=telegram_id, text=campaign.message_text or "", reply_markup=reply_markup
            )

    async def list_recent(self, limit: int = 10) -> list[Broadcast]:
        """Return the most recent broadcast campaigns."""
        return list(await self._repository.list_recent(limit=limit))

    async def list_failed_users(self, broadcast_id: int) -> list[dict[str, object]]:
        """Return the failed-delivery log for a campaign as plain dicts."""
        failed = await self._repository.list_failed_users(broadcast_id)
        return [
            {"telegram_id": item.telegram_id, "error": item.error_message} for item in failed
        ]
