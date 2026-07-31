"""Database Manager (V4.0): live SQLite health/optimization from the admin panel."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.config import Settings
from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback, DatabaseActionCallback
from src.keyboards.inline.admin_panel import build_database_manager_keyboard
from src.services.database_manager_service import DatabaseHealthSnapshot, DatabaseManagerService

router = Router(name="admin.database_manager")


def _format_snapshot(snapshot: DatabaseHealthSnapshot) -> str:
    """Render a health snapshot as admin-facing text."""
    integrity_icon = "✅" if snapshot.integrity_ok else "❌"
    lines = [
        "💽 <b>Database Manager</b>",
        "",
        f"🗂 Jadvallar: {snapshot.table_count}",
        f"🔍 Indekslar: {snapshot.index_count}",
        f"📊 Jami qatorlar: {snapshot.total_rows}",
        f"💾 Fayl hajmi: {snapshot.database_size_mb} MB",
        f"🧩 Fragmentatsiya: {snapshot.fragmentation_percent}%",
        f"{integrity_icon} Yaxlitlik tekshiruvi: {'OK' if snapshot.integrity_ok else 'Muammo aniqlandi'}",
    ]
    if snapshot.broken_indexes:
        lines.append(f"⚠️ Shubhali indekslar: {', '.join(snapshot.broken_indexes)}")
    if snapshot.slow_query_count:
        lines.append(f"🐢 Sekin so'rovlar: {snapshot.slow_query_count}")
    return "\n".join(lines)


@router.callback_query(AdminMenuCallback.filter(F.section == "database"))
async def open_database_manager(callback: CallbackQuery, session, settings: Settings) -> None:
    """Show the current database health snapshot."""
    service = DatabaseManagerService(session, settings)
    snapshot = await service.build_snapshot()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(_format_snapshot(snapshot), reply_markup=build_database_manager_keyboard())
    await callback.answer()


@router.callback_query(DatabaseActionCallback.filter(F.action == "refresh"))
async def refresh_database_manager(callback: CallbackQuery, session, settings: Settings) -> None:
    """Recompute and re-render the health snapshot."""
    await open_database_manager(callback, session, settings)


@router.callback_query(DatabaseActionCallback.filter(F.action == "vacuum"))
async def run_vacuum(callback: CallbackQuery, session, settings: Settings) -> None:
    """Run VACUUM and re-render the snapshot."""
    service = DatabaseManagerService(session, settings)
    await service.vacuum()
    snapshot = await service.build_snapshot()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(_format_snapshot(snapshot), reply_markup=build_database_manager_keyboard())
    await callback.answer("✅ VACUUM bajarildi")


@router.callback_query(DatabaseActionCallback.filter(F.action == "analyze"))
async def run_analyze(callback: CallbackQuery, session, settings: Settings) -> None:
    """Run ANALYZE and re-render the snapshot."""
    service = DatabaseManagerService(session, settings)
    await service.analyze()
    snapshot = await service.build_snapshot()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(_format_snapshot(snapshot), reply_markup=build_database_manager_keyboard())
    await callback.answer("✅ ANALYZE bajarildi")


@router.callback_query(DatabaseActionCallback.filter(F.action == "reindex"))
async def run_reindex(callback: CallbackQuery, session, settings: Settings) -> None:
    """Run REINDEX and re-render the snapshot."""
    service = DatabaseManagerService(session, settings)
    await service.reindex()
    snapshot = await service.build_snapshot()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(_format_snapshot(snapshot), reply_markup=build_database_manager_keyboard())
    await callback.answer("✅ REINDEX bajarildi")


@router.callback_query(DatabaseActionCallback.filter(F.action == "optimize"))
async def run_optimize(callback: CallbackQuery, session, settings: Settings) -> None:
    """Run the full VACUUM -> ANALYZE -> REINDEX pipeline and re-render the snapshot."""
    service = DatabaseManagerService(session, settings)
    snapshot = await service.optimize()
    if isinstance(callback.message, Message):
        await callback.message.edit_text(_format_snapshot(snapshot), reply_markup=build_database_manager_keyboard())
    await callback.answer("⚡ To'liq optimizatsiya bajarildi")


register_admin_plugin(router)
