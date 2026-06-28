"""Google Sheets backup via Apps Script webhook (no paid API required)."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# GAS web apps rate-limit bursts — small pause between backfill rows
_BACKFILL_DELAY_SECONDS = 0.35


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

    GAS runs doPost on the first POST, then returns 302 to a googleusercontent URL.
    That redirect must be fetched with GET (POST there returns 405).
    """
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "LeadAgent/1.2",
    }
    response = client.post(url, content=body, headers=headers, follow_redirects=False)
    if response.status_code in (301, 302, 303):
        location = response.headers.get("Location")
        if location:
            response = client.get(location, headers={"User-Agent": "LeadAgent/1.2"}, follow_redirects=False)
    return response


def _is_success_response(response: httpx.Response, original_post_status: int | None = None) -> bool:
    if original_post_status in (301, 302, 303):
        return True
    if response.status_code < 400:
        return True
    return False


def sync_lead_to_sheet(lead: dict) -> bool:
    """
    POST lead row to a Google Apps Script web app URL.
    Returns True on success. Never raises — safe to call from agent/webhook paths.
    """
    url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()
    if not url:
        return False

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
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "LeadAgent/1.2",
            }
            post_response = client.post(
                url, content=body, headers=headers, follow_redirects=False
            )
            post_status = post_response.status_code

            if post_status in (301, 302, 303):
                location = post_response.headers.get("Location")
                if location:
                    get_response = client.get(
                        location,
                        headers={"User-Agent": "LeadAgent/1.2"},
                        follow_redirects=False,
                    )
                    if get_response.status_code < 400:
                        logger.info(
                            "Google Sheets sync ok for lead id=%s (POST %s → GET %s)",
                            lead.get("id"),
                            post_status,
                            get_response.status_code,
                        )
                        return True
                logger.info(
                    "Google Sheets sync ok for lead id=%s (POST %s, GAS redirect)",
                    lead.get("id"),
                    post_status,
                )
                return True

            if post_status < 400:
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
    except Exception:
        logger.exception("Google Sheets sync failed for lead id=%s", lead.get("id"))
        return False


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
