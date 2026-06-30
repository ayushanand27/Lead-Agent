"""Build daily WhatsApp summary messages for business owners."""

from __future__ import annotations

import asyncio
import logging

from app import db
from app.config import get_business_name, get_owner_phones
from app.whatsapp import send_whatsapp_reply

logger = logging.getLogger(__name__)

_MAX_SEND_ATTEMPTS = 2
_RETRY_DELAY_SECONDS = 3


def build_summary_text(owner_phone: str, stale_days: int = 2) -> str:
    stats = db.fetch_lead_stats(owner_phone)
    stale = db.fetch_stale_leads(owner_phone, stale_days)
    business = get_business_name()

    lines = [
        f"Good morning — {business} lead summary",
        "",
        f"Total leads: {stats['total']}",
    ]
    if stats["by_status"]:
        status_bits = ", ".join(f"{k}: {v}" for k, v in sorted(stats["by_status"].items()))
        lines.append(f"By status — {status_bits}")
    lines.append(f"Stale ({stale_days}+ days): {len(stale)}")
    if stale:
        lines.append("")
        lines.append("Needs follow-up:")
        for lead in stale[:5]:
            lines.append(f"• {lead['name']} ({lead['status']})")
        if len(stale) > 5:
            lines.append(f"…and {len(stale) - 5} more")
    lines.append("")
    lines.append("Reply on WhatsApp to manage leads, or open your admin dashboard.")
    return "\n".join(lines)


async def _send_summary_to_owner(owner: str, text: str) -> bool:
    for attempt in range(1, _MAX_SEND_ATTEMPTS + 1):
        ok = await send_whatsapp_reply(owner, text)
        if ok:
            return True
        if attempt < _MAX_SEND_ATTEMPTS:
            logger.warning(
                "Daily summary send failed for %s (attempt %s/%s), retrying…",
                owner,
                attempt,
                _MAX_SEND_ATTEMPTS,
            )
            await asyncio.sleep(_RETRY_DELAY_SECONDS)
    logger.error("Daily summary send failed for %s after %s attempts", owner, _MAX_SEND_ATTEMPTS)
    return False


async def send_daily_summaries(stale_days: int = 2) -> dict[str, int | list[str]]:
    owners = get_owner_phones()
    if not owners:
        return {"sent": 0, "failed": 0, "failed_owners": []}

    sent = 0
    failed = 0
    failed_owners: list[str] = []
    for owner in owners:
        text = build_summary_text(owner, stale_days=stale_days)
        ok = await _send_summary_to_owner(owner, text)
        if ok:
            sent += 1
        else:
            failed += 1
            failed_owners.append(owner)
    return {"sent": sent, "failed": failed, "failed_owners": failed_owners}
