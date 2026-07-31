"""Discovered chats: zero-typing add flow for channels/groups.

Adds discovered_chats, populated automatically whenever the bot is added
to (or removed from) a Telegram channel/group via the my_chat_member
update. Lets the admin panel offer a tap-to-pick list for Force Subscribe
and Media Sources instead of requiring the admin to type a username or
chat id anywhere.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_discovered_chats"
down_revision: Union[str, None] = "0004_v4_platform_features"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discovered_chats",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("chat_username", sa.String(length=64), nullable=True),
        sa.Column(
            "chat_type",
            sa.Enum("channel", "group", name="discovered_chat_type"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("administrator", "member", "left", "kicked", name="discovered_chat_status"),
            nullable=False,
            server_default="member",
        ),
        sa.Column("added_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_discovered_chats_chat_id", "discovered_chats", ["chat_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_discovered_chats_chat_id", table_name="discovered_chats")
    op.drop_table("discovered_chats")
