"""Lightweight in-process runtime metrics for the admin dashboard.

No external time-series database is used -- these are simple rolling
counters/windows kept in module-level state for a single process. This is
enough to answer "is the bot fast / healthy right now" from inside Telegram
without adding an operational dependency (Prometheus, etc.) that the project
does not otherwise need.
"""

from __future__ import annotations

import time
from collections import deque

_RESPONSE_WINDOW: deque[float] = deque(maxlen=500)
_REQUEST_COUNT = 0
_ERROR_COUNT = 0
_STARTED_AT = time.monotonic()
_ERROR_TIMESTAMPS: deque[float] = deque(maxlen=2000)


def record_request_duration(duration_seconds: float) -> None:
    """Record one handled update's end-to-end processing duration."""
    global _REQUEST_COUNT
    _RESPONSE_WINDOW.append(duration_seconds)
    _REQUEST_COUNT += 1


def record_error() -> None:
    """Record one unhandled/unexpected error occurrence."""
    global _ERROR_COUNT
    _ERROR_COUNT += 1
    _ERROR_TIMESTAMPS.append(time.time())


def errors_since(seconds_ago: float) -> int:
    """Return how many recorded errors happened within the last ``seconds_ago``."""
    cutoff = time.time() - seconds_ago
    return sum(1 for timestamp in _ERROR_TIMESTAMPS if timestamp >= cutoff)


def uptime_seconds() -> float:
    """Return how long this process has been running."""
    return time.monotonic() - _STARTED_AT


def average_response_ms() -> float:
    """Return the average recorded response time in milliseconds (0 if none yet)."""
    if not _RESPONSE_WINDOW:
        return 0.0
    return (sum(_RESPONSE_WINDOW) / len(_RESPONSE_WINDOW)) * 1000


def requests_per_second() -> float:
    """Return an approximate requests/sec figure based on the rolling window."""
    if not _RESPONSE_WINDOW or uptime_seconds() <= 0:
        return 0.0
    window_seconds = sum(_RESPONSE_WINDOW)
    if window_seconds <= 0:
        return 0.0
    return len(_RESPONSE_WINDOW) / max(window_seconds, 0.001)


def snapshot() -> dict[str, float | int]:
    """Return every counter/derived metric as a single dict for rendering."""
    return {
        "total_requests": _REQUEST_COUNT,
        "total_errors": _ERROR_COUNT,
        "errors_last_24h": errors_since(86400),
        "average_response_ms": round(average_response_ms(), 2),
        "requests_per_second": round(requests_per_second(), 3),
        "uptime_seconds": round(uptime_seconds(), 1),
    }


def reset_for_tests() -> None:
    """Clear all counters. Only intended to be called from the test suite."""
    global _REQUEST_COUNT, _ERROR_COUNT
    _RESPONSE_WINDOW.clear()
    _ERROR_TIMESTAMPS.clear()
    _REQUEST_COUNT = 0
    _ERROR_COUNT = 0
