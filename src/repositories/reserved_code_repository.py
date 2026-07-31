"""Data-access operations for short-lived movie-code reservations."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from src.models.reserved_code import ReservedCode
from src.repositories.base import BaseRepository


class ReservedCodeRepository(BaseRepository[ReservedCode]):
    """Repository encapsulating all SQL access for ``ReservedCode`` rows."""

    model = ReservedCode

    async def get_active_by_code(self, code: str) -> ReservedCode | None:
        """Return the active (non-released, non-expired) reservation for ``code``, if any."""
        statement = select(ReservedCode).where(
            ReservedCode.code == code, ReservedCode.released.is_(False)
        )
        result = await self._session.execute(statement)
        reservation = result.scalar_one_or_none()
        if reservation is None:
            return None
        if reservation.expires_at is not None and reservation.expires_at < datetime.now(timezone.utc):
            reservation.released = True
            await self.flush()
            return None
        return reservation

    async def release(self, code: str) -> bool:
        """Release an active reservation for ``code``. Returns ``False`` if none existed."""
        reservation = await self.get_active_by_code(code)
        if reservation is None:
            return False
        reservation.released = True
        await self.flush()
        return True
