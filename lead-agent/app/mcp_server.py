"""MCP server exposing lead-management tools."""

import json

from mcp.server.fastmcp import FastMCP

from app import lead_service
from app.models import (
    GetLeadDetailsInput,
    GetStaleLeadsInput,
    ListLeadsInput,
    SearchLeadsInput,
)

mcp = FastMCP(
    "lead-agent",
    instructions=(
        "Tools for managing sales leads for a WhatsApp-based small business. "
        "Every tool requires owner_phone — the business owner's WhatsApp number."
    ),
)


def _serialize(result: dict) -> str:
    return json.dumps(result, indent=2, default=str)


@mcp.tool(
    name="list_leads",
    description="List all leads for a business owner, optionally filtered by status.",
)
def list_leads(owner_phone: str, status_filter: str | None = None) -> str:
    """Return leads belonging to owner_phone, optionally filtered by status."""
    params = ListLeadsInput(owner_phone=owner_phone, status_filter=status_filter)
    return _serialize(lead_service.list_leads(params.owner_phone, params.status_filter))


@mcp.tool(
    name="get_stale_leads",
    description=(
        "Find leads not contacted in N days. Excludes converted and lost leads."
    ),
)
def get_stale_leads(owner_phone: str, days_since_contact: int = 2) -> str:
    """Return leads that have not been contacted within the given number of days."""
    params = GetStaleLeadsInput(
        owner_phone=owner_phone, days_since_contact=days_since_contact
    )
    return _serialize(
        lead_service.get_stale_leads(params.owner_phone, params.days_since_contact)
    )


@mcp.tool(
    name="search_leads",
    description="Fuzzy search leads by name, phone, source, or notes.",
)
def search_leads(owner_phone: str, query: str) -> str:
    """Search leads matching the query string."""
    params = SearchLeadsInput(owner_phone=owner_phone, query=query)
    return _serialize(lead_service.search_leads(params.owner_phone, params.query))


@mcp.tool(
    name="get_lead_details",
    description="Get the full record for a single lead by ID.",
)
def get_lead_details(owner_phone: str, lead_id: int) -> str:
    """Return detailed information for one lead."""
    params = GetLeadDetailsInput(owner_phone=owner_phone, lead_id=lead_id)
    return _serialize(lead_service.get_lead_details(params.owner_phone, params.lead_id))


if __name__ == "__main__":
    mcp.run()
