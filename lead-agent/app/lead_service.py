"""Lead operations used by MCP tools and the agent loop."""

import os
from datetime import datetime, timezone
from typing import Any

import httpx
from groq import Groq

from app import db
from app.integrations.sheets import sync_lead_to_sheet_background
from app.models import LEAD_STATUS_VALUES, LeadStatus

GROQ_MODEL = "openai/gpt-oss-120b"
WHATSAPP_GRAPH_API_VERSION = "v21.0"


def _tool_result(success: bool, data: Any = None, error: str | None = None) -> dict:
    result: dict[str, Any] = {"success": success}
    if data is not None:
        result["data"] = data
    if error is not None:
        result["error"] = error
    return result


def _validate_status(status: str) -> str | None:
    if status not in LEAD_STATUS_VALUES:
        return f"Invalid status '{status}'. Allowed: {sorted(LEAD_STATUS_VALUES)}"
    return None


def _require_lead(owner_phone: str, lead_id: int) -> tuple[dict | None, dict | None]:
    lead = db.fetch_lead_by_id(owner_phone, lead_id)
    if lead is None:
        return None, _tool_result(
            success=False,
            error=f"No lead found with id={lead_id} for this owner.",
        )
    return lead, None


def _format_note_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _sync_lead(owner_phone: str, lead_id: int) -> None:
    lead = db.fetch_lead_by_id(owner_phone, lead_id)
    if lead:
        sync_lead_to_sheet_background(lead)


def _normalize_whatsapp_recipient(phone: str) -> str:
    return phone.strip().lstrip("+")


# --- Read tools ---


def list_leads(owner_phone: str, status_filter: str | None = None) -> dict:
    if status_filter is not None:
        status_error = _validate_status(status_filter)
        if status_error:
            return _tool_result(success=False, error=status_error)
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
    lead, error = _require_lead(owner_phone, lead_id)
    if error:
        return error
    return _tool_result(success=True, data={"lead": lead})


# --- Write tools ---


def create_lead(
    owner_phone: str,
    name: str,
    phone: str,
    source: str,
    notes: str | None = None,
) -> dict:
    lead_id = db.insert_lead(
        owner_phone=owner_phone,
        name=name.strip(),
        phone=phone.strip(),
        source=source.strip(),
        notes=notes.strip() if notes else None,
        status=LeadStatus.NEW.value,
    )
    db.log_action(
        owner_phone,
        "lead_created",
        f"Created lead '{name.strip()}' (id={lead_id}) from {source.strip()}",
    )
    lead = db.fetch_lead_by_id(owner_phone, lead_id)
    _sync_lead(owner_phone, lead_id)
    return _tool_result(success=True, data={"lead": lead, "lead_id": lead_id})


def update_lead_status(owner_phone: str, lead_id: int, new_status: str) -> dict:
    status_error = _validate_status(new_status)
    if status_error:
        return _tool_result(success=False, error=status_error)

    lead, error = _require_lead(owner_phone, lead_id)
    if error:
        return error

    old_status = lead["status"]
    if not db.update_lead_status(owner_phone, lead_id, new_status):
        return _tool_result(
            success=False,
            error=f"Failed to update lead id={lead_id}.",
        )

    db.log_action(
        owner_phone,
        "status_updated",
        f"Lead '{lead['name']}' (id={lead_id}) status: {old_status} → {new_status}",
    )
    updated = db.fetch_lead_by_id(owner_phone, lead_id)
    _sync_lead(owner_phone, lead_id)
    return _tool_result(
        success=True,
        data={"lead": updated, "old_status": old_status, "new_status": new_status},
    )


def add_lead_note(owner_phone: str, lead_id: int, note: str) -> dict:
    lead, error = _require_lead(owner_phone, lead_id)
    if error:
        return error

    note_text = note.strip()
    if not note_text:
        return _tool_result(success=False, error="Note cannot be empty.")

    timestamped = f"[{_format_note_timestamp()}] {note_text}"
    if not db.append_lead_note(owner_phone, lead_id, timestamped):
        return _tool_result(
            success=False,
            error=f"Failed to add note to lead id={lead_id}.",
        )

    db.log_action(
        owner_phone,
        "note_added",
        f"Added note to lead '{lead['name']}' (id={lead_id}): {note_text}",
    )
    updated = db.fetch_lead_by_id(owner_phone, lead_id)
    _sync_lead(owner_phone, lead_id)
    return _tool_result(success=True, data={"lead": updated})


