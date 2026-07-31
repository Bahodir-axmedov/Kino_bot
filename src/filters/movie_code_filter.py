"""Filter that matches plain-text messages shaped like a movie code."""

from __future__ import annotations

import re
from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import Message

_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")


class MovieCodeFilter(BaseFilter):
    """Passes only when the message text looks like a valid movie code.

    This keeps the free-text "send me a code" flow from swallowing arbitrary
    chatter -- only strings matching the code alphabet are routed here.
    """

    async def __call__(self, message: Message, **kwargs: Any) -> bool:
        """Return ``True`` when ``message.text`` matches the code alphabet."""
        if not message.text:
            return False
        return bool(_CODE_PATTERN.match(message.text.strip()))
