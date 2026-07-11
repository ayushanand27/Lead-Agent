"""Session-based auth for the owner admin dashboard."""

from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Request

from app.config import get_owner_phones, is_registered_owner
from app.security.passwords import verify_admin_password
from app.utils.phone import normalize_owner_phone


def get_admin_password() -> str | None:
    password = os.getenv("ADMIN_DASHBOARD_PASSWORD", "").strip()
    if len(password) >= 2 and password[0] == password[-1] and password[0] in "\"'":
        password = password[1:-1]
    return password or None


def get_session_secret() -> str:
    return os.getenv("ADMIN_SESSION_SECRET", "dev-change-me-in-production")


def is_production() -> bool:
    return os.getenv("RENDER") == "true" or os.getenv("ENVIRONMENT") == "production"


def login_owner(request: Request, owner_phone: str, password: str) -> bool:
    expected = get_admin_password()
    if not expected:
        return False
    if not verify_admin_password(password, expected):
        return False
    normalized = normalize_owner_phone(owner_phone)
    if not normalized:
        return False
    allowed = get_owner_phones()
    if allowed and normalized not in set(allowed):
        return False
    request.session["owner_phone"] = normalized
    return True


def logout_owner(request: Request) -> None:
    request.session.clear()


def get_session_owner(request: Request) -> str | None:
    phone = request.session.get("owner_phone")
    if not phone:
        return None
    normalized = normalize_owner_phone(str(phone))
    if not is_registered_owner(normalized):
        return None
    return normalized


def require_owner(request: Request) -> str:
    owner = get_session_owner(request)
    if not owner:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return owner


def dashboard_context(request: Request, **extra: Any) -> dict[str, Any]:
    from app.config import get_business_name, get_industry

    owner = require_owner(request)
    return {
        "request": request,
        "business_name": get_business_name(),
        "industry": get_industry(),
        "owner_phone": owner,
        **extra,
    }
