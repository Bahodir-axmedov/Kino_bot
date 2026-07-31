"""Aggregates every feature router into a single top-level router."""

from aiogram import Router

from src.handlers.admin import build_admin_router
from src.handlers.user import build_user_router


def build_root_router() -> Router:
    """Build and return the root router with all feature routers included.

    Admin routers are included first so admin-only commands are not
    shadowed by looser user-facing text filters (e.g. the movie-code
    catch-all).
    """
    router = Router(name="root")
    router.include_router(build_admin_router())
    router.include_router(build_user_router())
    return router
