"""Persistence for Premium payment requests / the card-approval queue."""

from __future__ import annotations

from sqlalchemy import func, select

from src.models.payment_request import PaymentRequest, PaymentStatus
from src.repositories.base import BaseRepository


class PaymentRequestRepository(BaseRepository[PaymentRequest]):
    """Read/write helpers for :class:`PaymentRequest`."""

    model = PaymentRequest

    async def list_by_status(
        self, status: PaymentStatus, *, limit: int = 50
    ) -> list[PaymentRequest]:
        """Return payment requests in ``status``, most recent first."""
        result = await self._session.execute(
            select(PaymentRequest)
            .where(PaymentRequest.status == status)
            .order_by(PaymentRequest.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(self, status: PaymentStatus) -> int:
        """Return how many payment requests are currently in ``status``."""
        result = await self._session.execute(
            select(func.count())
            .select_from(PaymentRequest)
            .where(PaymentRequest.status == status)
        )
        return int(result.scalar_one())

    async def list_for_user(self, user_id: int, *, limit: int = 20) -> list[PaymentRequest]:
        """Return every payment request for ``user_id``, most recent first."""
        result = await self._session.execute(
            select(PaymentRequest)
            .where(PaymentRequest.user_id == user_id)
            .order_by(PaymentRequest.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
