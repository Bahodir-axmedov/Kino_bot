"""Aggregates every admin-facing router into a single admin router.

Routers are collected from the Plugin Architecture registry
(:mod:`src.core.plugin`) instead of a fixed list: every admin handler module
calls ``register_admin_plugin(router)`` at import time, and this module only
needs to import each module once (below) to trigger that registration.
Adding a brand-new admin feature module going forward only requires adding
one import line here -- ``build_admin_router`` itself never changes.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.core.plugin import admin_plugins
from src.filters.admin_filter import IsAdminFilter

# Imported for their registration side effects (each module calls
# register_admin_plugin(router) at import time). The `noqa` marker silences
# unused-import lint warnings for names that are intentionally never referenced.
from src.handlers.admin import (  # noqa: F401
    ad_center,
    admins,
    backup,
    blacklist_center,
    broadcast,
    chat_discovery,
    dashboard,
    database_manager,
    force_sub,
    log_center,
    media_center,
    media_collections,
    media_queue,
    media_sources,
    movie_management,
    premium_center,
    security_center,
    settings_center,
    stats,
    user_management,
    whitelist_center,
)
from src.keyboards.callback_data import AdminMenuCallback
from src.keyboards.inline.admin_panel import (
    build_admin_main_menu_keyboard,
    build_movies_menu_keyboard,
)
from src.services.admin_security_service import AdminSecurityService

root_router = Router(name="admin.root")
root_router.message.filter(IsAdminFilter())
root_router.callback_query.filter(IsAdminFilter())


@root_router.message(F.text == "/admin")
async def open_admin_panel(
    message: Message, state: FSMContext, admin_security_service: AdminSecurityService
) -> None:
    """Entry point for the admin panel: runs the Admin Login Protection gate first.

    If the admin has a PIN set, they must clear the PIN (and 2FA, if enabled)
    challenge from :mod:`src.handlers.admin.security_center` before the menu
    is shown. Admins without a PIN yet are let through immediately.
    """
    await security_center.start_login_gate(message, state, admin_security_service)


@root_router.callback_query(AdminMenuCallback.filter(F.section == "root"))
async def back_to_admin_root(callback: CallbackQuery) -> None:
    """Return to the top-level admin panel menu."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\U0001F6E0 <b>Admin panel</b>", reply_markup=build_admin_main_menu_keyboard()
        )
    await callback.answer()


@root_router.callback_query(AdminMenuCallback.filter(F.section == "movies"))
async def open_movies_menu(callback: CallbackQuery) -> None:
    """Show the movie-management submenu."""
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "\U0001F3AC <b>Kino boshqaruvi</b>", reply_markup=build_movies_menu_keyboard()
        )
    await callback.answer()


@root_router.callback_query(AdminMenuCallback.filter(F.section == "docs"))
async def open_docs_menu(callback: CallbackQuery) -> None:
    """Show a short pointer to the project's README/documentation."""
    text = (
        "\U0001F4C4 <b>Docs</b>\n\n"
        "To'liq texnik va foydalanuvchi hujjatlari loyihaning README.md faylida.\n"
        "Har bir servis va handler modulida ham docstringlar mavjud."
    )
    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=build_admin_main_menu_keyboard())
    await callback.answer()


def build_admin_router() -> Router:
    """Build and return the aggregated admin router (root menu + every registered plugin).

    IMPORTANT: aiogram filters bound via ``.filter()`` only apply to handlers
    registered directly on that exact ``Router`` object -- they do NOT cascade
    to routers attached with ``include_router``. ``root_router`` binds
    ``IsAdminFilter`` on itself above, but every plugin module creates its own
    separate ``Router`` instance, so each one needs the same gate applied here
    before it is included. Skipping this would let any Telegram user invoke
    admin-only handlers (ban/broadcast/database/security/etc.) just by
    guessing or replaying the right callback_data, with no admin check at all.
    """
    router = Router(name="admin")
    router.include_router(root_router)
    for plugin_router in admin_plugins():
        plugin_router.message.filter(IsAdminFilter())
        plugin_router.callback_query.filter(IsAdminFilter())
        router.include_router(plugin_router)
    return router
