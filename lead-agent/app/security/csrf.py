"""Session-bound CSRF tokens for admin dashboard forms."""

from __future__ import annotations

import secrets

from fastapi import Request

_SESSION_KEY = "csrf_token"


def get_csrf_token(request: Request) -> str:
    """Return the session's CSRF token, generating one on first use."""
    token = request.session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[_SESSION_KEY] = token
    return token


def verify_csrf_token(request: Request, submitted: str | None) -> bool:
    expected = request.session.get(_SESSION_KEY)
    if not expected or not submitted:
        return False
    return secrets.compare_digest(submitted, expected)
