"""Persistent store for pending write actions awaiting owner confirmation."""

from __future__ import annotations

import json
from typing import Any, Optional

from app import db

TERMINAL_STATUSES = frozenset({"converted", "lost"})

CONFIRMATION_KEYWORDS = frozenset(
    {
        "yes",
        "haan",
        "haan bhej do",
        "send it",
        "confirm",
        "kar do",
        "bhej do",
    }
)

ACTIONS_REQUIRING_CONFIRMATION = frozenset(
    {
        "send_whatsapp_message",
        "update_lead_status_terminal",
    }
)


def is_confirmation_message(text: str) -> bool:
    """Return True if the owner's reply is an affirmative confirmation."""
    normalized = " ".join(text.strip().lower().split())
    if not normalized:
        return False
    if normalized in CONFIRMATION_KEYWORDS:
        return True
    stripped = normalized.rstrip("!.?")
    return stripped in CONFIRMATION_KEYWORDS


def requires_confirmation(action: str, new_status: str | None = None) -> bool:
    """Return True if this action must wait for owner confirmation before executing."""
    if action == "send_whatsapp_message":
        return True
    if action == "update_lead_status" and new_status in TERMINAL_STATUSES:
        return True
    return False


class PendingActionStore:
    """Per-owner pending actions persisted in the database."""

    def set_pending(self, owner_phone: str, action_dict: dict[str, Any]) -> None:
        db.upsert_pending_action(owner_phone, action_dict)

    def get_pending(self, owner_phone: str) -> Optional[dict[str, Any]]:
        pending = db.fetch_pending_action(owner_phone)
        if pending is None:
            return None
        return dict(pending)

    def clear_pending(self, owner_phone: str) -> None:
        db.delete_pending_action(owner_phone)

    def has_pending(self, owner_phone: str) -> bool:
        return db.fetch_pending_action(owner_phone) is not None


pending_store = PendingActionStore()
