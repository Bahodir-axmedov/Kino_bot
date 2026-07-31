"""Aiohttp application exposing Railway's health/readiness/liveness endpoints.

Also hosts the Telegram webhook receiver route when ``USE_WEBHOOK=true``.

- ``/health``    -- legacy combined check (kept for backward compatibility).
- ``/liveness``  -- "is the process itself alive" (no I/O). Railway should
  restart the container if this ever fails to respond.
- ``/readiness`` -- "is the process ready to serve traffic" (DB reachable +
  bot/dispatcher constructed). Railway should stop routing traffic (but not
  necessarily restart) if this fails.
"""

from __future__ import annotations

import time

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiohttp import web

from src.config import Settings
from src.database.engine import is_database_reachable
from src.utils import metrics

_PROCESS_STARTED_AT = time.monotonic()


async def handle_health(request: web.Request) -> web.Response:
    """Return 200 OK when the process and its database connection are healthy.

    Railway (and any external monitor) uses this to decide whether the
    deployment is alive; a non-200 response here should trigger a restart.
    """
    session_factory = request.app["session_factory"]
    healthy = await is_database_reachable(session_factory)
    if not healthy:
        return web.json_response({"status": "unhealthy", "database": "unreachable"}, status=503)
    return web.json_response({"status": "ok", "database": "reachable"}, status=200)


async def handle_liveness(request: web.Request) -> web.Response:
    """Return 200 as long as the event loop is responsive -- no I/O performed.

    This intentionally never touches the database: it answers "is this
    process wedged/deadlocked", not "is this process fully ready".
    """
    return web.json_response(
        {"status": "alive", "uptime_seconds": round(time.monotonic() - _PROCESS_STARTED_AT, 1)},
        status=200,
    )


async def handle_readiness(request: web.Request) -> web.Response:
    """Return 200 only once the database is reachable and the bot is wired up.

    Used to gate traffic during startup/deploys so Railway does not route
    requests to a container that has not finished initializing yet.
    """
    session_factory = request.app["session_factory"]
    db_ok = await is_database_reachable(session_factory)
    checks = {"database": db_ok, "bot": request.app.get("bot_ready", False)}
    ready = all(checks.values())
    status_code = 200 if ready else 503
    return web.json_response(
        {"status": "ready" if ready else "not_ready", "checks": checks, "metrics": metrics.snapshot()},
        status=status_code,
    )


def build_web_app(*, settings: Settings, bot: Bot, dispatcher: Dispatcher, session_factory) -> web.Application:
    """Build the aiohttp application used for health/readiness/liveness and webhooks."""
    app = web.Application()
    app["session_factory"] = session_factory
    app["bot_ready"] = True
    app.router.add_get("/health", handle_health)
    app.router.add_get("/readiness", handle_readiness)
    app.router.add_get("/liveness", handle_liveness)
    app.router.add_get("/", handle_health)

    if settings.use_webhook:
        async def handle_webhook(request: web.Request) -> web.Response:
            """Receive Telegram webhook updates, verifying the secret token header."""
            if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.webhook_secret:
                return web.Response(status=401)
            payload = await request.json()
            update = Update.model_validate(payload)
            await dispatcher.feed_update(bot, update)
            return web.Response(status=200)

        app.router.add_post("/webhook", handle_webhook)

    return app
