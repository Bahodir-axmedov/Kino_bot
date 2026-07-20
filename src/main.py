"""Application entrypoint: bootstraps the bot, web app, and scheduler.

Run with: ``python -m src.main``
"""

from __future__ import annotations

import asyncio
import signal

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from src.config import get_settings
from src.database.engine import get_session_factory, init_database, shutdown_database
from src.handlers import build_root_router
from src.middlewares import (
    DatabaseMiddleware,
    DuplicateRequestMiddleware,
    ErrorHandlingMiddleware,
    ThrottlingMiddleware,
    UserActivityMiddleware,
)
from src.scheduler.jobs import build_scheduler
from src.utils.logger import configure_logging
from src.web.health import build_web_app

logger = structlog.get_logger(__name__)


async def _run_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    """Run the bot in long-polling mode (used when ``USE_WEBHOOK=false``)."""
    await bot.delete_webhook(drop_pending_updates=True)
    # Explicitly request every update type the routers actually use (notably
    # ``my_chat_member``, which powers zero-typing chat discovery) so Telegram
    # never withholds an update the bot depends on.
    await dispatcher.start_polling(
        bot,
        handle_signals=False,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )


async def main() -> None:
    """Bootstrap every subsystem and run until a shutdown signal is received."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.logs_path)
    logger.info("startup.begin", database="sqlite" if settings.is_sqlite else "postgresql")

    await init_database(settings)
    session_factory = get_session_factory()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())

    dispatcher.update.outer_middleware(ErrorHandlingMiddleware())
    dispatcher.update.outer_middleware(DuplicateRequestMiddleware())
    dispatcher.update.outer_middleware(DatabaseMiddleware(session_factory, settings))
    dispatcher.message.middleware(ThrottlingMiddleware(settings.rate_limit))
    dispatcher.update.outer_middleware(UserActivityMiddleware())
    dispatcher.include_router(build_root_router())

    scheduler = build_scheduler(settings)
    scheduler.start()

    web_app = build_web_app(
        settings=settings, bot=bot, dispatcher=dispatcher, session_factory=session_factory
    )
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, settings.host, settings.port)
    await site.start()
    logger.info("web.started", host=settings.host, port=settings.port)

    if settings.use_webhook and settings.webhook_url:
        await bot.set_webhook(
            url=f"{settings.webhook_url}/webhook",
            secret_token=settings.webhook_secret,
            drop_pending_updates=True,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        logger.info("webhook.configured", url=settings.webhook_url)

    stop_event = asyncio.Event()

    def _request_shutdown() -> None:
        logger.info("shutdown.signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig_name, _request_shutdown)  # type: ignore[attr-defined]
        except (NotImplementedError, AttributeError):
            loop.add_signal_handler = None  # noqa: E731 - platform without signal support

    try:
        loop.add_signal_handler  # noqa: B018 - probe attribute existence
    except AttributeError:
        pass

    for sig_name in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig_name, lambda *_: _request_shutdown())
        except (ValueError, OSError):  # pragma: no cover - non-main-thread/platform limits
            pass

    polling_task: asyncio.Task | None = None
    if not settings.use_webhook:
        polling_task = asyncio.create_task(_run_polling(bot, dispatcher))

    logger.info("startup.complete")
    await stop_event.wait()

    logger.info("shutdown.begin")
    if polling_task is not None:
        await dispatcher.stop_polling()
        polling_task.cancel()
    scheduler.shutdown(wait=False)
    await runner.cleanup()
    await bot.session.close()
    await shutdown_database()
    logger.info("shutdown.complete")


if __name__ == "__main__":
    asyncio.run(main())
