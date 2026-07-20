"""Domain-specific exception hierarchy.

Using dedicated exception types (instead of bare ``Exception``/``ValueError``
everywhere) lets handlers catch precisely what they expect and lets the
global error middleware log everything else as truly unexpected.
"""

from __future__ import annotations


class KinoBotError(Exception):
    """Base class for every domain error raised by the application."""


class MovieNotFoundError(KinoBotError):
    """Raised when a movie code does not exist in the catalogue."""


class MovieCodeAlreadyExistsError(KinoBotError):
    """Raised when attempting to create a movie with a duplicate code."""


class DuplicateMediaError(KinoBotError):
    """Raised when the same Telegram file id is already indexed."""


class UserBannedError(KinoBotError):
    """Raised when a banned user attempts a restricted action."""


class UserMutedError(KinoBotError):
    """Raised when a muted user attempts to interact with the bot."""


class NotSubscribedError(KinoBotError):
    """Raised when a user has not joined all mandatory channels."""


class PermissionDeniedError(KinoBotError):
    """Raised when an actor lacks the role/permission required for an action."""


class InvalidInputError(KinoBotError):
    """Raised when user-supplied input fails validation."""


class RateLimitExceededError(KinoBotError):
    """Raised when an actor exceeds the configured rate limit."""


class BackupError(KinoBotError):
    """Raised when a backup or restore operation fails."""


class CodeReservedError(KinoBotError):
    """Raised when attempting to use/create a code that is currently reserved."""


class CodeReservationConflictError(KinoBotError):
    """Raised when two admins attempt to reserve the same code concurrently."""


class VisibilityDeniedError(KinoBotError):
    """Raised when a user requests a movie code they are not allowed to receive."""


class DuplicateRequestError(KinoBotError):
    """Raised when the same Telegram update is processed more than once."""


class StartupValidationError(KinoBotError):
    """Raised when a startup/environment/database/volume check fails."""


class MaintenanceModeError(KinoBotError):
    """Raised when a non-admin interacts with the bot while Maintenance Mode is ON."""


class BlacklistedError(KinoBotError):
    """Raised when a blacklisted user/value attempts a restricted action."""


class AdminLockedOutError(KinoBotError):
    """Raised when an admin is temporarily locked out after too many failed login attempts."""


class InvalidTwoFactorCodeError(KinoBotError):
    """Raised when an admin submits an incorrect or expired 2FA code."""


class SessionExpiredError(KinoBotError):
    """Raised when an admin panel session has expired or been revoked."""
