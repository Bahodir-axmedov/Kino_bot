"""Settings Center (V4.0): DB-backed configuration the admin edits without code.

Every value is stored as a typed ``BotSetting`` row. ``Settings`` (env vars)
remain the bootstrap defaults used the very first time a key is read; once an
admin sets a value through the panel, the database row always wins.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bot_setting import BotSetting, SettingValueType
from src.repositories.bot_setting_repository import BotSettingRepository

#: Every key the Settings Center exposes, grouped by category, with defaults.
#: Kept as plain data (not hardcoded branching) so new settings only require
#: a new entry here -- no new code path.
DEFAULT_SETTINGS: dict[str, dict[str, Any]] = {
    "bot_name": {"category": "general", "type": SettingValueType.STRING, "default": "Kino Bot"},
    "bot_username": {"category": "general", "type": SettingValueType.STRING, "default": ""},
    "bot_description": {"category": "general", "type": SettingValueType.STRING, "default": ""},
    "start_message": {"category": "messages", "type": SettingValueType.STRING, "default": ""},
    "about_message": {"category": "messages", "type": SettingValueType.STRING, "default": ""},
    "help_message": {"category": "messages", "type": SettingValueType.STRING, "default": ""},
    "support_username": {"category": "support", "type": SettingValueType.STRING, "default": ""},
    "support_group": {"category": "support", "type": SettingValueType.STRING, "default": ""},
    "default_language": {"category": "general", "type": SettingValueType.STRING, "default": "uz"},
    "timezone": {"category": "general", "type": SettingValueType.STRING, "default": "Asia/Tashkent"},
    "maintenance_mode": {"category": "maintenance", "type": SettingValueType.BOOLEAN, "default": False},
    "maintenance_message": {
        "category": "maintenance",
        "type": SettingValueType.STRING,
        "default": "Tizimda texnik ishlar ketmoqda.",
    },
    "rate_limit_per_minute": {"category": "limits", "type": SettingValueType.INTEGER, "default": 20},
    "flood_limit_per_minute": {"category": "limits", "type": SettingValueType.INTEGER, "default": 10},
    "premium_enabled": {"category": "premium", "type": SettingValueType.BOOLEAN, "default": True},
    "premium_price_stars": {"category": "premium", "type": SettingValueType.INTEGER, "default": 50},
    "premium_price_uzs": {"category": "premium", "type": SettingValueType.INTEGER, "default": 20000},
    "premium_duration_days": {"category": "premium", "type": SettingValueType.INTEGER, "default": 30},
    "stars_payment_enabled": {"category": "premium", "type": SettingValueType.BOOLEAN, "default": True},
    "card_payment_enabled": {"category": "premium", "type": SettingValueType.BOOLEAN, "default": True},
    "payment_card_number": {"category": "premium", "type": SettingValueType.STRING, "default": ""},
    "payment_card_holder": {"category": "premium", "type": SettingValueType.STRING, "default": ""},
    "payment_card_bank": {"category": "premium", "type": SettingValueType.STRING, "default": "Uzcard / Humo"},
    "premium_features_text": {"category": "premium", "type": SettingValueType.STRING, "default": ""},
    "referral_enabled": {"category": "referral", "type": SettingValueType.BOOLEAN, "default": True},
    "referral_bonus_amount": {"category": "referral", "type": SettingValueType.INTEGER, "default": 1},
    "referral_premium_bonus_threshold": {"category": "referral", "type": SettingValueType.INTEGER, "default": 10},
    "force_subscribe_enabled": {"category": "force_subscribe", "type": SettingValueType.BOOLEAN, "default": True},
    "media_watermark_enabled": {"category": "media", "type": SettingValueType.BOOLEAN, "default": False},
    "media_caption_protection_enabled": {"category": "media", "type": SettingValueType.BOOLEAN, "default": False},
    "media_forward_protection_enabled": {"category": "media", "type": SettingValueType.BOOLEAN, "default": False},
    "scheduler_optimize_enabled": {"category": "scheduler", "type": SettingValueType.BOOLEAN, "default": True},
    "backup_frequency": {"category": "backup", "type": SettingValueType.STRING, "default": "daily"},
    "backup_retention_count": {"category": "backup", "type": SettingValueType.INTEGER, "default": 14},
    "database_auto_optimize_enabled": {"category": "database", "type": SettingValueType.BOOLEAN, "default": True},
    "logging_level": {"category": "logging", "type": SettingValueType.STRING, "default": "INFO"},
    "notification_center_enabled": {"category": "notifications", "type": SettingValueType.BOOLEAN, "default": True},
    "railway_deploy_version": {"category": "railway", "type": SettingValueType.STRING, "default": ""},
    "railway_environment": {"category": "railway", "type": SettingValueType.STRING, "default": "production"},
    "ad_display_every_n_searches": {"category": "advertisement", "type": SettingValueType.INTEGER, "default": 10},
    "admin_login_max_attempts": {"category": "security", "type": SettingValueType.INTEGER, "default": 3},
    "admin_login_lockout_minutes": {"category": "security", "type": SettingValueType.INTEGER, "default": 10},
    "admin_session_timeout_minutes": {"category": "security", "type": SettingValueType.INTEGER, "default": 60},
}


def _serialize(value: Any, value_type: SettingValueType) -> str | None:
    """Convert a Python value into the string form stored in ``BotSetting.value``."""
    if value is None:
        return None
    if value_type is SettingValueType.BOOLEAN:
        return "1" if value else "0"
    if value_type is SettingValueType.JSON:
        return json.dumps(value)
    return str(value)


def _deserialize(raw: str | None, value_type: SettingValueType, default: Any) -> Any:
    """Convert a stored string back into its typed Python value."""
    if raw is None:
        return default
    if value_type is SettingValueType.BOOLEAN:
        return raw == "1"
    if value_type is SettingValueType.INTEGER:
        return int(raw)
    if value_type is SettingValueType.FLOAT:
        return float(raw)
    if value_type is SettingValueType.JSON:
        return json.loads(raw)
    return raw


class SettingsService:
    """Reads and writes every admin-configurable setting (Settings Center)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = BotSettingRepository(session)

    async def get(self, key: str) -> Any:
        """Return the current typed value for ``key`` (DB row, else the registered default)."""
        spec = DEFAULT_SETTINGS.get(key, {"type": SettingValueType.STRING, "default": None})
        row = await self._repository.get_by_key(key)
        if row is None:
            return spec["default"]
        return _deserialize(row.value, row.value_type, spec["default"])

    async def set(self, key: str, value: Any, *, updated_by: int | None = None) -> BotSetting:
        """Upsert ``key`` to ``value``, creating the row on first write."""
        spec = DEFAULT_SETTINGS.get(key, {"category": "custom", "type": SettingValueType.STRING})
        value_type: SettingValueType = spec["type"]
        row = await self._repository.get_by_key(key)
        serialized = _serialize(value, value_type)
        if row is None:
            row = BotSetting(
                key=key,
                value=serialized,
                value_type=value_type,
                category=spec.get("category", "custom"),
                updated_by=updated_by,
            )
            return await self._repository.add(row)
        row.value = serialized
        row.updated_by = updated_by
        await self._repository.flush()
        return row

    async def get_all(self) -> dict[str, Any]:
        """Return every registered setting key with its current effective value."""
        return {key: await self.get(key) for key in DEFAULT_SETTINGS}

    async def list_by_category(self, category: str) -> dict[str, Any]:
        """Return every setting key in ``category`` with its current effective value."""
        return {
            key: await self.get(key)
            for key, spec in DEFAULT_SETTINGS.items()
            if spec.get("category") == category
        }

    async def is_maintenance_mode(self) -> bool:
        """Convenience accessor used by the maintenance-mode gate on every update."""
        return bool(await self.get("maintenance_mode"))

    async def maintenance_message(self) -> str:
        """Convenience accessor for the message shown to blocked non-admin users."""
        return str(await self.get("maintenance_message"))
