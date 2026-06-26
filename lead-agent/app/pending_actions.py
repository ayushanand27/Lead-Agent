"""In-memory store for pending write actions awaiting owner confirmation."""

from typing import Any, Optional

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
    # Allow short affirmatives with trailing punctuation, e.g. "yes!"
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
    """Per-owner pending actions (in-process dict for v1)."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def set_pending(self, owner_phone: str, action_dict: dict[str, Any]) -> None:
        self._store[owner_phone] = dict(action_dict)

    def get_pending(self, owner_phone: str) -> Optional[dict[str, Any]]:
        pending = self._store.get(owner_phone)
        if pending is None:
            return None
        return dict(pending)

    def clear_pending(self, owner_phone: str) -> None:
        self._store.pop(owner_phone, None)

    def has_pending(self, owner_phone: str) -> bool:
        return owner_phone in self._store


# Module-level singleton for agent loop (step 4) and tests
pending_store = PendingActionStore()
