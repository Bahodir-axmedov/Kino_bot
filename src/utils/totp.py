"""Minimal, dependency-free TOTP (RFC 6238) implementation for Admin 2FA.

No third-party TOTP/2FA library is available in this environment, so the
algorithm is implemented directly against the Python standard library
(``hmac``, ``hashlib``, ``base64``, ``secrets``) rather than pulling in an
unvetted dependency. This is the same algorithm used by Google
Authenticator, Authy, and other standard TOTP apps.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

_DEFAULT_PERIOD_SECONDS = 30
_DEFAULT_DIGITS = 6


def generate_secret() -> str:
    """Generate a new random base32 TOTP secret suitable for a QR/manual entry."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _hotp(secret: str, counter: int, digits: int = _DEFAULT_DIGITS) -> str:
    """Compute one HOTP value (RFC 4226) for ``secret`` at ``counter``."""
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(padded.upper())
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    truncated = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(truncated % (10**digits)).zfill(digits)


def current_code(secret: str, *, period: int = _DEFAULT_PERIOD_SECONDS, digits: int = _DEFAULT_DIGITS) -> str:
    """Return the TOTP code for ``secret`` valid at the current time."""
    counter = int(time.time() // period)
    return _hotp(secret, counter, digits)


def verify_code(
    secret: str, code: str, *, period: int = _DEFAULT_PERIOD_SECONDS, digits: int = _DEFAULT_DIGITS, window: int = 1
) -> bool:
    """Verify ``code`` against ``secret``, tolerating clock drift of ``window`` periods."""
    counter = int(time.time() // period)
    normalized = code.strip()
    for offset in range(-window, window + 1):
        if _hotp(secret, counter + offset, digits) == normalized:
            return True
    return False


def provisioning_uri(secret: str, *, account_name: str, issuer: str = "KinoBot") -> str:
    """Build a ``otpauth://`` URI that standard TOTP apps can import via QR code."""
    label = f"{issuer}:{account_name}"
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&digits={_DEFAULT_DIGITS}&period={_DEFAULT_PERIOD_SECONDS}"
