"""Premium System (V4.0): grant/extend/revoke premium and keep an audit trail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.premium_history import PremiumHistory
from src.models.user import User
from src.repositories.premium_history_repository import PremiumHistoryRepository
from src.repositories.user_repository import UserRepository
from src.utils.exceptions import InvalidInputError


class PremiumService:
    """Grants Premium/VIP status to users and records every change."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._history_repository = PremiumHistoryRepository(session)
        self._user_repository = UserRepository(session)

    async def grant(
        self, user_id: int, *, days: int, plan: str = "premium", granted_by: int | None = None
    ) -> PremiumHistory:
        """Grant or extend premium for ``user_id`` by ``days`` from now (or from current expiry)."""
        if days <= 0:
            raise InvalidInputError("Kunlar soni musbat bo'lishi kerak.")
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise InvalidInputError("Foydalanuvchi topilmadi.")
        now = datetime.now(timezone.utc)
        base = user.premium_expires_at if user.premium_expires_at and user.premium_expires_at > now else now
        new_expiry = base + timedelta(days=days)
        user.is_premium = True
        user.premium_expires_at = new_expiry
        history = PremiumHistory(user_id=user_id, granted_by=granted_by, plan=plan, started_at=now, expires_at=new_expiry)
        await self._history_repository.add(history)
        return history

    async def revoke(self, user_id: int) -> None:
        """Immediately revoke premium status from a user."""
        user = await self._user_repository.get_by_id(user_id)
        if user is None:
            raise InvalidInputError("Foydalanuvchi topilmadi.")
        user.is_premium = False
        user.premium_expires_at = None
        await self._user_repository.flush()

    async def history_for_user(self, user_id: int) -> list[PremiumHistory]:
        """Return every premium grant/extension event for a user."""
        return await self._history_repository.list_for_user(user_id)

    @staticmethod
    def is_active(user: User) -> bool:
        """Return True if the user currently has non-expired premium access."""
        if not user.is_premium:
            return False
        if user.premium_expires_at is None:
            return True
        return user.premium_expires_at > datetime.now(timezone.utc)
