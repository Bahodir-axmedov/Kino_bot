"""Injects a per-update database session and service instances.

This is the Dependency Injection seam: every handler/filter simply declares
a parameter (e.g. ``movie_service: MovieService``) and aiogram fills it in
from the ``data`` dict this middleware populates -- no service locator, no
global singletons.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.config import Settings
from src.database.session import session_scope
from src.services.ad_service import AdService
from src.services.admin_security_service import AdminSecurityService
from src.services.admin_service import AdminService
from src.services.backup_service import BackupService
from src.services.blacklist_service import BlacklistService
from src.services.broadcast_service import BroadcastService
from src.services.database_manager_service import DatabaseManagerService
from src.services.discovered_chat_service import DiscoveredChatService
from src.services.force_sub_service import ForceSubService
from src.services.log_service import LogService
from src.services.media_collection_service import MediaCollectionService
from src.services.media_source_service import MediaSourceService
from src.services.movie_service import MovieService
from src.services.notification_service import NotificationService
from src.services.payment_service import PaymentService
from src.services.premium_service import PremiumService
from src.services.referral_reward_service import ReferralRewardService
from src.services.search_log_service import SearchLogService
from src.services.settings_service import SettingsService
from src.services.stats_service import StatsService
from src.services.support_service import SupportService
from src.services.system_log_service import SystemLogService
from src.services.system_service import SystemService
from src.services.user_service import UserService
from src.services.whitelist_service import WhitelistService


class DatabaseMiddleware(BaseMiddleware):
    """Opens one database transaction per update and injects service instances."""

    def __init__(self, session_factory: async_sessionmaker, settings: Settings) -> None:
        """Store the session factory and settings used to build services."""
        super().__init__()
        self._session_factory = session_factory
        self._settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Open a session/transaction, inject services, then commit or roll back."""
        async with session_scope(self._session_factory) as session:
            data["session"] = session
            data["settings"] = self._settings
            data["admin_service"] = AdminService(session, self._settings)
            data["user_service"] = UserService(session)
            data["movie_service"] = MovieService(session)
            data["media_source_service"] = MediaSourceService(session)
            data["discovered_chat_service"] = DiscoveredChatService(session)
            data["force_sub_service"] = ForceSubService(session)
            data["broadcast_service"] = BroadcastService(session)
            data["stats_service"] = StatsService(session)
            data["backup_service"] = BackupService(self._settings)
            data["log_service"] = LogService(session)
            data["system_service"] = SystemService(session, self._settings)
            data["search_log_service"] = SearchLogService(session)
            data["support_service"] = SupportService(session)
            # --- V4.0 platform services -----------------------------------
            data["settings_service"] = SettingsService(session)
            data["media_collection_service"] = MediaCollectionService(session)
            data["blacklist_service"] = BlacklistService(session)
            data["whitelist_service"] = WhitelistService(session)
            data["admin_security_service"] = AdminSecurityService(session)
            data["system_log_service"] = SystemLogService(session)
            data["database_manager_service"] = DatabaseManagerService(session, self._settings)
            data["ad_service"] = AdService(session)
            data["premium_service"] = PremiumService(session)
            data["payment_service"] = PaymentService(session)
            data["referral_reward_service"] = ReferralRewardService(session)
            bot = data.get("bot")
            if bot is not None:
                data["notification_service"] = NotificationService(bot, self._settings)
            return await handler(event, data)
