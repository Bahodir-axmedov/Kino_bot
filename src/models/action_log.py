"""Immutable audit trail of every meaningful action taken in the bot."""

from __future__ import annotations

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ActionLog(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single audit entry: who did what, to what, and what changed."""

    __tablename__ = "action_logs"

    actor_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Admin Activity (#7): "Qayerda" -- the surface an action happened on
    # (e.g. chat id, panel section name). Best-effort: Telegram Bot API does
    # not expose true device/IP, so this only records in-app context.
    context: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ActionLog(actor_id={self.actor_id!r}, action={self.action!r})"
