"""V4.0 platform features: settings center, collections, blacklist/whitelist,
admin login protection, log center, backup metadata, ads, premium/referral history

Revision ID: 0004_v4_platform_features
Revises: 0003_multi_source_collections
Create Date: 2026-07-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_v4_platform_features"
down_revision: Union[str, None] = "0003_multi_source_collections"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # --- Settings Center ----------------------------------------------------
    op.create_table(
        "bot_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column(
            "value_type",
            sa.Enum("string", "integer", "float", "boolean", "json", name="setting_value_type"),
            nullable=False,
            server_default="string",
        ),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bot_settings_key", "bot_settings", ["key"], unique=True)
    op.create_index("ix_bot_settings_category", "bot_settings", ["category"])

    # --- Media Collections ---------------------------------------------------
    op.create_table(
        "media_collections",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("icon", sa.String(length=32), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_collections_slug", "media_collections", ["slug"], unique=True)
    op.create_index("ix_media_collections_position", "media_collections", ["position"])

    with op.batch_alter_table("movies") as batch_op:
        batch_op.add_column(sa.Column("collection_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_movies_collection_id", "movies", ["collection_id"])

    # --- Blacklist / Whitelist Centers ---------------------------------------
    op.create_table(
        "blacklist_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "entry_type",
            sa.Enum(
                "telegram_id", "username", "phone", "media", "caption", "code", "word",
                "referral", "country", "spam_user", name="blacklist_entry_type",
            ),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_blacklist_entries_entry_type", "blacklist_entries", ["entry_type"])
    op.create_index("ix_blacklist_entries_value", "blacklist_entries", ["value"])

    op.create_table(
        "whitelist_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "entry_type",
            sa.Enum("user", "admin", "channel", "group", "role", name="whitelist_entry_type"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_whitelist_entries_entry_type", "whitelist_entries", ["entry_type"])
    op.create_index("ix_whitelist_entries_value", "whitelist_entries", ["value"])

    # --- Admin Login Protection -----------------------------------------------
    op.create_table(
        "admin_login_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_login_attempts_admin_telegram_id", "admin_login_attempts", ["admin_telegram_id"])

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("admin_telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("session_token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_sessions_admin_telegram_id", "admin_sessions", ["admin_telegram_id"])
    op.create_index("ix_admin_sessions_session_token", "admin_sessions", ["session_token"], unique=True)

    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.add_column(sa.Column("login_pin_hash", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("two_factor_secret", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("two_factor_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))

    # --- Log Center -------------------------------------------------------------
    op.create_table(
        "system_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "level",
            sa.Enum("debug", "info", "warning", "error", "critical", name="log_level"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum(
                "system", "security", "database", "media", "admin", "user", "scheduler", "backup",
                name="log_category",
            ),
            nullable=False,
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("module", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("exception", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_system_logs_level", "system_logs", ["level"])
    op.create_index("ix_system_logs_category", "system_logs", ["category"])
    op.create_index("ix_system_logs_user_id", "system_logs", ["user_id"])
    op.create_index("ix_system_logs_admin_id", "system_logs", ["admin_id"])

    # --- Automatic Backup metadata ----------------------------------------------
    op.create_table(
        "backup_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column(
            "integrity_status",
            sa.Enum("ok", "corrupted", "unknown", name="backup_integrity_status"),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("frequency", sa.Enum("daily", "weekly", "monthly", name="backup_frequency"), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_backup_records_filename", "backup_records", ["filename"], unique=True)

    # --- Advertisement Center -----------------------------------------------------
    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "content_type",
            sa.Enum("text", "photo", "video", "gif", name="ad_content_type"),
            nullable=False,
            server_default="text",
        ),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("file_id", sa.String(length=255), nullable=True),
        sa.Column("button_text", sa.String(length=64), nullable=True),
        sa.Column("button_url", sa.String(length=512), nullable=True),
        sa.Column("schedule_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schedule_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger_every_n_searches", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("impressions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ad_campaigns_priority", "ad_campaigns", ["priority"])

    # --- Premium / Referral history -------------------------------------------------
    op.create_table(
        "premium_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False),
        sa.Column("granted_by", sa.BigInteger(), nullable=True),
        sa.Column("plan", sa.String(length=64), nullable=False, server_default="premium"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_premium_history_user_id", "premium_history", ["user_id"])

    op.create_table(
        "referral_rewards",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False),
        sa.Column("reward_type", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_referral_rewards_user_id", "referral_rewards", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_referral_rewards_user_id", table_name="referral_rewards")
    op.drop_table("referral_rewards")

    op.drop_index("ix_premium_history_user_id", table_name="premium_history")
    op.drop_table("premium_history")

    op.drop_index("ix_ad_campaigns_priority", table_name="ad_campaigns")
    op.drop_table("ad_campaigns")

    op.drop_index("ix_backup_records_filename", table_name="backup_records")
    op.drop_table("backup_records")

    op.drop_index("ix_system_logs_admin_id", table_name="system_logs")
    op.drop_index("ix_system_logs_user_id", table_name="system_logs")
    op.drop_index("ix_system_logs_category", table_name="system_logs")
    op.drop_index("ix_system_logs_level", table_name="system_logs")
    op.drop_table("system_logs")

    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.drop_column("two_factor_enabled")
        batch_op.drop_column("two_factor_secret")
        batch_op.drop_column("login_pin_hash")

    op.drop_index("ix_admin_sessions_session_token", table_name="admin_sessions")
    op.drop_index("ix_admin_sessions_admin_telegram_id", table_name="admin_sessions")
    op.drop_table("admin_sessions")

    op.drop_index("ix_admin_login_attempts_admin_telegram_id", table_name="admin_login_attempts")
    op.drop_table("admin_login_attempts")

    op.drop_index("ix_whitelist_entries_value", table_name="whitelist_entries")
    op.drop_index("ix_whitelist_entries_entry_type", table_name="whitelist_entries")
    op.drop_table("whitelist_entries")

    op.drop_index("ix_blacklist_entries_value", table_name="blacklist_entries")
    op.drop_index("ix_blacklist_entries_entry_type", table_name="blacklist_entries")
    op.drop_table("blacklist_entries")

    op.drop_index("ix_movies_collection_id", table_name="movies")
    with op.batch_alter_table("movies") as batch_op:
        batch_op.drop_column("collection_id")

    op.drop_index("ix_media_collections_position", table_name="media_collections")
    op.drop_index("ix_media_collections_slug", table_name="media_collections")
    op.drop_table("media_collections")

    op.drop_index("ix_bot_settings_category", table_name="bot_settings")
    op.drop_index("ix_bot_settings_key", table_name="bot_settings")
    op.drop_table("bot_settings")
