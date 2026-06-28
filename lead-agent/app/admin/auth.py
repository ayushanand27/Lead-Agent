"""Session-based auth for the owner admin dashboard."""

from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import HTTPException, Request

from app.config import get_owner_phones, is_registered_owner


def get_admin_password() -> str | None:
    password = os.getenv("ADMIN_DASHBOARD_PASSWORD", "").strip()
    return password or None


def get_session_secret() -> str:
    return os.getenv("ADMIN_SESSION_SECRET", "dev-change-me-in-production")


def login_owner(request: Request, owner_phone: str, password: str) -> bool:
    expected = get_admin_password()
    if not expected:
        return False
    if not secrets.compare_digest(password, expected):
        return False
    normalized = owner_phone.strip().lstrip("+")
    if not is_registered_owner(normalized):
        allowed = get_owner_phones()
        if allowed and normalized not in {p.lstrip("+") for p in allowed}:
            return False
    request.session["owner_phone"] = normalized
    return True


def logout_owner(request: Request) -> None:
    request.session.clear()


def get_session_owner(request: Request) -> str | None:
    phone = request.session.get("owner_phone")
    if not phone:
        return None
    if not is_registered_owner(str(phone)):
        return None
    return str(phone)


def require_owner(request: Request) -> str:
    owner = get_session_owner(request)
    if not owner:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return owner


def dashboard_context(request: Request, **extra: Any) -> dict[str, Any]:
    from app.config import get_business_name, get_industry

    owner = require_owner(request)
    return {
        "business_name": get_business_name(),
        "industry": get_industry(),
        "owner_phone": owner,
        "active_page": extra.pop("active_page", ""),
        **extra,
    }
