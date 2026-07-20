"""Finite-state-machine states for user-management admin flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class UserManagementStates(StatesGroup):
    """Look up a user and act on them (ban/unban/mute/premium/history)."""

    waiting_for_identifier = State()
    waiting_for_ban_reason = State()


class PremiumPurchaseStates(StatesGroup):
    """Buy Premium via card: waiting for the user to upload a payment receipt."""

    waiting_for_receipt = State()
