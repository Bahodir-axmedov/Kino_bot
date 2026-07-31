"""Aiogram middlewares: cross-cutting concerns applied to every update."""

from src.middlewares.database_middleware import DatabaseMiddleware
from src.middlewares.duplicate_request_middleware import DuplicateRequestMiddleware
from src.middlewares.error_handling_middleware import ErrorHandlingMiddleware
from src.middlewares.throttling_middleware import ThrottlingMiddleware
from src.middlewares.user_activity_middleware import UserActivityMiddleware

# NOTE: there is no standalone ForceSubMiddleware. The mandatory-subscription
# gate is enforced directly inside the relevant handlers (see
# handlers/user/start.py and handlers/user/movie_code.py via
# ForceSubService.get_missing_channels), not through a dispatcher middleware.
# A previous refactor left a dangling import here for a file that was never
# created, which crashed the whole bot on startup (ModuleNotFoundError).

__all__ = [
    "DatabaseMiddleware",
    "DuplicateRequestMiddleware",
    "ErrorHandlingMiddleware",
    "ThrottlingMiddleware",
    "UserActivityMiddleware",
]
