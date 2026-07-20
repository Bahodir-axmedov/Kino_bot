"""Settings Center (V4.0): admin-editable configuration stored in the database.

Every value the admin should be able to change without touching code or
redeploying (bot name, messages, limits, feature toggles) lives here as a
single typed key/value row instead of being hardcoded or environment-only.
Environment variables (``src.config.settings``) remain the *bootstrap*
defaults; a row in this table always takes precedence once set.
"""

from __future__ import annotations

import enum

from sqlalchemy import BigInteger, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class SettingValueType(str, enum.Enum):
    """How a setting's raw string value should be interpreted."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"


class BotSetting(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single admin-configurable setting, addressed by a unique string key."""

    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[SettingValueType] = mapped_column(
        SAEnum(SettingValueType, name="setting_value_type"),
        nullable=False,
        default=SettingValueType.STRING,
        server_default=SettingValueType.STRING.value,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general", index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"BotSetting(key={self.key!r}, value={self.value!r})"
