"""Database backup and restore for the SQLite deployment mode.

For Postgres deployments (after the config-only migration mentioned in the
spec), operators should rely on the managed database provider's own backup
tooling instead; this service specifically targets the Railway-Volume+SQLite
setup described in the deployment requirements.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import structlog

from src.config import Settings
from src.utils.exceptions import BackupError

logger = structlog.get_logger(__name__)


class BackupService:
    """Creates and restores point-in-time copies of the SQLite database file."""

    def __init__(self, settings: Settings) -> None:
        """Bind this service to the application settings."""
        self._settings = settings

    def _database_file_path(self) -> Path:
        """Resolve the SQLite file path from ``DATABASE_URL``."""
        if not self._settings.is_sqlite:
            raise BackupError(
                "Backup/restore orqali fayl nusxalash faqat SQLite uchun ishlaydi. "
                "PostgreSQL uchun provayderning zaxira vositasidan foydalaning."
            )
        raw_path = self._settings.database_url.split(":///")[-1]
        return Path(raw_path)

    def create_backup(self) -> Path:
        """Copy the live database file into the backups directory with a timestamp."""
        source = self._database_file_path()
        if not source.exists():
            raise BackupError(f"Database fayli topilmadi: {source}")

        backup_dir = Path(self._settings.backup_path)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        destination = backup_dir / f"backup_{timestamp}.sqlite3"
        shutil.copy2(source, destination)
        logger.info("backup.created", path=str(destination))
        return destination

    def list_backups(self) -> list[Path]:
        """Return every available backup file, most recent first."""
        backup_dir = Path(self._settings.backup_path)
        if not backup_dir.exists():
            return []
        return sorted(backup_dir.glob("backup_*.sqlite3"), reverse=True)

    def restore_backup(self, backup_path: Path) -> None:
        """Restore the live database file from a previously created backup.

        The current live file is itself backed up first (suffixed
        ``.before_restore``) so a bad restore can always be undone.
        """
        if not backup_path.exists():
            raise BackupError(f"Backup fayli topilmadi: {backup_path}")

        target = self._database_file_path()
        if target.exists():
            shutil.copy2(target, target.with_suffix(target.suffix + ".before_restore"))
        shutil.copy2(backup_path, target)
        logger.info("backup.restored", path=str(backup_path))

    def export_database(self) -> Path:
        """Export the live database file for download (alias of ``create_backup``)."""
        return self.create_backup()

    def import_database(self, uploaded_file_path: Path) -> None:
        """Import an externally provided database file, replacing the live one."""
        self.restore_backup(uploaded_file_path)
