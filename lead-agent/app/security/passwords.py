"""Admin password verification — plain text or bcrypt hash."""

from __future__ import annotations

import secrets


def verify_admin_password(plain: str, stored: str) -> bool:
    """
    Verify password against env value.
    Supports bcrypt hashes ($2a$ / $2b$) or legacy plain text (backward compatible).
    """
    if not stored:
        return False
    if stored.startswith("$2"):
        try:
            import bcrypt

            return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
        except Exception:
            return False
    return secrets.compare_digest(plain, stored)


def hash_password(plain: str) -> str:
    import bcrypt

    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
