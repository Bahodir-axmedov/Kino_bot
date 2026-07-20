"""Unit tests for input validators."""

from __future__ import annotations

import pytest

from src.utils.exceptions import InvalidInputError
from src.utils.validators import (
    normalize_movie_code,
    validate_channel_reference,
    validate_non_empty_text,
    validate_telegram_id,
    validate_year,
)


def test_normalize_movie_code_accepts_valid_code() -> None:
    assert normalize_movie_code(" 1055 ") == "1055"


@pytest.mark.parametrize("bad_code", ["", " ", "has space", "a" * 33, "bad;code"])
def test_normalize_movie_code_rejects_invalid_code(bad_code: str) -> None:
    with pytest.raises(InvalidInputError):
        normalize_movie_code(bad_code)


def test_validate_year_accepts_valid_year() -> None:
    assert validate_year("2024") == 2024


@pytest.mark.parametrize("bad_year", ["18", "20", "abcd", "21000"])
def test_validate_year_rejects_invalid_year(bad_year: str) -> None:
    with pytest.raises(InvalidInputError):
        validate_year(bad_year)


def test_validate_telegram_id_accepts_negative_chat_ids() -> None:
    assert validate_telegram_id("-100123456") == -100123456


def test_validate_telegram_id_rejects_non_numeric() -> None:
    with pytest.raises(InvalidInputError):
        validate_telegram_id("not-a-number")


def test_validate_non_empty_text_rejects_blank() -> None:
    with pytest.raises(InvalidInputError):
        validate_non_empty_text("   ", field_name="Sarlavha")


def test_validate_non_empty_text_rejects_too_long() -> None:
    with pytest.raises(InvalidInputError):
        validate_non_empty_text("a" * 10, field_name="Sarlavha", max_length=5)


def test_validate_channel_reference_accepts_username_and_id() -> None:
    assert validate_channel_reference("@mychannel") == "@mychannel"
    assert validate_channel_reference("-1001234567890") == "-1001234567890"


def test_validate_channel_reference_rejects_garbage() -> None:
    with pytest.raises(InvalidInputError):
        validate_channel_reference("not a channel")
