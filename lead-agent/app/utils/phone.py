"""Phone number normalization for owners and dashboard login."""

from __future__ import annotations

import re


def normalize_owner_phone(phone: str | None) -> str:
    """
    Digits-only WhatsApp owner number.
    Accepts +91…, spaces, dashes, or bare 10-digit Indian mobiles.
    """
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"91{digits[1:]}"
    return digits
