"""Lead capture webhook for website forms, IndiaMART Zaps, etc."""

from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app import db
from app.config import get_owner_phones, primary_owner_phone
from app.integrations.sheets import sync_lead_to_sheet
from app.models import LeadStatus
from app.notifications import notify_owners_new_lead

router = APIRouter(tags=["api"])


class LeadCaptureBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: str = Field(..., min_length=5, max_length=30)
    source: str = Field(default="website", max_length=100)
    notes: str | None = Field(default=None, max_length=2000)
    tags: str | None = Field(default=None, max_length=500)
    consent_source: str | None = Field(default="web_form", max_length=100)
    owner_phone: str | None = Field(default=None, max_length=20)


def _default_owner_phone() -> str | None:
    return primary_owner_phone()


def _verify_lead_webhook_secret(request: Request) -> bool:
    secret = os.getenv("LEAD_WEBHOOK_SECRET", "").strip()
    if not secret:
        return False
    provided = request.headers.get("X-Lead-Webhook-Secret", "")
    return bool(provided) and secrets.compare_digest(provided, secret)


async def _after_webhook_lead(lead: dict, source: str) -> None:
    sync_lead_to_sheet(lead)
    await notify_owners_new_lead(lead, channel=source)


@router.post("/leads")
async def capture_lead(
    request: Request,
    body: LeadCaptureBody,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """
    Capture a lead from an external form (website, Zapier, IndiaMART).
    Requires header: X-Lead-Webhook-Secret
    """
    if not _verify_lead_webhook_secret(request):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    owner = (body.owner_phone or _default_owner_phone() or "").strip().lstrip("+")
    if not owner:
        return JSONResponse(
            status_code=400,
            content={"error": "Set BUSINESS_OWNER_PHONES or pass owner_phone."},
        )

    lead_id = db.insert_lead(
        owner_phone=owner,
        name=body.name.strip(),
        phone=body.phone.strip(),
        source=body.source.strip(),
        notes=body.notes.strip() if body.notes else None,
        status=LeadStatus.NEW.value,
        consent_source=body.consent_source.strip() if body.consent_source else None,
        tags=body.tags.strip() if body.tags else None,
    )
    db.log_action(
        owner,
        "lead_created",
        f"Webhook capture: '{body.name.strip()}' (id={lead_id}) from {body.source.strip()}",
    )
    lead = db.fetch_lead_by_id(owner, lead_id)
    if lead:
        background_tasks.add_task(_after_webhook_lead, lead, body.source.strip())

    return JSONResponse(
        status_code=201,
        content={"status": "ok", "lead_id": lead_id, "owner_phone": owner},
    )


@router.get("/leads/health")
async def lead_webhook_health() -> dict[str, Any]:
    configured = bool(os.getenv("LEAD_WEBHOOK_SECRET", "").strip())
    notify = os.getenv("NOTIFY_OWNERS_ON_WEBHOOK", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "status": "ok",
        "webhook_configured": configured,
        "owner_notify_enabled": notify,
        "registered_owners": len(get_owner_phones()),
    }
