"""In-memory store for pending write actions awaiting owner confirmation."""

from dataclasses import dataclass
from typing import Literal, Optional


PendingActionType = Literal[
    "send_whatsapp_message",
    "update_lead_status",
    "create_lead",
    "add_lead_note",
]


@dataclass
class PendingAction:
    action: PendingActionType
    lead_id: Optional[int] = None
    message_text: Optional[str] = None
    new_status: Optional[str] = None
    # create_lead / add_note fields added in step 3


class PendingActionStore:
    """Per-owner pending actions (in-process dict for v1)."""

    def __init__(self) -> None:
        self._store: dict[str, PendingAction] = {}

    def set(self, owner_phone: str, action: PendingAction) -> None:
        self._store[owner_phone] = action

    def get(self, owner_phone: str) -> Optional[PendingAction]:
        return self._store.get(owner_phone)

    def clear(self, owner_phone: str) -> None:
        self._store.pop(owner_phone, None)

    def has_pending(self, owner_phone: str) -> bool:
        return owner_phone in self._store
