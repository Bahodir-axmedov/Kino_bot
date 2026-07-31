"""Helpers for acquiring scoped async sessions with automatic rollback."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.engine import get_session_factory


@asynccontextmanager
async def session_scope(
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncIterator[AsyncSession]:
    """Yield a transactional session; commits on success, rolls back on error.

    This guarantees every unit of work is atomic: either every change in the
    block is persisted, or none of it is, which is essential once many
    concurrent users hit the same rows (e.g. incrementing view counters).

    ``session_factory`` is optional: callers that already hold the factory
    (e.g. :class:`DatabaseMiddleware`) may pass it to avoid the global lookup,
    while everyone else falls back to the process-wide factory. Accepting both
    call styles prevents the ``TypeError`` that otherwise fires on every
    update and is silently swallowed by the error middleware.
    """
    if session_factory is None:
        session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
