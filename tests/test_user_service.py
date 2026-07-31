"""Service-level tests for user registration and moderation actions."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.user_service import UserService
from src.utils.exceptions import UserBannedError, UserMutedError


@pytest.mark.asyncio
async def test_get_or_register_creates_new_user(async_session: AsyncSession) -> None:
    service = UserService(async_session)
    user, is_new = await service.get_or_register(
        telegram_id=111, username="alice", first_name="Alice", last_name=None, language_code="uz"
    )
    assert is_new is True
    assert user.telegram_id == 111


@pytest.mark.asyncio
async def test_get_or_register_returns_existing_user_on_second_call(async_session: AsyncSession) -> None:
    service = UserService(async_session)
    await service.get_or_register(
        telegram_id=222, username="bob", first_name="Bob", last_name=None, language_code="uz"
    )
    user, is_new = await service.get_or_register(
        telegram_id=222, username="bob2", first_name="Bob", last_name=None, language_code="uz"
    )
    assert is_new is False
    assert user.username == "bob2"


@pytest.mark.asyncio
async def test_referral_increments_referrer_invite_count(async_session: AsyncSession) -> None:
    service = UserService(async_session)
    referrer, _ = await service.get_or_register(
        telegram_id=333, username="ref", first_name="Ref", last_name=None, language_code="uz"
    )
    await service.get_or_register(
        telegram_id=444,
        username="invitee",
        first_name="Invitee",
        last_name=None,
        language_code="uz",
        referred_by=333,
    )
    refreshed = await service.find_by_identifier("333")
    assert refreshed is not None
    assert refreshed.invite_count == 1


@pytest.mark.asyncio
async def test_assert_not_restricted_raises_for_banned_user(async_session: AsyncSession) -> None:
    service = UserService(async_session)
    user, _ = await service.get_or_register(
        telegram_id=555, username="banned", first_name=None, last_name=None, language_code="uz"
    )
    await service.ban(555, "spam")
    banned_user = await service.find_by_identifier("555")
    assert banned_user is not None
    with pytest.raises(UserBannedError):
        await service.assert_not_restricted(banned_user)


@pytest.mark.asyncio
async def test_assert_not_restricted_raises_for_muted_user(async_session: AsyncSession) -> None:
    service = UserService(async_session)
    await service.get_or_register(
        telegram_id=666, username="muted", first_name=None, last_name=None, language_code="uz"
    )
    await service.set_muted(666, True)
    muted_user = await service.find_by_identifier("666")
    assert muted_user is not None
    with pytest.raises(UserMutedError):
        await service.assert_not_restricted(muted_user)


@pytest.mark.asyncio
async def test_grant_and_revoke_premium(async_session: AsyncSession) -> None:
    service = UserService(async_session)
    await service.get_or_register(
        telegram_id=777, username="vip", first_name=None, last_name=None, language_code="uz"
    )
    await service.grant_premium(777, days=30)
    vip_user = await service.find_by_identifier("777")
    assert vip_user is not None and vip_user.is_premium is True

    await service.revoke_premium(777)
    vip_user = await service.find_by_identifier("777")
    assert vip_user is not None and vip_user.is_premium is False
