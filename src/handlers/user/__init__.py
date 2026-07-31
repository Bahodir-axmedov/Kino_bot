"""User-facing feature routers."""

from aiogram import Router

from src.handlers.user.help import router as help_router
from src.handlers.user.movie_code import router as movie_code_router
from src.handlers.user.premium import router as premium_router
from src.handlers.user.referral import router as referral_router
from src.handlers.user.search import router as search_router
from src.handlers.user.start import router as start_router


def build_user_router() -> Router:
    """Build and return the aggregate user-facing router.

    ``referral_router`` (which serves both the "\U0001F91D Referral" and
    "\u2B50\uFE0F Premium" main-menu buttons) is included *before*
    ``movie_code_router`` so its exact-text handlers always win over the
    movie-code catch-all, and must be present at all -- omitting it left both
    buttons with no handler, so tapping them produced no response.
    """
    router = Router(name="user")
    router.include_router(start_router)
    router.include_router(help_router)
    router.include_router(search_router)
    router.include_router(referral_router)
    router.include_router(premium_router)
    router.include_router(movie_code_router)
    return router
