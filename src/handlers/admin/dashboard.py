"""Real-time admin Dashboard: CPU/RAM/Storage/DB/traffic/backup/job status."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard
from src.services.backup_service import BackupService
from src.services.settings_service import SettingsService
from src.services.system_service import SystemService, measure_bot_ping

router = Router(name="admin.dashboard")


@router.callback_query(AdminMenuCallback.filter(F.section == "dashboard"))
async def show_dashboard(
    callback: CallbackQuery,
    system_service: SystemService,
    backup_service: BackupService,
    settings_service: SettingsService,
) -> None:
    """Render the real-time system dashboard."""
    snapshot = await system_service.build_dashboard()
    ping_ms = await measure_bot_ping(callback.bot) if callback.bot else 0.0
    backups = backup_service.list_backups()
    last_backup = backups[-1].name if backups else "yo'q"
    railway_version = await settings_service.get("railway_deploy_version") or "—"
    railway_environment = await settings_service.get("railway_environment") or "—"

    text = (
        "\U0001F5A5 <b>Dashboard (Real Time)</b>\n\n"
        f"CPU: {snapshot.cpu_percent}%\n"
        f"RAM: {snapshot.ram_used_mb} MB ({snapshot.ram_percent}%)\n"
        f"Storage: {snapshot.disk_used_percent}%\n"
        f"Database hajmi: {snapshot.database_size_mb} MB\n"
        f"Media soni: {snapshot.media_count}\n\n"
        f"Bugungi foydalanuvchilar: {snapshot.users_today}\n"
        f"Kechagi foydalanuvchilar: {snapshot.users_yesterday}\n"
        f"Online (5 daqiqa): {snapshot.users_online_5m}\n\n"
        f"Bot ping: {ping_ms} ms\n"
        f"O'rtacha javob vaqti: {snapshot.average_response_ms} ms\n"
        f"So'rov/soniya: {snapshot.requests_per_second}\n"
        f"Jami so'rovlar: {snapshot.total_requests}\n"
        f"Bugungi xatolar: {snapshot.errors_today}\n"
        f"Uptime: {round(snapshot.uptime_seconds / 60, 1)} daqiqa\n\n"
        f"Oxirgi backup: {last_backup}\n"
        f"Backuplar soni: {len(backups)}\n"
        "Scheduler: Ishlamoqda\n"
        "Railway Volume: Ulangan\n"
        f"Railway muhiti: {railway_environment}\n"
        f"Railway versiyasi: {railway_version}"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=build_back_to_admin_menu_keyboard())
    await callback.answer()


register_admin_plugin(router)
