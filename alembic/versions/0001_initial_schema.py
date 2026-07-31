"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column("phone_number", sa.String(length=32), nullable=True),
        sa.Column("language_code", sa.String(length=8), nullable=False, server_default="uz"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ban_reason", sa.String(length=255), nullable=True),
        sa.Column("is_muted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("premium_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
        sa.Column("invite_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("movies_received_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("searches_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["referred_by"], ["users.telegram_id"], ondelete="SET NULL"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Enum("owner", "admin", "moderator", name="admin_role"), nullable=False),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_users_telegram_id", "admin_users", ["telegram_id"], unique=True)

    op.create_table(
        "media_sources",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", sa.Enum("channel", "group", name="media_source_type"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_media_sources_chat_id", "media_sources", ["chat_id"], unique=True)

    op.create_table(
        "movies",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("telegram_file_id", sa.String(length=255), nullable=False),
        sa.Column(
            "media_type",
            sa.Enum("video", "document", "audio", "photo", "animation", name="media_type"),
            nullable=False,
        ),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("genre", sa.String(length=128), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("quality", sa.String(length=32), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("downloads_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_chat_id"], ["media_sources.chat_id"], ondelete="SET NULL"),
    )
    op.create_index("ix_movies_code", "movies", ["code"], unique=True)
    op.create_index("ix_movies_genre", "movies", ["genre"])
    op.create_index("ix_movies_language", "movies", ["language"])
    op.create_index("ix_movies_year", "movies", ["year"])

    op.create_table(
        "force_sub_channels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_username", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("invite_link", sa.String(length=255), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_force_sub_channels_chat_id", "force_sub_channels", ["chat_id"], unique=True)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("source_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("reply_markup_json", sa.Text(), nullable=True),
        sa.Column("total_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="broadcast_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "broadcast_failed_users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("broadcast_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retried", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["broadcast_id"], ["broadcasts.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_broadcast_failed_users_broadcast_id", "broadcast_failed_users", ["broadcast_id"])

    op.create_table(
        "action_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_action_logs_actor_id", "action_logs", ["actor_id"])
    op.create_index("ix_action_logs_action", "action_logs", ["action"])


def downgrade() -> None:
    op.drop_table("action_logs")
    op.drop_table("broadcast_failed_users")
    op.drop_table("broadcasts")
    op.drop_table("force_sub_channels")
    op.drop_table("movies")
    op.drop_table("media_sources")
    op.drop_table("admin_users")
    op.drop_table("users")