def add_lead_tags(owner_phone: str, lead_id: int, tags: str) -> dict:
    lead, error = _require_lead(owner_phone, lead_id)
    if error:
        return error

    tag_text = tags.strip()
    if not tag_text:
        return _tool_result(success=False, error="Tags cannot be empty.")

    if not db.append_lead_tags(owner_phone, lead_id, tag_text):
        return _tool_result(success=False, error=f"Failed to add tags to lead id={lead_id}.")

    db.log_action(
        owner_phone,
        "tags_added",
        f"Added tags to lead '{lead['name']}' (id={lead_id}): {tag_text}",
    )
    updated = db.fetch_lead_by_id(owner_phone, lead_id)
    _sync_lead(owner_phone, lead_id)
    return _tool_result(success=True, data={"lead": updated})


def draft_followup_message(
    owner_phone: str,
    lead_id: int,
    tone: str = "friendly",
) -> dict:
    lead, error = _require_lead(owner_phone, lead_id)
    if error:
        return error

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _tool_result(
            success=False,
            error="GROQ_API_KEY is not configured.",
        )

    prompt = (
        f"Draft a short WhatsApp follow-up message for a sales lead.\n"
        f"Lead name: {lead['name']}\n"
        f"Source: {lead['source']}\n"
        f"Status: {lead['status']}\n"
        f"Notes: {lead.get('notes') or 'None'}\n"
        f"Tone: {tone}\n\n"
        "Write only the message text — no quotes, labels, or explanation. "
        "Keep it under 300 characters. Use simple Hindi-English mix if natural."
    )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You draft concise WhatsApp sales follow-up messages for "
                        "Indian small businesses. Output only the message body."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.7,
        )
        draft = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        return _tool_result(
            success=False,
            error=f"Failed to generate draft: {exc}",
        )

    if not draft:
        return _tool_result(
            success=False,
            error="Groq returned an empty draft.",
        )

    return _tool_result(
        success=True,
        data={
            "lead_id": lead_id,
            "lead_name": lead["name"],
            "lead_phone": lead["phone"],
            "tone": tone,
            "draft": draft,
        },
    )


def _send_via_whatsapp_cloud_api(to_phone: str, message_text: str) -> dict:
    token = os.getenv("WHATSAPP_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not token or not phone_number_id:
        return _tool_result(
            success=False,
            error="WHATSAPP_TOKEN or WHATSAPP_PHONE_NUMBER_ID is not configured.",
        )

    url = (
        f"https://graph.facebook.com/{WHATSAPP_GRAPH_API_VERSION}/"
        f"{phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalize_whatsapp_recipient(to_phone),
        "type": "text",
        "text": {"body": message_text},
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:200] if exc.response is not None else str(exc)
        return _tool_result(
            success=False,
            error=f"WhatsApp API error: {detail}",
        )
    except Exception as exc:
        return _tool_result(
            success=False,
            error=f"Failed to send WhatsApp message: {exc}",
        )

    return _tool_result(success=True, data={"api_response": body})


def send_whatsapp_message(
    owner_phone: str,
    lead_id: int,
    message_text: str,
) -> dict:
    lead, error = _require_lead(owner_phone, lead_id)
    if error:
        return error

    text = message_text.strip()
    if not text:
        return _tool_result(success=False, error="Message text cannot be empty.")

    send_result = _send_via_whatsapp_cloud_api(lead["phone"], text)
    if not send_result["success"]:
        return send_result

    if not db.update_last_contacted_at(owner_phone, lead_id):
        return _tool_result(
            success=False,
            error=f"Message sent but failed to update last_contacted_at for lead id={lead_id}.",
        )

    db.log_action(
        owner_phone,
        "message_sent",
        f"Sent WhatsApp to '{lead['name']}' ({lead['phone']}, id={lead_id}): {text[:120]}",
    )
    updated = db.fetch_lead_by_id(owner_phone, lead_id)
    _sync_lead(owner_phone, lead_id)
    return _tool_result(
        success=True,
        data={
            "lead": updated,
            "message_sent_to": lead["phone"],
            "message_text": text,
        },
    )
