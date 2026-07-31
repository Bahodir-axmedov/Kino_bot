"""Log Center (V4.0): structured, queryable log entries for the admin panel."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, LogFilterCallback
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard, build_log_filter_keyboard
from src.models.system_log import LogLevel
from src.services.system_log_service import SystemLogService

router = Router(name="admin.log_center")

_LEVEL_ICON = {
    LogLevel.DEBUG: "⚪️",
    LogLevel.INFO: "🟢",
    LogLevel.WARNING: "🟡",
    LogLevel.ERROR: "🔴",
    LogLevel.CRITICAL: "⛔",
}


async def _render(level: str | None, system_log_service: SystemLogService) -> str:
    """Build the Log Center text listing for the chosen level filter."""
    filter_level = LogLevel(level) if level and level != "all" else None
    entries = await system_log_service.list_filtered(level=filter_level, limit=25)
    lines = ["🗄 <b>Log markazi</b>", ""]
    if not entries:
        lines.append("Yozuvlar topilmadi.")
    for entry in entries:
        icon = _LEVEL_ICON.get(entry.level, "⚪️")
        lines.append(f"{icon} <code>{entry.created_at:%Y-%m-%d %H:%M}</code> [{entry.category.value}] {entry.action}")
        lines.append(f"   {entry.description[:120]}")
    return "\n".join(lines)


@router.callback_query(AdminMenuCallback.filter(F.section == "logs"))
async def open_log_center(callback: CallbackQuery, system_log_service: SystemLogService) -> None:
    """Show the Log Center with no level filter applied."""
    text = await _render(None, system_log_service)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=build_log_filter_keyboard())
    await callback.answer()


@router.callback_query(LogFilterCallback.filter())
async def filter_log_center(
    callback: CallbackQuery, callback_data: LogFilterCallback, system_log_service: SystemLogService
) -> None:
    """Re-render the Log Center filtered by the chosen level."""
    text = await _render(callback_data.level, system_log_service)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=build_log_filter_keyboard())
    await callback.answer()


register_admin_plugin(router)
