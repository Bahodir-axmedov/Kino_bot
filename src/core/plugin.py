"""Plugin Architecture (V4.0): self-registering handler routers.

Every handler module (admin or user) calls ``register_admin_plugin(router)``
or ``register_user_plugin(router)`` once, at import time, instead of being
hardcoded into a fixed list inside ``build_admin_router``/``build_user_router``.
This makes the handler set genuinely extensible: adding a new feature module
only requires dropping a new file in ``handlers/admin`` or ``handlers/user``
and importing it once from that package's ``__init__.py`` -- no other file
needs to change.
"""

from __future__ import annotations

from aiogram import Router

_admin_plugins: list[Router] = []
_user_plugins: list[Router] = []


def register_admin_plugin(router: Router) -> Router:
    """Register an admin-facing router with the plugin registry. Returns it unchanged."""
    if router not in _admin_plugins:
        _admin_plugins.append(router)
    return router


def register_user_plugin(router: Router) -> Router:
    """Register a user-facing router with the plugin registry. Returns it unchanged."""
    if router not in _user_plugins:
        _user_plugins.append(router)
    return router


def admin_plugins() -> list[Router]:
    """Return every admin router registered so far, in registration order."""
    return list(_admin_plugins)


def user_plugins() -> list[Router]:
    """Return every user router registered so far, in registration order."""
    return list(_user_plugins)
