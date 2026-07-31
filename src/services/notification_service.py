"""Notification Center (#13) -- pushes operational events to the owner/admins.

This service does not persist anything; it is a thin, best-effort fan-out of
short Telegram messages to the configured admin ids whenever a notable
system event happens (new user, new movie, backup ready, error, spam,
bot/Railway restart). Delivery failures are swallowed -- a notification
failure must never break the feature that triggered it.
"""

from __future__ import annotations

import structlog
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from src.config import Settings

logger = structlog.get_logger(__name__)

_EVENT_LABELS: dict[str, str] = {
    "new_user": "\U0001F464 Yangi foydalanuvchi",
    "new_movie": "\U0001F3AC Yangi kino qo'shildi",
    "backup_ready": "\U0001F4E6 Backup tayyor",
    "error": "\u26A0\uFE0F Xatolik",
    "spam": "\U0001F6AB Spam aniqlandi",
    "bot_restart": "\U0001F501 Bot qayta ishga tushdi",
    "railway_restart": "\u2601\uFE0F Railway qayta ishga tushdi",
}


class NotificationService:
    """Sends short operational alerts to every configured admin."""

    def __init__(self, bot: Bot, settings: Settings) -> None:
        """Bind this service to a bot instance and the app settings."""
        self._bot = bot
        self._settings = settings

    async def notify(self, event: str, detail: str = "") -> None:
        """Fan out a single event notification to every admin id (best-effort)."""
        label = _EVENT_LABELS.get(event, event)
        text = f"{label}\n{detail}" if detail else label
        for admin_id in self._settings.admin_ids:
            try:
                await self._bot.send_message(chat_id=admin_id, text=text)
            except TelegramAPIError as error:  # pragma: no cover - best effort
                logger.warning("notification.delivery_failed", admin_id=admin_id, error=str(error))
