"""Admin backup, restore, export, and import of the SQLite database."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard
from src.services.backup_service import BackupService
from src.services.log_service import LogService
from src.utils.exceptions import BackupError

router = Router(name="admin.backup")


@router.callback_query(AdminMenuCallback.filter(F.section == "backup"))
async def open_backup_menu(callback: CallbackQuery, backup_service: BackupService) -> None:
    """Create a fresh backup on demand and list previously created ones."""
    try:
        latest = backup_service.create_backup()
    except BackupError as error:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                f"❌ {error}", reply_markup=build_back_to_admin_menu_keyboard()
            )
        await callback.answer()
        return

    backups = backup_service.list_backups()
    lines = ["💾 <b>Backup / Restore</b>", "", f"✅ Yangi backup yaratildi: {latest.name}", ""]
    lines.append(f"Jami backuplar: {len(backups)}")
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=build_back_to_admin_menu_keyboard()
        )
        if callback.message.chat:
            await callback.message.answer_document(FSInputFile(str(latest)))
    await callback.answer()


@router.message(F.document, F.caption == "/restore")
async def restore_from_upload(
    message: Message, backup_service: BackupService, log_service: LogService
) -> None:
    """Restore the database from an uploaded backup file (caption ``/restore``).

    Requiring the exact caption prevents an admin from accidentally
    overwriting the live database with an unrelated file upload.
    """
    if message.document is None or message.bot is None:
        return

    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = Path(tmp_dir) / message.document.file_name
        await message.bot.download(message.document, destination=local_path)
        try:
            backup_service.restore_backup(local_path)
        except BackupError as error:
            await message.answer(f"❌ {error}")
            return

    await log_service.record(
        actor_id=message.from_user.id if message.from_user else 0,
        actor_role="admin",
        action="database_restored",
        entity_type="database",
    )
    await message.answer("✅ Baza muvaffaqiyatli tiklandi. Botni qayta ishga tushiring.")


register_admin_plugin(router)
