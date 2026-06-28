"""Owner admin dashboard — leads, activity, CSV export."""

from __future__ import annotations

import csv
import io
import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.admin.auth import (
    dashboard_context,
    get_admin_password,
    get_session_owner,
    is_production,
    login_owner,
    logout_owner,
    require_owner,
)
from app.config import get_owner_phones
from app.integrations.sheets import is_sheets_sync_enabled, sync_all_leads_to_sheet, sync_lead_to_sheet
from app.models import LEAD_STATUS_VALUES
from app.security.audit import log_admin_event
from app.security.ip_allowlist import is_ip_allowed
from app.security.rate_limit import (
    clear_login_failures,
    is_login_blocked,
    record_login_failure,
)
from app.security.request_info import get_client_ip

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

STATUSES = sorted(LEAD_STATUS_VALUES)
STALE_DAYS = int(os.getenv("STALE_LEAD_DAYS", "2"))


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=303)


def _login_error(request: Request, message: str, status_code: int = 401):
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"error": message},
        status_code=status_code,
    )


def _guard_admin_ip(request: Request) -> RedirectResponse | None:
    if not is_ip_allowed(get_client_ip(request)):
        return _login_error(
            request,
            "Dashboard access is not allowed from this network.",
            status_code=403,
        )
    return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    blocked = _guard_admin_ip(request)
    if blocked:
        return blocked
    if get_session_owner(request):
        return RedirectResponse(url="/admin/", status_code=303)
    if not get_admin_password():
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "Admin dashboard is not configured (set ADMIN_DASHBOARD_PASSWORD)."},
        )
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login", response_model=None)
async def login_submit(
    request: Request,
    owner_phone: str = Form(...),
    password: str = Form(...),
):
    client_ip = get_client_ip(request)
    blocked = _guard_admin_ip(request)
    if blocked:
        return blocked

    normalized = owner_phone.strip().lstrip("+")

    if is_login_blocked(client_ip):
        log_admin_event(
            normalized or "unknown",
            "admin_login_blocked",
            f"Rate limit exceeded from {client_ip}",
        )
        return _login_error(
            request,
            "Too many failed attempts. Try again in 15 minutes.",
            status_code=429,
        )

    if not login_owner(request, owner_phone, password):
        record_login_failure(client_ip)
        log_admin_event(
            normalized or "unknown",
            "admin_login_failed",
            f"Invalid credentials from {client_ip}",
        )
        return _login_error(request, "Invalid phone or password.")

    clear_login_failures(client_ip)
    log_admin_event(normalized, "admin_login_success", f"Signed in from {client_ip}")
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
    owner = get_session_owner(request)
    if owner:
        log_admin_event(owner, "admin_logout", f"Signed out from {get_client_ip(request)}")
    logout_owner(request)
    return _redirect_login()


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    stats = db.fetch_lead_stats(owner)
    stale = db.fetch_stale_leads(owner, STALE_DAYS)
    ctx = dashboard_context(
        request,
        active_page="dashboard",
        stats=stats,
        stale_count=len(stale),
        stale_days=STALE_DAYS,
        recent_activity=db.fetch_action_log(owner, limit=8),
    )
    return templates.TemplateResponse(request, "admin/dashboard.html", ctx)


@router.get("/leads", response_class=HTMLResponse)
async def leads_page(
    request: Request,
    q: str | None = None,
    status: str | None = None,
) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if q:
        leads = db.search_leads_for_owner(owner, q)
    else:
        leads = db.fetch_leads_for_owner(owner, status_filter=status or None)
    if status and q:
        leads = [lead for lead in leads if lead.get("status") == status]

    ctx = dashboard_context(
        request,
        active_page="leads",
        leads=leads,
        query=q,
        status_filter=status,
        statuses=STATUSES,
        sheets_sync_enabled=is_sheets_sync_enabled(),
        sync_message=request.query_params.get("sync"),
    )
    return templates.TemplateResponse(request, "admin/leads.html", ctx)


@router.post("/leads/sync-sheets", response_model=None)
async def sync_leads_to_sheets(request: Request):
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if not is_sheets_sync_enabled():
        return RedirectResponse(url="/admin/leads?sync=not_configured", status_code=303)

    leads = db.fetch_leads_for_owner(owner)
    ok, failed = sync_all_leads_to_sheet(leads)
    log_admin_event(
        owner,
        "sheets_backfill",
        f"Synced {ok} leads to Google Sheets ({failed} failed)",
    )
    return RedirectResponse(
        url=f"/admin/leads?sync=ok&count={ok}&failed={failed}",
        status_code=303,
    )


@router.get("/leads/{lead_id}/edit", response_class=HTMLResponse)
async def edit_lead_page(request: Request, lead_id: int) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    lead = db.fetch_lead_by_id(owner, lead_id)
    if not lead:
        return RedirectResponse(url="/admin/leads", status_code=303)
    ctx = dashboard_context(
        request,
        active_page="leads",
        lead=lead,
        statuses=STATUSES,
    )
    return templates.TemplateResponse(request, "admin/lead_edit.html", ctx)


@router.post("/leads/{lead_id}/edit", response_model=None)
async def edit_lead_submit(
    request: Request,
    lead_id: int,
    status: str = Form(...),
    notes: str = Form(""),
    tags: str = Form(""),
):
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    lead = db.fetch_lead_by_id(owner, lead_id)
    if not lead:
        return RedirectResponse(url="/admin/leads", status_code=303)

    if status not in LEAD_STATUS_VALUES:
        return RedirectResponse(url=f"/admin/leads/{lead_id}/edit?error=status", status_code=303)

    db.update_lead_fields(
        owner,
        lead_id,
        status=status,
        notes=notes.strip() or None,
        tags=tags.strip() or None,
    )
    db.log_action(owner, "lead_updated", f"Dashboard edit lead id={lead_id} status={status}")
    updated = db.fetch_lead_by_id(owner, lead_id)
    if updated:
        sync_lead_to_sheet(updated)
    return RedirectResponse(url="/admin/leads", status_code=303)


@router.get("/leads/export", response_model=None)
async def export_leads(request: Request, q: str | None = None):
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if q:
        leads = db.search_leads_for_owner(owner, q)
    else:
        leads = db.fetch_leads_for_owner(owner)

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "id",
            "name",
            "phone",
            "source",
            "status",
            "notes",
            "tags",
            "consent_source",
            "consent_at",
            "last_contacted_at",
            "created_at",
        ],
    )
    writer.writeheader()
    for lead in leads:
        writer.writerow({k: lead.get(k, "") for k in writer.fieldnames})

    buffer.seek(0)
    filename = f"leads-{owner}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/activity", response_class=HTMLResponse)
async def activity_page(request: Request) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    ctx = dashboard_context(
        request,
        active_page="activity",
        activity=db.fetch_action_log(owner, limit=100),
    )
    return templates.TemplateResponse(request, "admin/activity.html", ctx)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    phones = get_owner_phones()
    ctx = dashboard_context(
        request,
        active_page="settings",
        owner_phones_display=", ".join(phones) if phones else "(any WhatsApp number)",
        sheets_sync_enabled=bool(os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()),
        lead_webhook_enabled=bool(os.getenv("LEAD_WEBHOOK_SECRET", "").strip()),
        production_mode=is_production(),
    )
    return templates.TemplateResponse(request, "admin/settings.html", ctx)
