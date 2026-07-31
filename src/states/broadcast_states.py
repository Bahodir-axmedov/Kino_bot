"""Finite-state-machine states for the broadcast/advertisement flow."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    """Compose and confirm a broadcast campaign before it is sent."""

    waiting_for_content = State()
    waiting_for_buttons = State()
    # Broadcast (#19): optional scheduling -- "YYYY-MM-DD HH:MM" sent instead
    # of sending immediately.
    waiting_for_schedule_time = State()
    confirm = State()
