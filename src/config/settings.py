"""Application configuration loaded exclusively from environment variables.

No secret or environment-specific value is ever hardcoded in source code.
All values are validated by pydantic at process startup, so misconfiguration
fails fast instead of surfacing as a runtime error deep in the bot.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(raw: str | None) -> list[str]:
    """Split a comma separated environment value into a clean list of tokens."""
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


class Settings(BaseSettings):
    """Strongly typed, validated application settings.

    All fields are sourced from environment variables (optionally loaded
    from a local ``.env`` file). See ``.env.example`` for the full list of
    supported variables and their meaning.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Telegram ---
    bot_token: str = Field(..., alias="BOT_TOKEN")
    bot_username: str = Field(default="", alias="BOT_USERNAME")
    owner_id: int = Field(..., alias="OWNER_ID")
    admins_raw: str = Field(default="", alias="ADMINS")

    # --- Database ---
    database_url: str = Field(
        default="sqlite+aiosqlite:////data/database.sqlite3",
        alias="DATABASE_URL",
    )

    # --- Cache ---
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    logs_path: str = Field(default="/data/logs", alias="LOGS_PATH")

    # --- Webhook / Polling ---
    use_webhook: bool = Field(default=False, alias="USE_WEBHOOK")
    webhook_url: str | None = Field(default=None, alias="WEBHOOK_URL")
    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")

    # --- Force Subscribe ---
    force_sub_channels_raw: str = Field(default="", alias="FORCE_SUB_CHANNELS")

    # --- Localization ---
    default_language: str = Field(default="uz", alias="DEFAULT_LANGUAGE")
    timezone: str = Field(default="Asia/Tashkent", alias="TIMEZONE")

    # --- Security ---
    secret_key: str = Field(..., alias="SECRET_KEY")
    rate_limit: float = Field(default=5.0, alias="RATE_LIMIT")

    # --- Storage ---
    backup_path: str = Field(default="/data/backups", alias="BACKUP_PATH")

    # --- Media Sources ---
    media_channel_ids_raw: str = Field(default="", alias="MEDIA_CHANNEL_IDS")
    media_group_ids_raw: str = Field(default="", alias="MEDIA_GROUP_IDS")

    # --- Limits & Features ---
    max_upload_size: int = Field(default=2000, alias="MAX_UPLOAD_SIZE")
    premium_enabled: bool = Field(default=True, alias="PREMIUM_ENABLED")

    @field_validator("database_url")
    @classmethod
    def _ensure_sqlite_dir_or_pass_through(cls, value: str) -> str:
        """Ensure the parent directory of a local SQLite file exists."""
        if value.startswith("sqlite"):
            path_part = value.split(":///")[-1]
            if path_part and path_part != ":memory:":
                Path(path_part).parent.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def admin_ids(self) -> set[int]:
        """Return the statically configured admin Telegram IDs, owner included."""
        ids = {int(token) for token in _split_csv(self.admins_raw) if token.lstrip("-").isdigit()}
        ids.add(self.owner_id)
        return ids

    @property
    def force_sub_channels(self) -> list[str]:
        """Return the statically configured force-subscribe channel identifiers."""
        return _split_csv(self.force_sub_channels_raw)

    @property
    def media_channel_ids(self) -> list[int]:
        """Return configured media channel chat ids."""
        return [int(token) for token in _split_csv(self.media_channel_ids_raw) if token.lstrip("-").isdigit()]

    @property
    def media_group_ids(self) -> list[int]:
        """Return configured media group chat ids."""
        return [int(token) for token in _split_csv(self.media_group_ids_raw) if token.lstrip("-").isdigit()]

    @property
    def is_sqlite(self) -> bool:
        """Return True when the configured database backend is SQLite."""
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached ``Settings`` singleton.

    Using ``lru_cache`` keeps settings creation side-effect free while still
    guaranteeing a single parsed/validated instance across the whole app,
    which plays well with dependency injection in handlers and services.
    """
    return Settings()  # type: ignore[call-arg]
