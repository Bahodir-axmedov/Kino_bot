"""Service layer: orchestrates repositories and encodes business rules.

Handlers never talk to repositories directly -- they always go through a
service. This keeps Telegram-specific glue code (handlers) fully decoupled
from persistence details (repositories), matching Clean Architecture's
Presentation -> Service -> Repository -> Data layering.
"""

from src.services.admin_security_service import AdminSecurityService
from src.services.admin_service import AdminService
from src.services.ad_service import AdService
from src.services.backup_service import BackupService
from src.services.blacklist_service import BlacklistService
from src.services.broadcast_service import BroadcastService
from src.services.database_manager_service import DatabaseManagerService
from src.services.force_sub_service import ForceSubService
from src.services.log_service import LogService
from src.services.media_collection_service import MediaCollectionService
from src.services.media_source_service import MediaSourceService
from src.services.movie_service import MovieService
from src.services.notification_service import NotificationService
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

__all__ = [
    "AdminSecurityService",
    "AdminService",
    "AdService",
    "BackupService",
    "BlacklistService",
    "BroadcastService",
    "DatabaseManagerService",
    "ForceSubService",
    "LogService",
    "MediaCollectionService",
    "MediaSourceService",
    "MovieService",
    "NotificationService",
    "PremiumService",
    "ReferralRewardService",
    "SearchLogService",
    "SettingsService",
    "StatsService",
    "SupportService",
    "SystemLogService",
    "SystemService",
    "UserService",
    "WhitelistService",
]
