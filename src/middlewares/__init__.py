"""Aiogram middlewares: cross-cutting concerns applied to every update."""

from src.middlewares.database_middleware import DatabaseMiddleware
from src.middlewares.duplicate_request_middleware import DuplicateRequestMiddleware
from src.middlewares.error_handling_middleware import ErrorHandlingMiddleware
from src.middlewares.throttling_middleware import ThrottlingMiddleware
from src.middlewares.user_activity_middleware import UserActivityMiddleware

__all__ = [
    "DatabaseMiddleware",
    "DuplicateRequestMiddleware",
    "ErrorHandlingMiddleware",
    "ThrottlingMiddleware",
    "UserActivityMiddleware",
]
