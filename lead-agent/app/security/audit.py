"""Admin security audit events — stored in action_log."""

from __future__ import annotations

from app import db


def log_admin_event(owner_phone: str, action: str, details: str) -> None:
    db.log_action(owner_phone, action, details)
