"""Typed callback-data factories (aiogram ``CallbackData``).

Using typed callback data (instead of hand-built ``":"``-joined strings)
gives us validation and parsing for free, which is part of the FSM/callback
security surface: malformed or spoofed callback payloads fail to parse
rather than being blindly trusted.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class AdminMenuCallback(CallbackData, prefix="admin_menu"):
    """Navigate between admin panel sections."""

    section: str


class MovieActionCallback(CallbackData, prefix="movie_act"):
    """Act on a specific movie by id (edit/delete/duplicate-check/etc)."""

    action: str
    movie_id: int


class UserActionCallback(CallbackData, prefix="user_act"):
    """Act on a specific user by Telegram id (ban/unban/mute/premium/etc)."""

    action: str
    telegram_id: int


class ForceSubActionCallback(CallbackData, prefix="fsub_act"):
    """Act on a force-subscribe channel by id (remove/toggle)."""

    action: str
    channel_id: int


class ForceSubCheckCallback(CallbackData, prefix="fsub_check"):
    """User confirms they have joined all mandatory channels."""

    movie_code: str


class ForceSubPlatformCallback(CallbackData, prefix="fsub_platform"):
    """Admin picks which platform type to add to the mandatory-subscription center."""

    platform: str


class ForceSubConfirmCallback(CallbackData, prefix="fsub_confirm"):
    """User taps "Tasdiqlash" for a non-Telegram (manually verified) platform.

    ``movie_code`` is "-" when the confirmation happened from the /start gate
    (no pending code delivery to retry afterwards).
    """

    channel_id: int
    movie_code: str


class BroadcastConfirmCallback(CallbackData, prefix="bcast"):
    """Confirm or cancel a composed broadcast before it is sent."""

    action: str


class PaginationCallback(CallbackData, prefix="page"):
    """Move to another page within a paginated list view."""

    scope: str
    index: int


class SettingsCategoryCallback(CallbackData, prefix="settings_cat"):
    """Open one Settings Center category screen."""

    category: str


class SettingsEditCallback(CallbackData, prefix="settings_edit"):
    """Edit (or toggle) a single Settings Center key."""

    key: str


class CollectionActionCallback(CallbackData, prefix="collection_act"):
    """Act on a Media Collection (activate/deactivate/delete/rename/move up-down)."""

    action: str
    collection_id: int


class BlacklistTypeCallback(CallbackData, prefix="blacklist_type"):
    """Admin picks which entry type to view/add in the Blacklist Center."""

    entry_type: str


class BlacklistActionCallback(CallbackData, prefix="blacklist_act"):
    """Act on an existing Blacklist Center entry (remove)."""

    entry_id: int


class WhitelistTypeCallback(CallbackData, prefix="whitelist_type"):
    """Admin picks which entry type to view/add in the Whitelist Center."""

    entry_type: str


class WhitelistActionCallback(CallbackData, prefix="whitelist_act"):
    """Act on an existing Whitelist Center entry (remove)."""

    entry_id: int


class AdActionCallback(CallbackData, prefix="ad_act"):
    """Act on an Advertisement Center campaign (toggle/delete)."""

    action: str
    campaign_id: int


class SecurityActionCallback(CallbackData, prefix="security_act"):
    """Act within the admin Security Center (set PIN/enable 2FA/disable 2FA/logout-all)."""

    action: str


class LogFilterCallback(CallbackData, prefix="log_filter"):
    """Filter the Log Center list by level (or \"all\")."""

    level: str


class DatabaseActionCallback(CallbackData, prefix="db_act"):
    """Act on the live database from the Database Manager screen."""

    action: str


# --- Zero-typing chat discovery (tap-to-pick channels/groups) --------------
#
# ``purpose`` and ``sub_type`` intentionally use short 2-3 char codes (not the
# full enum value strings) to keep the packed callback_data comfortably under
# Telegram's 64-byte limit even for the longest chat ids.
#   purpose:   "fs" = Force Subscribe, "ms" = Media Source
#   sub_type:  "tc"/"tg"/"tdg" = Telegram channel/group/discussion group
#              "ch"/"gr" = media-source channel/group


class DiscoveredChatCallback(CallbackData, prefix="disc_pick"):
    """Admin taps a bot-discovered channel/group to register it, with no typing."""

    purpose: str
    sub_type: str
    chat_id: int


class MediaSourceTypeCallback(CallbackData, prefix="msrc_type"):
    """Admin picks channel vs. group before seeing the tap-to-pick list."""

    source_type: str


class MediaSourceActionCallback(CallbackData, prefix="msrc_act"):
    """Act on a configured Media Source (remove/add)."""

    action: str
    chat_id: int


class PremiumBuyCallback(CallbackData, prefix="prem_buy"):
    """User picks how to buy Premium (stars/card) or confirms a card payment."""

    method: str


class PaymentReviewCallback(CallbackData, prefix="pay_review"):
    """Admin approves or rejects a pending card payment request."""

    action: str
    request_id: int
