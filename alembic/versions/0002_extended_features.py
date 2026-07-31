"""extended features: force-sub center, media visibility/health, user history, code reservations

Revision ID: 0002_extended_features
Revises: 0001_initial_schema
Create Date: 2026-07-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_extended_features"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # --- movies: visibility rules + broken-file tracking -------------------
    with op.batch_alter_table("movies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "visibility",
                sa.Enum(
                    "public",
                    "hidden",
                    "vip",
                    "premium",
                    "admin_only",
                    "subscriber_only",
                    "referral_only",
                    name="movie_visibility",
                ),
                nullable=False,
                server_default="public",
            )
        )
        batch_op.add_column(
            sa.Column("is_broken", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("source_message_id", sa.BigInteger(), nullable=True))

    # --- users: full history / trust-signal columns -------------------------
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("start_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("spam_score", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("warnings_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("admin_remarks", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("last_known_client_hint", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_index("ix_users_spam_score", "users", ["spam_score"])

    # --- force_sub_channels: professional multi-platform center ------------
    with op.batch_alter_table("force_sub_channels") as batch_op:
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.Enum(
                    "telegram_channel",
                    "telegram_group",
                    "telegram_discussion_group",
                    "telegram_bot",
                    "instagram",
                    "youtube",
                    "tiktok",
                    "facebook",
                    "twitter_x",
                    "website",
                    name="force_sub_platform",
                ),
                nullable=False,
                server_default="telegram_channel",
            )
        )
        batch_op.add_column(sa.Column("url", sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column("instructions", sa.String(length=512), nullable=True))
        batch_op.add_column(
            sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.alter_column("chat_id", existing_type=sa.BigInteger(), nullable=True)

    # --- new tables ----------------------------------------------------------
    op.create_table(
        "force_sub_confirmations",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.telegram_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["channel_id"], ["force_sub_channels.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_force_sub_confirmation_user_channel"),
    )
    op.create_index("ix_force_sub_confirmations_user_id", "force_sub_confirmations", ["user_id"])
    op.create_index("ix_force_sub_confirmations_channel_id", "force_sub_confirmations", ["channel_id"])

    op.create_table(
        "reserved_codes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("reserved_by", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reserved_codes_code", "reserved_codes", ["code"], unique=True)


def downgrade() -> None:
    op.drop_table("reserved_codes")
    op.drop_index("ix_force_sub_confirmations_channel_id", table_name="force_sub_confirmations")
    op.drop_index("ix_force_sub_confirmations_user_id", table_name="force_sub_confirmations")
    op.drop_table("force_sub_confirmations")

    with op.batch_alter_table("force_sub_channels") as batch_op:
        batch_op.alter_column("chat_id", existing_type=sa.BigInteger(), nullable=False)
        batch_op.drop_column("is_mandatory")
        batch_op.drop_column("instructions")
        batch_op.drop_column("url")
        batch_op.drop_column("platform")

    op.drop_index("ix_users_spam_score", table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_verified")
        batch_op.drop_column("last_known_client_hint")
        batch_op.drop_column("admin_remarks")
        batch_op.drop_column("notes")
        batch_op.drop_column("warnings_count")
        batch_op.drop_column("spam_score")
        batch_op.drop_column("start_count")

    with op.batch_alter_table("movies") as batch_op:
        batch_op.drop_column("source_message_id")
        batch_op.drop_column("last_verified_at")
        batch_op.drop_column("is_broken")
        batch_op.drop_column("visibility")
