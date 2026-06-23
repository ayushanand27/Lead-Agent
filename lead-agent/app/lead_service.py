"""Lead read operations used by MCP tools and the agent loop."""

from typing import Any

from app import db
from app.models import LEAD_STATUS_VALUES


def _tool_result(success: bool, data: Any = None, error: str | None = None) -> dict:
    result: dict[str, Any] = {"success": success}
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    return result


def list_leads(owner_phone: str, status_filter: str | None = None) -> dict:
    if status_filter is not None and status_filter not in LEAD_STATUS_VALUES:
        return _tool_result(
            success=False,
            error=f"Invalid status '{status_filter}'. Allowed: {sorted(LEAD_STATUS_VALUES)}",
        )
    leads = db.fetch_leads_for_owner(owner_phone, status_filter)
    return _tool_result(success=True, data={"leads": leads, "count": len(leads)})


def get_stale_leads(owner_phone: str, days_since_contact: int = 2) -> dict:
    leads = db.fetch_stale_leads(owner_phone, days_since_contact)
    return _tool_result(
        success=True,
        data={
            "leads": leads,
            "count": len(leads),
            "days_since_contact": days_since_contact,
        },
    )


def search_leads(owner_phone: str, query: str) -> dict:
    leads = db.search_leads_for_owner(owner_phone, query)
    return _tool_result(
        success=True,
        data={"leads": leads, "count": len(leads), "query": query},
    )


def get_lead_details(owner_phone: str, lead_id: int) -> dict:
    lead = db.fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return _tool_result(
            success=False,
            error=f"No lead found with id={lead_id} for this owner.",
        )
    return _tool_result(success=True, data={"lead": lead})
