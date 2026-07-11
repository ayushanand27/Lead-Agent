"""Admin password verification — plain text or bcrypt hash."""

from __future__ import annotations

import secrets


def verify_admin_password(plain: str, stored: str) -> bool:
    """
    Verify password against env value.
    Supports bcrypt hashes ($2a$ / $2b$) or legacy plain text (backward compatible).
    """
    if not stored or plain is None:
        return False
    # Accidental spaces from mobile keyboards / copy-paste
    candidate = plain.strip()
    expected = stored.strip()
    # Render UI sometimes wraps values in quotes
    if len(expected) >= 2 and expected[0] == expected[-1] and expected[0] in "\"'":
        expected = expected[1:-1]

    if expected.startswith("$2"):
        try:
            import bcrypt

            return bcrypt.checkpw(candidate.encode("utf-8"), expected.encode("utf-8"))
        except Exception:
            return False
    try:
        return secrets.compare_digest(candidate, expected)
    except (TypeError, ValueError):
        return False


def hash_password(plain: str) -> str:
    import bcrypt

    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
