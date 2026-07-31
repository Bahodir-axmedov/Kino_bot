"""Broadcast campaigns and their per-user delivery failures."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class BroadcastStatus(str, enum.Enum):
    """Lifecycle state of a broadcast campaign."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Broadcast(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single broadcast/advertisement campaign sent by an admin."""

    __tablename__ = "broadcasts"

    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_markup_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_users: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[BroadcastStatus] = mapped_column(
        SAEnum(BroadcastStatus, name="broadcast_status"),
        nullable=False,
        default=BroadcastStatus.PENDING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    failed_users: Mapped[list["BroadcastFailedUser"]] = relationship(
        "BroadcastFailedUser", back_populates="broadcast", cascade="all, delete-orphan"
    )


class BroadcastFailedUser(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A user for whom a broadcast delivery failed, with the error captured."""

    __tablename__ = "broadcast_failed_users"

    broadcast_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("broadcasts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retried: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)

    broadcast: Mapped["Broadcast"] = relationship("Broadcast", back_populates="failed_users")
