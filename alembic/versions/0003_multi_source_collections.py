"""multi media source, media collection types, extended roles, search/support logs

Revision ID: 0003_multi_source_collections
Revises: 0002_extended_features
Create Date: 2026-07-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_multi_source_collections"
down_revision: Union[str, None] = "0002_extended_features"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # --- movies: Multi Media Source / Media Collection / auto-index (#1,#2,#3) --
    with op.batch_alter_table("movies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "collection_type",
                sa.Enum(
                    "movie",
                    "serial",
                    "anime",
                    "season",
                    "episode",
                    "part",
                    "trailer",
                    "short_video",
                    "clip",
                    name="movie_collection_type",
                ),
                nullable=False,
                server_default="movie",
            )
        )
        batch_op.add_column(sa.Column("series_title", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("season_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("episode_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("part_number", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("resolution", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("thumbnail_file_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("actor", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("director", sa.String(length=255), nullable=True))
    op.create_index("ix_movies_series_title", "movies", ["series_title"])
    op.create_index("ix_movies_actor", "movies", ["actor"])
    op.create_index("ix_movies_director", "movies", ["director"])

    # --- media_sources: named categories (#1) -------------------------------
    with op.batch_alter_table("media_sources") as batch_op:
        batch_op.add_column(sa.Column("category", sa.String(length=128), nullable=True))
    op.create_index("ix_media_sources_category", "media_sources", ["category"])

    # --- admin_users: extended roles (#18) ----------------------------------
    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.Enum("owner", "admin", "moderator", name="admin_role"),
            type_=sa.Enum(
                "owner",
                "admin",
                "moderator",
                "developer",
                "uploader",
                "support",
                "analyst",
                "backup_manager",
                "content_manager",
                name="admin_role",
            ),
            existing_nullable=False,
        )

    # --- action_logs: "Qayerda" context (#7) --------------------------------
    with op.batch_alter_table("action_logs") as batch_op:
        batch_op.add_column(sa.Column("context", sa.String(length=255), nullable=True))

    # --- new tables: search analytics (#9,#10) and support inbox (#12) -----
    op.create_table(
        "search_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("query_text", sa.String(length=255), nullable=False),
        sa.Column("query_type", sa.String(length=32), nullable=False, server_default="code"),
        sa.Column("found", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_search_logs_query_text", "search_logs", ["query_text"])
    op.create_index("ix_search_logs_found", "search_logs", ["found"])
    op.create_index("ix_search_logs_user_id", "search_logs", ["user_id"])
    op.create_index("ix_search_logs_created_at", "search_logs", ["created_at"])

    op.create_table(
        "support_messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("admin_reply", sa.Text(), nullable=True),
        sa.Column("replied_by", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_support_messages_user_id", "support_messages", ["user_id"])
    op.create_index("ix_support_messages_status", "support_messages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_support_messages_status", table_name="support_messages")
    op.drop_index("ix_support_messages_user_id", table_name="support_messages")
    op.drop_table("support_messages")

    op.drop_index("ix_search_logs_created_at", table_name="search_logs")
    op.drop_index("ix_search_logs_user_id", table_name="search_logs")
    op.drop_index("ix_search_logs_found", table_name="search_logs")
    op.drop_index("ix_search_logs_query_text", table_name="search_logs")
    op.drop_table("search_logs")

    with op.batch_alter_table("action_logs") as batch_op:
        batch_op.drop_column("context")

    with op.batch_alter_table("admin_users") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.Enum(
                "owner",
                "admin",
                "moderator",
                "developer",
                "uploader",
                "support",
                "analyst",
                "backup_manager",
                "content_manager",
                name="admin_role",
            ),
            type_=sa.Enum("owner", "admin", "moderator", name="admin_role"),
            existing_nullable=False,
        )

    op.drop_index("ix_media_sources_category", table_name="media_sources")
    with op.batch_alter_table("media_sources") as batch_op:
        batch_op.drop_column("category")

    op.drop_index("ix_movies_director", table_name="movies")
    op.drop_index("ix_movies_actor", table_name="movies")
    op.drop_index("ix_movies_series_title", table_name="movies")
    with op.batch_alter_table("movies") as batch_op:
        batch_op.drop_column("director")
        batch_op.drop_column("actor")
        batch_op.drop_column("thumbnail_file_id")
        batch_op.drop_column("resolution")
        batch_op.drop_column("file_size_bytes")
        batch_op.drop_column("part_number")
        batch_op.drop_column("episode_number")
        batch_op.drop_column("season_number")
        batch_op.drop_column("series_title")
        batch_op.drop_column("collection_type")
