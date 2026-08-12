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
from app.integrations.sheets import (
    is_sheets_sync_enabled,
    sync_all_leads_to_sheet_background,
    sync_lead_to_sheet_background,
)
from app.models import LEAD_STATUS_VALUES
from app.security.audit import log_admin_event
from app.security.csrf import verify_csrf_token
from app.security.ip_allowlist import is_ip_allowed
from app.security.rate_limit import (
    clear_login_failures,
    is_login_blocked,
    record_login_failure,
)
from app.security.request_info import get_client_ip
from app.utils.formatting import mask_phone

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
templates.env.filters["mask_phone"] = mask_phone

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

    from app.utils.phone import normalize_owner_phone

    normalized = normalize_owner_phone(owner_phone)

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
        # Helpful without leaking which field failed to strangers on shared demos
        allowed = get_owner_phones()
        if allowed and normalized and normalized not in set(allowed):
            hint = "Phone not registered. Use your WhatsApp number with country code (e.g. 91…)."
        else:
            hint = "Invalid phone or password. Check Render ADMIN_DASHBOARD_PASSWORD if it still fails."
        log_admin_event(
            normalized or "unknown",
            "admin_login_failed",
            f"Invalid credentials from {client_ip}",
        )
        return _login_error(request, hint)

    clear_login_failures(client_ip)
    log_admin_event(normalized, "admin_login_success", f"Signed in from {client_ip}")
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/logout")
async def logout(request: Request, csrf_token: str = Form(None)) -> RedirectResponse:
    owner = get_session_owner(request)
    if owner and not verify_csrf_token(request, csrf_token):
        return _redirect_login()
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
    converted = stats["by_status"].get("converted", 0)
    conversion_rate = round((converted / stats["total"] * 100) if stats["total"] else 0, 1)
    stale = db.fetch_stale_leads(owner, STALE_DAYS)
    ctx = dashboard_context(
        request,
        active_page="dashboard",
        stats=stats,
        conversion_rate=conversion_rate,
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
    source: str | None = None,
) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if q:
        leads = db.search_leads_for_owner(owner, q)
    else:
        leads = db.fetch_leads_for_owner(
            owner,
            status_filter=status or None,
            source_filter=source or None,
        )
    if status and q:
        leads = [lead for lead in leads if lead.get("status") == status]
    if source and q:
        leads = [lead for lead in leads if lead.get("source") == source]

    ctx = dashboard_context(
        request,
        active_page="leads",
        leads=leads,
        query=q,
        status_filter=status,
        source_filter=source,
        sources=db.fetch_lead_sources(owner),
        statuses=STATUSES,
        sheets_sync_enabled=is_sheets_sync_enabled(),
        sync_message=request.query_params.get("sync"),
        deleted=request.query_params.get("deleted"),
    )
    return templates.TemplateResponse(request, "admin/leads.html", ctx)


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, days: int = 14) -> HTMLResponse:
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    days = max(7, min(days, 90))
    analytics = db.fetch_analytics(owner, days=days)
    ctx = dashboard_context(
        request,
        active_page="analytics",
        analytics=analytics,
    )
    return templates.TemplateResponse(request, "admin/analytics.html", ctx)


@router.post("/leads/sync-sheets", response_model=None)
async def sync_leads_to_sheets(request: Request, csrf_token: str = Form(None)):
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url="/admin/leads", status_code=303)
    if not is_sheets_sync_enabled():
        return RedirectResponse(url="/admin/leads?sync=not_configured", status_code=303)

    leads = db.fetch_leads_for_owner(owner)
    sync_all_leads_to_sheet_background(leads)
    log_admin_event(
        owner,
        "sheets_backfill",
        f"Started background sync of {len(leads)} leads to Google Sheets",
    )
    return RedirectResponse(
        url=f"/admin/leads?sync=started&count={len(leads)}",
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
    csrf_token: str = Form(None),
):
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url=f"/admin/leads/{lead_id}/edit", status_code=303)
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
        sync_lead_to_sheet_background(updated)
    return RedirectResponse(url="/admin/leads", status_code=303)


@router.post("/leads/{lead_id}/delete", response_model=None)
async def delete_lead_submit(
    request: Request,
    lead_id: int,
    csrf_token: str = Form(None),
):
    if not get_session_owner(request):
        return _redirect_login()
    owner = require_owner(request)
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url=f"/admin/leads/{lead_id}/edit", status_code=303)

    lead = db.fetch_lead_by_id(owner, lead_id)
    if not lead:
        return RedirectResponse(url="/admin/leads", status_code=303)

    db.delete_lead(owner, lead_id)
    db.log_action(
        owner,
        "lead_deleted",
        f"Dashboard delete: '{lead['name']}' ({lead['phone']}, id={lead_id})",
    )
    return RedirectResponse(url="/admin/leads?deleted=1", status_code=303)
    if updated:
        sync_lead_to_sheet_background(updated)
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
    if phones:
        owners_label = f"{len(phones)} account{'s' if len(phones) != 1 else ''} configured"
    else:
        owners_label = "Any WhatsApp number"
    ctx = dashboard_context(
        request,
        active_page="settings",
        owner_phones_display=owners_label,
        sheets_sync_enabled=bool(os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "").strip()),
        lead_webhook_enabled=bool(os.getenv("LEAD_WEBHOOK_SECRET", "").strip()),
        production_mode=is_production(),
        db_connected=db.check_connection(),
        cron_configured=bool(os.getenv("CRON_SECRET", "").strip()),
        app_base_url=str(request.base_url).rstrip("/"),
    )
    return templates.TemplateResponse(request, "admin/settings.html", ctx)
