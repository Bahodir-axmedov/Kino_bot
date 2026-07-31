"""Finite-state-machine states for managing mandatory-subscription targets."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ForceSubStates(StatesGroup):
    """Add a new mandatory-subscription target (Telegram or external platform).

    Telegram-auto-verifiable platforms (channel/group/discussion group) are
    added with zero typing via the tap-to-pick discovered-chat picker, so they
    need no free-text state. External platforms still collect a title, URL and
    optional instructions.
    """

    choosing_platform = State()
    waiting_for_title = State()  # external / bot platforms
    waiting_for_url = State()  # external / bot platforms
    waiting_for_instructions = State()  # external / bot platforms, optional (/skip)
