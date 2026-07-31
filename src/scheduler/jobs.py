"""Background job definitions and scheduler bootstrap."""

from __future__ import annotations

from pathlib import Path

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import Settings
from src.services.backup_service import BackupService
from src.utils.exceptions import BackupError

logger = structlog.get_logger(__name__)

_MAX_BACKUPS_TO_KEEP = 14


def _run_daily_backup(settings: Settings) -> None:
    """Create a daily backup and prune old backups beyond the retention window.

    Errors are logged, not raised: a failed scheduled backup must never crash
    the whole process, since the bot should keep serving users regardless.
    """
    try:
        service = BackupService(settings)
        service.create_backup()
        backups = service.list_backups()
        for stale_backup in backups[_MAX_BACKUPS_TO_KEEP:]:
            stale_backup.unlink(missing_ok=True)
        logger.info("scheduler.backup_completed", kept=min(len(backups), _MAX_BACKUPS_TO_KEEP))
    except BackupError as error:
        logger.error("scheduler.backup_failed", error=str(error))


def _run_log_archival(settings: Settings) -> None:
    """Prune log files older than the retention window.

    ``TimedRotatingFileHandler`` (configured in ``utils/logger.py``) already
    performs daily rotation with its own ``backupCount``; this job is a
    second, explicit safety net driven purely by file age so behavior is not
    solely dependent on the handler having been continuously running.
    """
    import time

    logs_dir = Path(settings.logs_path)
    if not logs_dir.exists():
        return
    cutoff_seconds = time.time() - (_MAX_BACKUPS_TO_KEEP * 86400)
    for log_file in logs_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_seconds:
            log_file.unlink(missing_ok=True)
    logger.info("scheduler.log_archival_completed")


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    """Build (but do not start) the application's background job scheduler."""
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        _run_daily_backup,
        trigger=CronTrigger(hour=3, minute=0),
        args=[settings],
        id="daily_backup",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        _run_log_archival,
        trigger=CronTrigger(hour=3, minute=30),
        args=[settings],
        id="log_archival",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler
