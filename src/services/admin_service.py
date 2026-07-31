"""Administrator management and role-based access control (RBAC)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models.admin import AdminRole, AdminUser
from src.repositories.admin_repository import AdminRepository
from src.utils.exceptions import PermissionDeniedError

_ROLE_RANK: dict[AdminRole, int] = {
    AdminRole.SUPPORT: 1,
    AdminRole.ANALYST: 1,
    AdminRole.UPLOADER: 1,
    AdminRole.CONTENT_MANAGER: 1,
    AdminRole.BACKUP_MANAGER: 1,
    AdminRole.MODERATOR: 1,
    AdminRole.DEVELOPER: 2,
    AdminRole.ADMIN: 2,
    AdminRole.OWNER: 3,
}

# Admin Rollari (#18): named role groups used for feature-specific gating
# (e.g. only Content Manager/Uploader/Admin/Owner may edit the catalogue).
CONTENT_ROLES = frozenset({AdminRole.CONTENT_MANAGER, AdminRole.UPLOADER, AdminRole.ADMIN, AdminRole.OWNER})
SUPPORT_ROLES = frozenset({AdminRole.SUPPORT, AdminRole.ADMIN, AdminRole.OWNER})
ANALYST_ROLES = frozenset({AdminRole.ANALYST, AdminRole.ADMIN, AdminRole.OWNER})
BACKUP_ROLES = frozenset({AdminRole.BACKUP_MANAGER, AdminRole.ADMIN, AdminRole.OWNER})


class AdminService:
    """Encapsulates every rule about who is an admin and what they may do."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        """Bind this service to a unit-of-work session and app settings."""
        self._session = session
        self._settings = settings
        self._repository = AdminRepository(session)

    async def get_role(self, telegram_id: int) -> AdminRole | None:
        """Return the effective role of ``telegram_id``, or ``None`` if not an admin.

        The statically configured owner (``OWNER_ID``) always resolves to
        ``AdminRole.OWNER`` even before any DB row exists for them, so the
        very first boot always has a working super-admin.
        """
        if telegram_id == self._settings.owner_id:
            return AdminRole.OWNER
        record = await self._repository.get_by_telegram_id(telegram_id)
        if record is not None and record.is_active:
            return record.role
        if telegram_id in self._settings.admin_ids:
            return AdminRole.ADMIN
        return None

    async def is_admin(self, telegram_id: int) -> bool:
        """Return ``True`` when ``telegram_id`` has any active admin role."""
        return await self.get_role(telegram_id) is not None

    async def require_role(self, telegram_id: int, minimum_role: AdminRole) -> AdminRole:
        """Return the actor's role, raising if it is below ``minimum_role``."""
        role = await self.get_role(telegram_id)
        if role is None or _ROLE_RANK[role] < _ROLE_RANK[minimum_role]:
            raise PermissionDeniedError(
                f"Bu amal uchun kamida '{minimum_role.value}' darajasi kerak."
            )
        return role

    async def add_admin(
        self, *, telegram_id: int, role: AdminRole, added_by: int
    ) -> AdminUser:
        """Add (or reactivate) an administrator with the given role."""
        existing = await self._repository.get_by_telegram_id(telegram_id)
        if existing is not None:
            existing.role = role
            existing.is_active = True
            existing.added_by = added_by
            await self._repository.flush()
            return existing
        admin = AdminUser(telegram_id=telegram_id, role=role, added_by=added_by, is_active=True)
        return await self._repository.add(admin)

    async def remove_admin(self, telegram_id: int) -> bool:
        """Deactivate an administrator. Returns ``False`` if not found."""
        existing = await self._repository.get_by_telegram_id(telegram_id)
        if existing is None:
            return False
        existing.is_active = False
        await self._repository.flush()
        return True

    async def list_admins(self) -> list[AdminUser]:
        """Return every active administrator stored in the database."""
        return list(await self._repository.list_active())

    async def has_any_role(self, telegram_id: int, allowed: frozenset[AdminRole]) -> bool:
        """Return ``True`` if the actor's role is in ``allowed``. Owner/Admin always pass."""
        role = await self.get_role(telegram_id)
        if role is None:
            return False
        if role in (AdminRole.OWNER, AdminRole.ADMIN):
            return True
        return role in allowed
