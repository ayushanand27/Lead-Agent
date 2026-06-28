"""Owner notifications via WhatsApp."""

from __future__ import annotations

import logging
import os

from app.config import get_business_name, get_owner_phones
from app.whatsapp import send_whatsapp_reply

logger = logging.getLogger(__name__)


def _notifications_enabled() -> bool:
    return os.getenv("NOTIFY_OWNERS_ON_WEBHOOK", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


async def notify_owners_new_lead(lead: dict, channel: str = "webhook") -> None:
    """Send WhatsApp alert to all registered owners when a new lead is captured."""
    if not _notifications_enabled():
        return

    phones = get_owner_phones()
    if not phones:
        return

    business = get_business_name()
    name = lead.get("name", "")
    phone = lead.get("phone", "")
    source = lead.get("source", "")
    lead_id = lead.get("id", "")
    tags = lead.get("tags") or ""

    lines = [
        f"New lead — {business}",
        f"{name} | {phone}",
        f"Source: {source} ({channel})",
        f"ID: {lead_id}",
    ]
    if tags:
        lines.append(f"Tags: {tags}")

    message = "\n".join(lines)

    for owner_phone in phones:
        sent = await send_whatsapp_reply(owner_phone.strip().lstrip("+"), message)
        if not sent:
            logger.warning("Failed to notify owner %s about lead id=%s", owner_phone, lead_id)
