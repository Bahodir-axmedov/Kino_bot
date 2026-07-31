"""Short-lived movie-code reservations used by the code-management tools.

Reserving a code lets an admin "lock" it (e.g. while preparing a Media Queue
upload) so a second admin cannot simultaneously create a different movie
under the same code -- without requiring the movie row to exist yet.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class ReservedCode(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A movie code that is temporarily held by an admin before use."""

    __tablename__ = "reserved_codes"

    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    reserved_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"ReservedCode(code={self.code!r}, reserved_by={self.reserved_by!r})"
