"""Google Sheets backup via Apps Script webhook (no paid API required)."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


def is_sheets_sync_enabled() -> bool:
    return bool(os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip())


def sync_lead_to_sheet(lead: dict) -> None:
    """
    POST lead row to a Google Apps Script web app URL.
    Failures are logged only — never break the main lead flow.
    """
    url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        return

    payload = {
        "id": lead.get("id"),
        "name": lead.get("name"),
        "phone": lead.get("phone"),
        "source": lead.get("source"),
        "status": lead.get("status"),
        "notes": lead.get("notes") or "",
        "consent_source": lead.get("consent_source") or "",
        "consent_at": lead.get("consent_at") or "",
        "last_contacted_at": lead.get("last_contacted_at") or "",
        "created_at": lead.get("created_at") or "",
        "owner_phone": lead.get("owner_phone") or "",
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except Exception:
        logger.exception("Google Sheets sync failed for lead id=%s", lead.get("id"))
