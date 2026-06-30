"""Google Sheets backup via Apps Script webhook (no paid API required)."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import date, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# GAS web apps rate-limit bursts — small pause between backfill rows
_BACKFILL_DELAY_SECONDS = 0.35
_GAS_TIMEOUT = httpx.Timeout(10.0, read=45.0)
_MAX_ATTEMPTS = 2
_RETRY_PAUSE_SECONDS = 2.0
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


def is_sheets_sync_enabled() -> bool:
    return bool(os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip())


def _json_safe(value: Any) -> str | int | float | bool:
    """Convert DB values (e.g. Postgres datetime) to JSON-safe scalars."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value  # type: ignore[return-value]


def _lead_payload(lead: dict) -> dict[str, Any]:
    return {
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
        "tags": _json_safe(lead.get("tags")),
    }


def _post_success(post_status: int) -> bool:
    """GAS runs doPost on POST; 302 redirect means the script executed."""
    if post_status in _REDIRECT_STATUSES:
        return True
    return post_status < 400


def sync_lead_to_sheet(lead: dict) -> bool:
    """
    POST lead row to a Google Apps Script web app URL.
    Returns True on success. Never raises — safe to call from agent/webhook paths.
    """
    url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        return False

    body = json.dumps(_lead_payload(lead))
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LeadAgent/1.3",
    }

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(timeout=_GAS_TIMEOUT) as client:
                post_response = client.post(
                    url,
                    content=body,
                    headers=headers,
                    follow_redirects=False,
                )
            post_status = post_response.status_code

            if _post_success(post_status):
                logger.info(
                    "Google Sheets sync ok for lead id=%s (HTTP %s)",
                    lead.get("id"),
                    post_status,
                )
                return True

            logger.error(
                "Google Sheets sync HTTP %s for lead id=%s: %s",
                post_status,
                lead.get("id"),
                post_response.text[:300],
            )
            return False
        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            if attempt < _MAX_ATTEMPTS:
                logger.warning(
                    "Google Sheets sync timeout for lead id=%s (attempt %s/%s), retrying…",
                    lead.get("id"),
                    attempt,
                    _MAX_ATTEMPTS,
                )
                time.sleep(_RETRY_PAUSE_SECONDS)
                continue
            logger.error(
                "Google Sheets sync timed out for lead id=%s after %s attempts",
                lead.get("id"),
                _MAX_ATTEMPTS,
            )
            return False
        except Exception:
            logger.exception("Google Sheets sync failed for lead id=%s", lead.get("id"))
            return False

    return False


def sync_lead_to_sheet_background(lead: dict) -> None:
    """Fire-and-forget sheet sync — does not block HTTP or WhatsApp replies."""
    threading.Thread(
        target=sync_lead_to_sheet,
        args=(lead,),
        daemon=True,
        name=f"sheets-sync-{lead.get('id')}",
    ).start()


def sync_all_leads_to_sheet(leads: list[dict]) -> tuple[int, int]:
    """Backfill — sync every lead (one row per call). Returns (ok_count, fail_count)."""
    ok = 0
    failed = 0
    for index, lead in enumerate(leads):
        if index > 0:
            time.sleep(_BACKFILL_DELAY_SECONDS)
        if sync_lead_to_sheet(lead):
            ok += 1
        else:
            failed += 1
    return ok, failed


def sync_all_leads_to_sheet_background(leads: list[dict]) -> None:
    """Run full backfill without blocking the admin request."""
    threading.Thread(
        target=sync_all_leads_to_sheet,
        args=(leads,),
        daemon=True,
        name="sheets-backfill",
    ).start()
