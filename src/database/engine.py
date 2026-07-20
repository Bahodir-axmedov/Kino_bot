"""Async SQLAlchemy engine and session-factory lifecycle management.

The engine is created once per process. Switching from SQLite to PostgreSQL
later only requires changing ``DATABASE_URL`` -- no code in this module (or
anywhere else in the app) needs to change.
"""

from __future__ import annotations

import structlog
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.config import Settings
from src.database.base import Base

logger = structlog.get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine(settings: Settings) -> AsyncEngine:
    """Create a new async engine tuned for the configured database backend."""
    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {"echo": False, "future": True}

    if settings.is_sqlite:
        # SQLite has no real connection pool; NullPool avoids stale
        # connections surviving a Railway container restart/reconnect.
        connect_args["timeout"] = 30
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
        engine_kwargs["pool_recycle"] = 1800

    engine = create_async_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)

    if settings.is_sqlite:
        _install_sqlite_pragmas(engine)

    return engine


def _install_sqlite_pragmas(engine: AsyncEngine) -> None:
    """Tune SQLite for concurrent async access via a raw-DBAPI connect hook.

    - ``WAL`` lets readers proceed while a writer is active, which matters a
      lot once many users are querying while an admin is writing.
    - ``synchronous=NORMAL`` is the recommended pairing with WAL: still safe
      against application crashes, far less fsync overhead than FULL.
    - ``foreign_keys=ON`` enforces the FK constraints declared on the models
      (SQLite does not enforce them by default).
    - ``busy_timeout`` avoids immediate "database is locked" errors under
      concurrent write bursts, giving SQLite a window to retry internally.
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


async def init_database(settings: Settings, *, create_all: bool = True) -> AsyncEngine:
    """Initialize the global engine/session-factory and optionally create tables.

    ``create_all`` is a safety net for first boot / SQLite deployments where
    Alembic migrations have not been run yet. In production, Alembic
    (``alembic upgrade head``) is the source of truth for schema changes.
    """
    global _engine, _session_factory

    _engine = _build_engine(settings)
    _session_factory = async_sessionmaker(
        bind=_engine, expire_on_commit=False, class_=AsyncSession
    )

    if create_all:
        async with _engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            if settings.is_sqlite:
                await connection.run_sync(_drop_obsolete_source_chat_fk)

    logger.info("database.initialized", backend=settings.database_url.split(":")[0])
    return _engine


def _drop_obsolete_source_chat_fk(sync_connection) -> None:  # noqa: ANN001
    """Rebuild ``movies`` to drop the obsolete ``source_chat_id`` FK on old DBs.

    Early schema versions declared ``movies.source_chat_id`` as a FOREIGN KEY
    to ``media_sources.chat_id``. That made it impossible to index media
    captured from an unregistered group or uploaded directly to the bot
    ("FOREIGN KEY constraint failed"). The model no longer declares that FK,
    but ``create_all`` never alters an existing table, so this one-shot,
    idempotent migration rebuilds the table in place on databases created
    before the fix. It is a no-op once the FK is gone.
    """
    from sqlalchemy import inspect

    from src.models.movie import Movie

    inspector = inspect(sync_connection)
    if "movies" not in inspector.get_table_names():
        return
    has_obsolete_fk = any(
        fk.get("referred_table") == "media_sources"
        and "source_chat_id" in (fk.get("constrained_columns") or [])
        for fk in inspector.get_foreign_keys("movies")
    )
    if not has_obsolete_fk:
        return

    logger.info("database.migrating", change="drop movies.source_chat_id FK")
    columns = [column["name"] for column in inspector.get_columns("movies")]
    column_csv = ", ".join(f'"{name}"' for name in columns)
    droppable_indexes = [
        row[0]
        for row in sync_connection.exec_driver_sql(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND tbl_name='movies' AND sql IS NOT NULL"
        ).fetchall()
    ]

    # No table references ``movies``, so a straight rename-copy-drop is safe.
    sync_connection.exec_driver_sql("ALTER TABLE movies RENAME TO _movies_pre_fk_drop")
    for index_name in droppable_indexes:
        sync_connection.exec_driver_sql(f'DROP INDEX "{index_name}"')
    # Recreate ``movies`` (and its indexes) from the current, FK-free model.
    Movie.__table__.create(bind=sync_connection)
    sync_connection.exec_driver_sql(
        f"INSERT INTO movies ({column_csv}) SELECT {column_csv} FROM _movies_pre_fk_drop"
    )
    sync_connection.exec_driver_sql("DROP TABLE _movies_pre_fk_drop")
    logger.info("database.migrated", change="drop movies.source_chat_id FK")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory. Raises if not initialized."""
    if _session_factory is None:
        raise RuntimeError("Database has not been initialized. Call init_database() first.")
    return _session_factory


async def is_database_reachable(session_factory: async_sessionmaker[AsyncSession]) -> bool:
    """Return True if a trivial query succeeds against the database.

    Used by the /health endpoint so Railway can detect a database that has
    become unreachable (e.g. after a Volume issue) and restart the container.
    """
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as error:  # noqa: BLE001 - health check must never raise
        logger.error("database.health_check_failed", error=str(error))
        return False


async def shutdown_database() -> None:
    """Dispose the engine gracefully, releasing all pooled connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("database.disposed")
    _engine = None
    _session_factory = None
