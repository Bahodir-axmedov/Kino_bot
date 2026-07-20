"""Search log -- records every search a user performs, found or not.

Powers Kino statistikasi (#9) and Empty Search analytics (#10): which codes
are searched most, and which searched codes are never found.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin


class SearchLog(Base, BigIntPrimaryKeyMixin):
    """A single search attempt: what was searched, by whom, and whether it hit."""

    __tablename__ = "search_logs"

    query_text: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    query_type: Mapped[str] = mapped_column(String(32), nullable=False, default="code")
    platform: Mapped[str] = mapped_column(String(32), nullable=False, default="bot", server_default="bot")
    found: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"SearchLog(query_text={self.query_text!r}, found={self.found!r})"
