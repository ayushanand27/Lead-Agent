"""Display helpers for admin UI."""

from __future__ import annotations

import re


def mask_phone(phone: str | None) -> str:
    """Mask middle digits for privacy on screen recordings."""
    if not phone:
        return "—"
    digits = re.sub(r"\D", "", phone)
    if len(digits) <= 6:
        return phone
    hidden = max(len(digits) - 6, 0)
    return f"{digits[:2]}{'*' * hidden}{digits[-4:]}"
