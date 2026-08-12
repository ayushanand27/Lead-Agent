"""MCP server exposing lead-management tools."""

import json

from mcp.server.fastmcp import FastMCP

from app import lead_service
from app.models import (
    AddLeadNoteInput,
    AddLeadTagsInput,
    CreateLeadInput,
    DeleteLeadInput,
    DraftFollowupMessageInput,
    GetLeadDetailsInput,
    GetStaleLeadsInput,
    ListLeadsInput,
    SearchLeadsInput,
    SendWhatsappMessageInput,
    UpdateLeadStatusInput,
)

mcp = FastMCP(
    "lead-agent",
    instructions=(
        "Tools for managing sales leads for a WhatsApp-based small business. "
        "Every tool requires owner_phone — the business owner's WhatsApp number. "
        "Write tools that send messages, mark leads converted/lost, or delete a lead "
        "require owner confirmation in the agent loop before execution."
    ),
)


def _serialize(result: dict) -> str:
    return json.dumps(result, indent=2, default=str)


# --- Read tools ---


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


# --- Write tools ---


@mcp.tool(
    name="create_lead",
    description="Create a new lead for the business owner.",
)
def create_lead(
    owner_phone: str,
    name: str,
    phone: str,
    source: str,
    notes: str | None = None,
) -> str:
    """Add a new lead with status 'new'."""
    params = CreateLeadInput(
        owner_phone=owner_phone,
        name=name,
        phone=phone,
        source=source,
        notes=notes,
    )
    return _serialize(
        lead_service.create_lead(
            params.owner_phone,
            params.name,
            params.phone,
            params.source,
            params.notes,
        )
    )


@mcp.tool(
    name="update_lead_status",
    description="Update a lead's status. Terminal states (converted, lost) need confirmation in the agent loop.",
)
def update_lead_status(owner_phone: str, lead_id: int, new_status: str) -> str:
    """Change lead status to a valid enum value."""
    params = UpdateLeadStatusInput(
        owner_phone=owner_phone,
        lead_id=lead_id,
        new_status=new_status,
    )
    return _serialize(
        lead_service.update_lead_status(
            params.owner_phone,
            params.lead_id,
            params.new_status,
        )
    )


@mcp.tool(
    name="add_lead_note",
    description="Append a timestamped note to a lead.",
)
def add_lead_note(owner_phone: str, lead_id: int, note: str) -> str:
    """Add a note to an existing lead."""
    params = AddLeadNoteInput(owner_phone=owner_phone, lead_id=lead_id, note=note)
    return _serialize(
        lead_service.add_lead_note(params.owner_phone, params.lead_id, params.note)
    )


@mcp.tool(
    name="add_lead_tags",
    description="Add comma-separated tags to a lead (e.g. site-visit, urgent, noida).",
)
def add_lead_tags(owner_phone: str, lead_id: int, tags: str) -> str:
    """Append tags to a lead."""
    params = AddLeadTagsInput(owner_phone=owner_phone, lead_id=lead_id, tags=tags)
    return _serialize(
        lead_service.add_lead_tags(params.owner_phone, params.lead_id, params.tags)
    )


@mcp.tool(
    name="delete_lead",
    description=(
        "Permanently delete a lead and its notes/history. Irreversible — the agent loop "
        "must obtain owner confirmation before calling this tool."
    ),
)
def delete_lead(owner_phone: str, lead_id: int) -> str:
    """Permanently remove a lead."""
    params = DeleteLeadInput(owner_phone=owner_phone, lead_id=lead_id)
    return _serialize(lead_service.delete_lead(params.owner_phone, params.lead_id))


@mcp.tool(
    name="draft_followup_message",
    description="Draft a WhatsApp follow-up message for a lead using Groq. Does NOT send the message.",
)
def draft_followup_message(
    owner_phone: str,
    lead_id: int,
    tone: str = "friendly",
) -> str:
    """Generate follow-up message text for owner review."""
    params = DraftFollowupMessageInput(
        owner_phone=owner_phone,
        lead_id=lead_id,
        tone=tone,
    )
    return _serialize(
        lead_service.draft_followup_message(
            params.owner_phone,
            params.lead_id,
            params.tone,
        )
    )


@mcp.tool(
    name="send_whatsapp_message",
    description=(
        "Send a WhatsApp message to a lead via Meta Cloud API. "
        "Agent loop must obtain owner confirmation before calling this tool."
    ),
)
def send_whatsapp_message(
    owner_phone: str,
    lead_id: int,
    message_text: str,
) -> str:
    """Send message to lead and update last_contacted_at."""
    params = SendWhatsappMessageInput(
        owner_phone=owner_phone,
        lead_id=lead_id,
        message_text=message_text,
    )
    return _serialize(
        lead_service.send_whatsapp_message(
            params.owner_phone,
            params.lead_id,
            params.message_text,
        )
    )


if __name__ == "__main__":
    mcp.run()
