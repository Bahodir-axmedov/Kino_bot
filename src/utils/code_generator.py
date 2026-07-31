"""Movie code generation strategy.

Codes are short, human-typeable, numeric strings (e.g. ``1055``) so users can
share/type them easily. Generation is guarded by a process-wide
``asyncio.Lock`` so two admins creating movies concurrently can never be
handed the same random candidate before either has committed it -- closing
the race window that plain "check then insert" has under concurrent load.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

_MIN_CODE = 1000
_MAX_CODE = 999_999
_MAX_ATTEMPTS = 25

# One lock per process is sufficient: code generation is a rare, cheap,
# already-fast operation (a handful of indexed lookups), so serializing it
# never becomes a throughput bottleneck even under heavy concurrent load.
_generation_lock = asyncio.Lock()

# Backing counter for the optional auto-increment strategy. Seeded lazily by
# whoever calls generate_sequential_movie_code first with the current max.
_sequential_counter: int | None = None


async def generate_unique_movie_code(
    code_exists: Callable[[str], Awaitable[bool]],
) -> str:
    """Generate a random numeric movie code guaranteed unique by ``code_exists``.

    ``code_exists`` is an async predicate (typically
    ``MovieRepository.code_exists``) so this function stays free of any
    direct database dependency and remains trivially unit-testable.
    """
    async with _generation_lock:
        for _ in range(_MAX_ATTEMPTS):
            candidate = str(random.randint(_MIN_CODE, _MAX_CODE))
            if not await code_exists(candidate):
                return candidate
        raise RuntimeError("Could not generate a unique movie code after multiple attempts.")


async def generate_sequential_movie_code(
    code_exists: Callable[[str], Awaitable[bool]],
    *,
    current_max: int,
) -> str:
    """Generate the next auto-increment code above ``current_max``.

    ``current_max`` should be the highest existing numeric code known to the
    caller (e.g. from ``MovieRepository.max_numeric_code``). Guarded by the
    same process-wide lock as the random strategy so the two strategies can
    never race each other into handing out the same code.
    """
    global _sequential_counter
    async with _generation_lock:
        if _sequential_counter is None or _sequential_counter < current_max:
            _sequential_counter = current_max
        for _ in range(_MAX_ATTEMPTS):
            _sequential_counter += 1
            candidate = str(_sequential_counter)
            if not await code_exists(candidate):
                return candidate
        raise RuntimeError("Could not generate a unique sequential movie code.")
