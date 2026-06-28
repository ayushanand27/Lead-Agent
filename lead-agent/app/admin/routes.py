"""Owner admin dashboard — leads, activity, CSV export."""

from __future__ import annotations

import csv
import io
import os
from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.admin.auth import (
    dashboard_context,
    get_admin_password,
    get_session_owner,
    login_owner,
    logout_owner,
    require_owner,
)
from app.config import get_business_name, get_industry, get_owner_phones
from app.models import LEAD_STATUS_VALUES

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory="app/templates")

STATUSES = sorted(LEAD_STATUS_VALUES)
STALE_DAYS = int(os.getenv("STALE_LEAD_DAYS", "2"))


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
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
    if not login_owner(request, owner_phone, password):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "Invalid phone or password."},
            status_code=401,
        )
    return RedirectResponse(url="/admin/", status_code=303)


@router.post("/logout")
async def logout(request: Request) -> RedirectResponse:
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
    )
    return templates.TemplateResponse(request, "admin/leads.html", ctx)


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
    )
    return templates.TemplateResponse(request, "admin/settings.html", ctx)
