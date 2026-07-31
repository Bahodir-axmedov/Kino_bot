"""Admin statistics dashboard."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.core.plugin import register_admin_plugin
from src.keyboards.callback_data import AdminMenuCallback
from src.keyboards.inline.admin_panel import build_back_to_admin_menu_keyboard
from src.services.stats_service import StatsService

router = Router(name="admin.stats")


@router.callback_query(AdminMenuCallback.filter(F.section == "stats"))
async def show_stats(callback: CallbackQuery, stats_service: StatsService) -> None:
    """Compute and render the statistics dashboard."""
    stats = await stats_service.build_dashboard()

    top_views = "\n".join(
        f"  • {movie.title} — {movie.views_count} 👁" for movie in stats.top_movies_by_views
    ) or "  —"
    top_downloads = "\n".join(
        f"  • {movie.title} — {movie.downloads_count} ⬇️"
        for movie in stats.top_movies_by_downloads
    ) or "  —"

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"🟢 Bugun qo'shilganlar: {stats.users_today}\n"
        f"⚪️ Kecha qo'shilganlar: {stats.users_yesterday}\n"
        f"📅 Shu hafta: {stats.users_this_week}\n"
        f"📆 Shu oy: {stats.users_this_month}\n"
        f"👥 Jami foydalanuvchilar: {stats.users_total}\n"
        f"🔥 Faol (7 kun): {stats.active_users_7d}\n"
        f"⭐️ Premium: {stats.premium_users}\n"
        f"🎬 Jami kinolar: {stats.movies_total}\n\n"
        f"🏆 <b>Top ko'rilgan kinolar:</b>\n{top_views}\n\n"
        f"🏆 <b>Top yuklab olingan kinolar:</b>\n{top_downloads}"
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=build_back_to_admin_menu_keyboard())
    await callback.answer()


register_admin_plugin(router)
