"""Unit tests for movie code generation."""

from __future__ import annotations

import pytest

from src.utils.code_generator import generate_unique_movie_code


@pytest.mark.asyncio
async def test_generate_unique_movie_code_returns_numeric_string() -> None:
    async def code_exists(_: str) -> bool:
        return False

    code = await generate_unique_movie_code(code_exists)
    assert code.isdigit()
    assert 1000 <= int(code) <= 999_999


@pytest.mark.asyncio
async def test_generate_unique_movie_code_retries_until_unique() -> None:
    seen: set[str] = set()

    async def code_exists(candidate: str) -> bool:
        # Force the first two attempts to collide, then accept.
        if len(seen) < 2:
            seen.add(candidate)
            return True
        return candidate in seen

    code = await generate_unique_movie_code(code_exists)
    assert code not in seen


@pytest.mark.asyncio
async def test_generate_unique_movie_code_raises_when_exhausted() -> None:
    async def always_exists(_: str) -> bool:
        return True

    with pytest.raises(RuntimeError):
        await generate_unique_movie_code(always_exists)
