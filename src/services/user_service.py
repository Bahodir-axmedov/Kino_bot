"""End-user lifecycle: registration, activity tracking, moderation, premium."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.utils.exceptions import UserBannedError, UserMutedError


class UserService:
    """Encapsulates every business rule about end-users."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._repository = UserRepository(session)

    async def get_or_register(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        referred_by: int | None = None,
    ) -> tuple[User, bool]:
        """Return the existing user or create a new one. Second value is ``is_new``."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is not None:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            await self._repository.flush()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code or "uz",
            referred_by=referred_by if referred_by != telegram_id else None,
        )
        await self._repository.add(user)

        if user.referred_by is not None:
            referrer = await self._repository.get_by_telegram_id(user.referred_by)
            if referrer is not None:
                referrer.invite_count += 1
                await self._repository.flush()

        return user, True

    async def touch_activity(self, telegram_id: int) -> None:
        """Update a user's last-active timestamp to now."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is not None:
            user.last_active_at = datetime.now(timezone.utc)
            await self._repository.flush()

    async def assert_not_restricted(self, user: User) -> None:
        """Raise if the user is banned or muted; no-op otherwise."""
        if user.is_banned:
            raise UserBannedError(user.ban_reason or "Siz botdan foydalanishdan bloklangansiz.")
        if user.is_muted:
            raise UserMutedError("Sizning ovozingiz vaqtincha o'chirilgan.")

    async def increment_search_count(self, telegram_id: int) -> None:
        """Increment a user's search counter."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is not None:
            user.searches_count += 1
            await self._repository.flush()

    async def increment_movies_received(self, telegram_id: int) -> None:
        """Increment a user's received-movies counter."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is not None:
            user.movies_received_count += 1
            await self._repository.flush()

    async def find_by_identifier(self, identifier: str) -> User | None:
        """Find a single user by Telegram id or username fragment."""
        matches = await self._repository.search_by_username_or_id(identifier, limit=1)
        return matches[0] if matches else None

    async def search(self, identifier: str, limit: int = 20) -> list[User]:
        """Search users by Telegram id or partial username."""
        return list(await self._repository.search_by_username_or_id(identifier, limit=limit))

    async def ban(self, telegram_id: int, reason: str | None) -> User | None:
        """Ban a user, recording an optional reason."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_banned = True
        user.ban_reason = reason
        await self._repository.flush()
        return user

    async def unban(self, telegram_id: int) -> User | None:
        """Lift a ban from a user."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_banned = False
        user.ban_reason = None
        await self._repository.flush()
        return user

    async def set_muted(self, telegram_id: int, muted: bool) -> User | None:
        """Mute or unmute a user."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_muted = muted
        await self._repository.flush()
        return user

    async def grant_premium(self, telegram_id: int, days: int | None = None) -> User | None:
        """Grant premium status, optionally with an expiration in ``days``."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_premium = True
        user.premium_expires_at = (
            datetime.now(timezone.utc) + timedelta(days=days) if days else None
        )
        await self._repository.flush()
        return user

    async def revoke_premium(self, telegram_id: int) -> User | None:
        """Revoke premium status from a user."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_premium = False
        user.premium_expires_at = None
        await self._repository.flush()
        return user

    async def list_all_ids(self, *, exclude_banned: bool = True) -> list[int]:
        """Return the Telegram ids of every user, optionally excluding banned ones."""
        return list(await self._repository.list_all_ids(exclude_banned=exclude_banned))

    # --- Foydalanuvchi tarixi (user history) -------------------------------

    async def record_start(self, telegram_id: int) -> User | None:
        """Increment a user's /start press counter ("Necha marta start bosgan")."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is not None:
            user.start_count += 1
            await self._repository.flush()
        return user

    async def add_warning(self, telegram_id: int, note: str | None = None) -> User | None:
        """Add one warning to a user's history, optionally with a free-text note."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.warnings_count += 1
        if note:
            existing = f"{user.notes}\n" if user.notes else ""
            user.notes = f"{existing}[Warning] {note}"
        await self._repository.flush()
        return user

    async def adjust_spam_score(self, telegram_id: int, delta: int) -> User | None:
        """Raise or lower a user's spam-trust score (used by flood/spam protection)."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.spam_score = max(0, user.spam_score + delta)
        await self._repository.flush()
        return user

    async def set_notes(self, telegram_id: int, notes: str | None) -> User | None:
        """Set (overwrite) an admin's free-text notes about a user."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.notes = notes
        await self._repository.flush()
        return user

    async def set_admin_remarks(self, telegram_id: int, remarks: str | None) -> User | None:
        """Set (overwrite) an admin's private remarks about a user."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.admin_remarks = remarks
        await self._repository.flush()
        return user

    async def mark_verified(self, telegram_id: int) -> User | None:
        """Mark a user as verified (e.g. after passing a captcha/confirmation step)."""
        user = await self._repository.get_by_telegram_id(telegram_id)
        if user is None:
            return None
        user.is_verified = True
        await self._repository.flush()
        return user

    async def export_csv(self) -> str:
        """Return every user as CSV text (User Manager -> Export CSV)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "telegram_id", "username", "is_banned", "is_muted", "is_premium",
                "invite_count", "movies_received_count", "searches_count", "start_count",
                "warnings_count", "spam_score", "is_verified", "joined_at", "last_active_at",
            ]
        )
        ids = await self._repository.list_all_ids(exclude_banned=False)
        for telegram_id in ids:
            user = await self._repository.get_by_telegram_id(telegram_id)
            if user is None:
                continue
            writer.writerow(
                [
                    user.telegram_id, user.username or "", user.is_banned, user.is_muted,
                    user.is_premium, user.invite_count, user.movies_received_count,
                    user.searches_count, user.start_count, user.warnings_count,
                    user.spam_score, user.is_verified, user.joined_at, user.last_active_at or "",
                ]
            )
        return buffer.getvalue()
