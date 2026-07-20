"""Declarative base and reusable mixins shared by every ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models in the application."""


class TimestampMixin:
    """Adds ``created_at``/``updated_at`` columns managed by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BigIntPrimaryKeyMixin:
    """Adds an auto-incrementing primary key column named ``id``.

    On PostgreSQL this is a ``BIGINT`` identity column. On SQLite, however, a
    ``BIGINT PRIMARY KEY`` is *not* an alias for ``rowid`` and therefore does
    **not** auto-increment -- inserts without an explicit id fail with
    ``NOT NULL constraint failed``. Using ``with_variant`` makes SQLite emit a
    plain ``INTEGER PRIMARY KEY`` (which does auto-increment) while keeping the
    full 64-bit ``BIGINT`` in production Postgres.
    """

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
