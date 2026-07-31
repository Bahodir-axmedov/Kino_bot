"""Support message -- a user's message to the admin team and its reply.

Powers Admin Reply (#12): a user writes to support, an admin replies from
the admin panel.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class SupportMessage(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single support thread entry: the user's message and the admin's reply."""

    __tablename__ = "support_messages"

    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    admin_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    replied_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"SupportMessage(user_id={self.user_id!r}, status={self.status!r})"
