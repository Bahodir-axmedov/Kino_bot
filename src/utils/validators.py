"""Input validation helpers used by handlers before touching the database.

Centralizing validation here (rather than scattering ``if`` checks through
handlers) keeps FSM flows short and makes every accepted input shape
auditable in one place.
"""

from __future__ import annotations

import re

from src.utils.exceptions import InvalidInputError

_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_YEAR_PATTERN = re.compile(r"^(19|20)\d{2}$")


def normalize_movie_code(raw_code: str) -> str:
    """Validate and normalize a user-supplied movie code.

    Codes are restricted to a small, predictable alphabet so they are safe to
    embed in callback data, URLs, and log lines without further escaping.
    """
    code = raw_code.strip()
    if not _CODE_PATTERN.match(code):
        raise InvalidInputError(
            "Kino kodi faqat harf, raqam, '_' va '-' belgilaridan iborat bo'lishi va "
            "32 belgidan oshmasligi kerak."
        )
    return code


def validate_year(raw_year: str) -> int:
    """Validate a 4-digit release year between 1900 and 2099."""
    if not _YEAR_PATTERN.match(raw_year.strip()):
        raise InvalidInputError("Yil formati noto'g'ri. Masalan: 2024")
    return int(raw_year)


def validate_telegram_id(raw_id: str) -> int:
    """Validate a numeric Telegram user/chat id (may be negative for chats)."""
    candidate = raw_id.strip()
    if not candidate.lstrip("-").isdigit():
        raise InvalidInputError("Telegram ID faqat raqamlardan iborat bo'lishi kerak.")
    return int(candidate)


def validate_non_empty_text(raw_text: str, *, field_name: str, max_length: int = 4096) -> str:
    """Validate that free text is present and within Telegram's length limits."""
    text = raw_text.strip()
    if not text:
        raise InvalidInputError(f"{field_name} bo'sh bo'lishi mumkin emas.")
    if len(text) > max_length:
        raise InvalidInputError(f"{field_name} {max_length} belgidan oshmasligi kerak.")
    return text


def validate_channel_reference(raw_reference: str) -> str:
    """Validate a channel/group reference: ``@username`` or numeric chat id."""
    reference = raw_reference.strip()
    if reference.startswith("@") and len(reference) > 1:
        return reference
    if reference.lstrip("-").isdigit():
        return reference
    raise InvalidInputError(
        "Kanal/guruh @username yoki raqamli chat ID ko'rinishida bo'lishi kerak."
    )
