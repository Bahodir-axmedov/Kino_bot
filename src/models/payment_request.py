"""Premium payment requests.

Every attempt to buy Premium is recorded here so the admin has a full audit
trail and an approval queue:

* **Stars** payments (Telegram XTR) are confirmed by Telegram itself, so they
  are stored already ``APPROVED`` -- there is nothing for the admin to do.
* **Card** payments (Uzcard / Humo) are manual: the user transfers money to
  the admin's card and uploads a receipt screenshot. The row starts as
  ``PENDING`` and an admin approves or rejects it from the admin panel.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base, BigIntPrimaryKeyMixin, TimestampMixin


class PaymentMethod(str, enum.Enum):
    """How the user paid (or attempted to pay) for Premium."""

    STARS = "stars"
    CARD = "card"


class PaymentStatus(str, enum.Enum):
    """Lifecycle of a single payment request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentRequest(TimestampMixin, BigIntPrimaryKeyMixin, Base):
    """A single Premium purchase attempt (Stars auto-approved, card manual)."""

    __tablename__ = "payment_requests"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True
    )
    method: Mapped[PaymentMethod] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS")
    days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    receipt_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper only
        return (
            f"PaymentRequest(id={self.id!r}, user_id={self.user_id!r}, "
            f"method={self.method!r}, status={self.status!r})"
        )
