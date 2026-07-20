"""Shared pytest fixtures: isolated env vars and an in-memory async DB."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.base import Base


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Populate the minimal required environment variables for Settings()."""
    monkeypatch.setenv("BOT_TOKEN", "123:test-token")
    monkeypatch.setenv("OWNER_ID", "1")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("BACKUP_PATH", "/tmp/kino_bot_test_backups")
    monkeypatch.setenv("LOGS_PATH", "/tmp/kino_bot_test_logs")
    os.makedirs("/tmp/kino_bot_test_backups", exist_ok=True)
    os.makedirs("/tmp/kino_bot_test_logs", exist_ok=True)
    from src.config.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    """Yield a fresh in-memory SQLite async session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()
