"""Google Sheets backup via Apps Script webhook (no paid API required)."""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def is_sheets_sync_enabled() -> bool:
    return bool(os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip())


def _json_safe(value: Any) -> str | int | float | bool:
    """Convert DB values (e.g. Postgres datetime) to JSON-safe scalars."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value  # type: ignore[return-value]


def _post_to_apps_script(client: httpx.Client, url: str, body: str) -> httpx.Response:
    """
    POST to Google Apps Script web app.

    GAS returns 302; httpx must not follow with GET (drops body). We re-POST to Location.
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LeadAgent/1.2",
    }
    response = client.post(url, content=body, headers=headers, follow_redirects=False)
    if response.status_code in (301, 302, 303, 307, 308):
        location = response.headers.get("Location")
        if location:
            response = client.post(
                location,
                content=body,
                headers=headers,
                follow_redirects=False,
            )
    return response


def sync_lead_to_sheet(lead: dict) -> None:
    """
    POST lead row to a Google Apps Script web app URL.
    Failures are logged only — never break the main lead flow.
    """
    url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        return

    payload = {
        "id": _json_safe(lead.get("id")),
        "name": _json_safe(lead.get("name")),
        "phone": _json_safe(lead.get("phone")),
        "source": _json_safe(lead.get("source")),
        "status": _json_safe(lead.get("status")),
        "notes": _json_safe(lead.get("notes")),
        "consent_source": _json_safe(lead.get("consent_source")),
        "consent_at": _json_safe(lead.get("consent_at")),
        "last_contacted_at": _json_safe(lead.get("last_contacted_at")),
        "created_at": _json_safe(lead.get("created_at")),
        "owner_phone": _json_safe(lead.get("owner_phone")),
    }

    body = json.dumps(payload)

    try:
        with httpx.Client(timeout=20.0) as client:
            response = _post_to_apps_script(client, url, body)
            if response.status_code >= 400:
                logger.error(
                    "Google Sheets sync HTTP %s for lead id=%s: %s",
                    response.status_code,
                    lead.get("id"),
                    response.text[:300],
                )
                return
            logger.info(
                "Google Sheets sync ok for lead id=%s (HTTP %s)",
                lead.get("id"),
                response.status_code,
            )
    except Exception:
        logger.exception("Google Sheets sync failed for lead id=%s", lead.get("id"))
