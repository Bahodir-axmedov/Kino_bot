"""Finite-state-machine states for administrator management flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddAdminStates(StatesGroup):
    """Add a new administrator by Telegram id and role."""

    waiting_for_telegram_id = State()
    waiting_for_role = State()


class SettingsEditStates(StatesGroup):
    """Edit a single Settings Center value."""

    waiting_for_value = State()


class CollectionStates(StatesGroup):
    """Create or rename a Media Collection."""

    waiting_for_name = State()
    waiting_for_rename = State()


class BlacklistStates(StatesGroup):
    """Add a new Blacklist Center entry."""

    waiting_for_value = State()


class WhitelistStates(StatesGroup):
    """Add a new Whitelist Center entry."""

    waiting_for_value = State()


class AdStates(StatesGroup):
    """Create a new Advertisement Center text campaign."""

    waiting_for_text = State()
    waiting_for_interval = State()


class SecurityStates(StatesGroup):
    """Admin Security Center + Admin Login Protection gate."""

    waiting_for_new_pin = State()
    waiting_for_login_pin = State()
    waiting_for_login_two_factor = State()


class PremiumGrantStates(StatesGroup):
    """Grant premium to a user for a specific number of days."""

    waiting_for_days = State()
