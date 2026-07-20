"""Service-level tests for the movie catalogue (against a real in-memory DB)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.movie import MediaType
from src.services.movie_service import MovieService
from src.utils.exceptions import MovieCodeAlreadyExistsError, MovieNotFoundError


@pytest.mark.asyncio
async def test_create_movie_generates_code_when_omitted(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    movie = await service.create_movie(
        code=None,
        title="Test Movie",
        telegram_file_id="FILE_ID_1",
        media_type=MediaType.VIDEO,
    )
    assert movie.code.isdigit()
    fetched = await service.get_by_code(movie.code)
    assert fetched.id == movie.id


@pytest.mark.asyncio
async def test_create_movie_rejects_duplicate_explicit_code(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    await service.create_movie(
        code="1055", title="First", telegram_file_id="FILE_ID_1", media_type=MediaType.VIDEO
    )
    with pytest.raises(MovieCodeAlreadyExistsError):
        await service.create_movie(
            code="1055", title="Second", telegram_file_id="FILE_ID_2", media_type=MediaType.VIDEO
        )


@pytest.mark.asyncio
async def test_get_by_code_raises_when_missing(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    with pytest.raises(MovieNotFoundError):
        await service.get_by_code("does-not-exist")


@pytest.mark.asyncio
async def test_get_by_code_raises_when_inactive(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    movie = await service.create_movie(
        code="2000", title="Hidden", telegram_file_id="FILE_ID_3", media_type=MediaType.VIDEO
    )
    await service.set_active(movie.id, False)
    with pytest.raises(MovieNotFoundError):
        await service.get_by_code("2000")


@pytest.mark.asyncio
async def test_find_duplicate_detects_same_file_id(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    await service.create_movie(
        code="3000", title="Original", telegram_file_id="SHARED_FILE", media_type=MediaType.VIDEO
    )
    duplicate = await service.find_duplicate("SHARED_FILE")
    assert duplicate is not None
    assert duplicate.code == "3000"


@pytest.mark.asyncio
async def test_replace_code_moves_movie_to_new_code(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    await service.create_movie(
        code="4000", title="Renamed", telegram_file_id="FILE_ID_4", media_type=MediaType.VIDEO
    )
    await service.replace_code("4000", "4001")
    with pytest.raises(MovieNotFoundError):
        await service.get_by_code("4000")
    assert (await service.get_by_code("4001")).code == "4001"


@pytest.mark.asyncio
async def test_register_delivery_increments_views_and_downloads(async_session: AsyncSession) -> None:
    service = MovieService(async_session)
    movie = await service.create_movie(
        code="5000", title="Popular", telegram_file_id="FILE_ID_5", media_type=MediaType.VIDEO
    )
    await service.register_delivery(movie)
    await service.register_delivery(movie)
    refreshed = await service.get_by_code("5000")
    assert refreshed.views_count == 2
    assert refreshed.downloads_count == 2
