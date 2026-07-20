"""Admin Login Protection (V4.0): lockout, sessions, and optional TOTP 2FA.

Telegram already authenticates *which* Telegram account is talking. This
service adds a second, revocable layer specifically for the admin panel: a
hashed PIN (and optional TOTP 2FA) an admin must confirm before the panel
unlocks, brute-force lockout after repeated failures, and sessions that can
be listed and force-logged-out.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin import AdminUser
from src.models.admin_session import AdminLoginAttempt, AdminSession
from src.repositories.admin_repository import AdminRepository
from src.repositories.admin_session_repository import AdminLoginAttemptRepository, AdminSessionRepository
from src.services.settings_service import SettingsService
from src.utils.exceptions import AdminLockedOutError, InvalidTwoFactorCodeError, PermissionDeniedError
from src.utils.totp import generate_secret, provisioning_uri, verify_code
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdminSecurityStatus:
    """Everything the Security Center / login gate need about one admin."""

    pin_set: bool
    two_factor_enabled: bool
    active_sessions_count: int


def _hash_pin(pin: str) -> str:
    """Hash a PIN with a per-call random salt using PBKDF2-HMAC-SHA256 (stdlib only)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()
    return f"{salt}${digest}"


def _verify_pin(pin: str, stored: str) -> bool:
    """Verify a PIN against a ``salt$digest`` hash produced by :func:`_hash_pin`."""
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()
    return secrets.compare_digest(candidate, digest)


class AdminSecurityService:
    """Admin panel login protection: PIN/2FA verification, lockout, sessions."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind this service to a unit-of-work session."""
        self._session = session
        self._admin_repository = AdminRepository(session)
        self._attempt_repository = AdminLoginAttemptRepository(session)
        self._session_repository = AdminSessionRepository(session)
        self._settings = SettingsService(session)

    async def get_status(self, admin_telegram_id: int) -> AdminSecurityStatus:
        """Return the current PIN/2FA/session status for one admin (Security Center)."""
        admin = await self._admin_repository.get_by_telegram_id(admin_telegram_id)
        sessions = await self._session_repository.list_active(admin_telegram_id)
        return AdminSecurityStatus(
            pin_set=bool(admin and admin.login_pin_hash),
            two_factor_enabled=bool(admin and admin.two_factor_enabled),
            active_sessions_count=len(sessions),
        )

    async def set_pin(self, admin_telegram_id: int, pin: str) -> AdminUser:
        """Set (or replace) an admin's panel-login PIN."""
        admin = await self._admin_repository.get_by_telegram_id(admin_telegram_id)
        if admin is None:
            raise PermissionDeniedError("Admin topilmadi.")
        admin.login_pin_hash = _hash_pin(pin)
        await self._admin_repository.flush()
        return admin

    async def enable_two_factor(self, admin_telegram_id: int) -> str:
        """Generate and store a new TOTP secret for an admin; returns the provisioning URI."""
        admin = await self._admin_repository.get_by_telegram_id(admin_telegram_id)
        if admin is None:
            raise PermissionDeniedError("Admin topilmadi.")
        secret = generate_secret()
        admin.two_factor_secret = secret
        admin.two_factor_enabled = True
        await self._admin_repository.flush()
        return provisioning_uri(secret, account_name=str(admin_telegram_id))

    async def disable_two_factor(self, admin_telegram_id: int) -> None:
        """Turn off 2FA for an admin."""
        admin = await self._admin_repository.get_by_telegram_id(admin_telegram_id)
        if admin is None:
            raise PermissionDeniedError("Admin topilmadi.")
        admin.two_factor_enabled = False
        admin.two_factor_secret = None
        await self._admin_repository.flush()

    async def _is_locked_out(self, admin_telegram_id: int) -> bool:
        """Check whether the recent-failure count exceeds the configured threshold."""
        max_attempts = int(await self._settings.get("admin_login_max_attempts"))
        lockout_minutes = int(await self._settings.get("admin_login_lockout_minutes"))
        since = datetime.now(timezone.utc) - timedelta(minutes=lockout_minutes)
        failed_count = await self._attempt_repository.recent_failed_count(admin_telegram_id, since)
        return failed_count >= max_attempts

    async def verify_login(
        self, admin_telegram_id: int, *, pin: str, two_factor_code: str | None = None
    ) -> AdminSession:
        """Verify PIN (+2FA if enabled) and issue a new session, enforcing lockout.

        Raises ``AdminLockedOutError`` if the admin is currently locked out,
        ``InvalidTwoFactorCodeError``/``PermissionDeniedError`` on bad credentials.
        """
        if await self._is_locked_out(admin_telegram_id):
            lockout_minutes = int(await self._settings.get("admin_login_lockout_minutes"))
            raise AdminLockedOutError(
                f"Juda ko'p noto'g'ri urinish. {lockout_minutes} daqiqadan so'ng qayta urinib ko'ring."
            )

        admin = await self._admin_repository.get_by_telegram_id(admin_telegram_id)
        pin_ok = admin is not None and admin.login_pin_hash is not None and _verify_pin(pin, admin.login_pin_hash)
        two_factor_ok = True
        if pin_ok and admin is not None and admin.two_factor_enabled:
            two_factor_ok = bool(
                two_factor_code and admin.two_factor_secret and verify_code(admin.two_factor_secret, two_factor_code)
            )

        success = bool(pin_ok and two_factor_ok)
        await self._attempt_repository.add(AdminLoginAttempt(admin_telegram_id=admin_telegram_id, success=success))

        if not pin_ok:
            raise PermissionDeniedError("PIN noto'g'ri.")
        if not two_factor_ok:
            raise InvalidTwoFactorCodeError("2FA kodi noto'g'ri.")

        timeout_minutes = int(await self._settings.get("admin_session_timeout_minutes"))
        now = datetime.now(timezone.utc)
        new_session = AdminSession(
            admin_telegram_id=admin_telegram_id,
            session_token=secrets.token_urlsafe(32),
            expires_at=now + timedelta(minutes=timeout_minutes),
            last_seen_at=now,
        )
        return await self._session_repository.add(new_session)

    async def touch_session(self, session_token: str) -> AdminSession | None:
        """Validate a session token and refresh its ``last_seen_at``/expiry ("Session Validation").

        Returns ``None`` if the token is unknown, revoked, or expired.
        """
        session_row = await self._session_repository.get_by_token(session_token)
        if session_row is None or not session_row.is_active:
            return None
        now = datetime.now(timezone.utc)
        if session_row.expires_at <= now:
            return None
        timeout_minutes = int(await self._settings.get("admin_session_timeout_minutes"))
        session_row.last_seen_at = now
        session_row.expires_at = now + timedelta(minutes=timeout_minutes)
        await self._session_repository.flush()
        return session_row

    async def list_active_sessions(self, admin_telegram_id: int) -> list[AdminSession]:
        """Return every active (non-revoked, non-expired) session for an admin."""
        return await self._session_repository.list_active(admin_telegram_id)

    async def logout_all(self, admin_telegram_id: int) -> int:
        """Revoke every active session for an admin. Returns the number revoked."""
        return await self._session_repository.revoke_all(admin_telegram_id)
