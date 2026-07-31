"""Premium payment flow: create purchase requests and run the approval queue.

This service only manages the :class:`PaymentRequest` lifecycle (create,
list, approve, reject). Actually granting Premium days is the job of
:class:`~src.services.premium_service.PremiumService`; the handler layer
orchestrates the two so each service keeps a single responsibility.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.payment_request import PaymentMethod, PaymentRequest, PaymentStatus
from src.repositories.payment_request_repository import PaymentRequestRepository
from src.utils.exceptions import InvalidInputError


class PaymentService:
    """Creates and reviews Premium payment requests."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = PaymentRequestRepository(session)

    async def create_request(
        self,
        *,
        user_id: int,
        method: PaymentMethod,
        amount: int,
        currency: str,
        days: int,
        receipt_file_id: str | None = None,
        telegram_payment_charge_id: str | None = None,
        status: PaymentStatus = PaymentStatus.PENDING,
    ) -> PaymentRequest:
        """Persist a new payment request (pending for card, approved for stars)."""
        reviewed_at = datetime.now(timezone.utc) if status is not PaymentStatus.PENDING else None
        request = PaymentRequest(
            user_id=user_id,
            method=method,
            amount=amount,
            currency=currency,
            days=days,
            receipt_file_id=receipt_file_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            status=status,
            reviewed_at=reviewed_at,
        )
        return await self._repository.add(request)

    async def get(self, request_id: int) -> PaymentRequest | None:
        """Return a single payment request by id."""
        return await self._repository.get_by_id(request_id)

    async def list_pending(self, *, limit: int = 50) -> list[PaymentRequest]:
        """Return every card payment awaiting admin review."""
        return await self._repository.list_by_status(PaymentStatus.PENDING, limit=limit)

    async def pending_count(self) -> int:
        """Return the number of card payments awaiting admin review."""
        return await self._repository.count_by_status(PaymentStatus.PENDING)

    async def mark_reviewed(
        self, request_id: int, *, status: PaymentStatus, reviewed_by: int | None
    ) -> PaymentRequest:
        """Approve or reject a pending request; errors if already reviewed."""
        if status is PaymentStatus.PENDING:
            raise InvalidInputError("Ko'rib chiqilgan holat 'pending' bo'lishi mumkin emas.")
        request = await self._repository.get_by_id(request_id)
        if request is None:
            raise InvalidInputError("To'lov so'rovi topilmadi.")
        if request.status is not PaymentStatus.PENDING:
            raise InvalidInputError("Bu so'rov allaqachon ko'rib chiqilgan.")
        request.status = status
        request.reviewed_by = reviewed_by
        request.reviewed_at = datetime.now(timezone.utc)
        await self._repository.flush()
        return request
