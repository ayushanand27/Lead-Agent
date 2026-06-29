"""Groq agent loop — decides which tools to call and handles confirmation flow."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Callable

from groq import Groq
from pydantic import BaseModel, ValidationError

from app import lead_service
from app.lead_service import GROQ_MODEL
from app.models import (
    LEAD_STATUS_VALUES,
    AddLeadNoteInput,
    AddLeadTagsInput,
    CreateLeadInput,
    DraftFollowupMessageInput,
    GetLeadDetailsInput,
    GetStaleLeadsInput,
    ListLeadsInput,
    SearchLeadsInput,
    SendWhatsappMessageInput,
    UpdateLeadStatusInput,
)
from app.config import build_system_prompt, is_registered_owner
from app.pending_actions import is_confirmation_message, pending_store, requires_confirmation
from app.text_normalize import romanize_query

logger = logging.getLogger(__name__)

GENERIC_ERROR_REPLY = (
    "Sorry, I'm having trouble right now. Please try again in a moment."
)
CANCELLED_PREFIX = "Previous action cancelled. Processing your new request...\n\n"
WELCOME_REPLY = (
    "Hi! I'm LeadAgent — your WhatsApp lead assistant.\n\n"
    "Try:\n"
    "• list all my leads\n"
    "• 2 din se contact nahi hua kaun?\n"
    "• add lead Rahul phone 9876543210 from website\n"
    "• search Priya\n"
    "• mark Rahul as warm\n\n"
    "Hindi ya English — jo aapko easy lage."
)
_GREETINGS = frozenset({
    "hi", "hello", "hey", "hii", "hiii", "yo", "namaste", "namaskar", "start", "help",
    "hlo", "hlw", "helo", "hola", "gm", "sup", "hiiii",
})
_MAX_GREETING_WORDS = 4


def _is_greeting(text: str) -> bool:
    """Match hi/hello even with punctuation, emoji-adjacent text, or short extras."""
    cleaned = re.sub(r"[^\w\s]", " ", text.strip().lower())
    normalized = " ".join(cleaned.split())
    if not normalized:
        return False
    if normalized in _GREETINGS:
        return True
    words = normalized.split()
    if words[0] in _GREETINGS and len(words) <= _MAX_GREETING_WORDS:
        return True
    return False
MAX_AGENT_ITERATIONS = 8

# OpenAI-compatible tool schemas (owner_phone is injected server-side, not by the model)
# Optional fields use nullable types — Groq rejects null for non-nullable schema properties.
GROQ_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_leads",
            "description": "List all leads, optionally filtered by status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Optional: new, contacted, warm, hot, converted, lost",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stale_leads",
            "description": "Leads not contacted in N days (excludes converted/lost).",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_since_contact": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "description": "Days since last contact (default 2)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_leads",
            "description": "Search leads by name, phone, source, or notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_lead_details",
            "description": "Get full details for one lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer", "description": "Lead ID"},
                },
                "required": ["lead_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": "Create a new lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "source": {"type": "string"},
                    "notes": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": ["name", "phone", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_lead_status",
            "description": "Update a lead's status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer"},
                    "new_status": {
                        "type": "string",
                        "description": "new, contacted, warm, hot, converted, lost",
                    },
                },
                "required": ["lead_id", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_lead_note",
            "description": "Append a note to a lead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer"},
                    "note": {"type": "string"},
                },
                "required": ["lead_id", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_lead_tags",
            "description": "Add comma-separated tags to a lead (e.g. site-visit, urgent).",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer"},
                    "tags": {"type": "string"},
                },
                "required": ["lead_id", "tags"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_followup_message",
            "description": "Draft a follow-up WhatsApp message (does not send).",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer"},
                    "tone": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                        "description": "friendly, formal, or urgent",
                    },
                },
                "required": ["lead_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Send a WhatsApp message to a lead (requires owner confirmation).",
            "parameters": {
                "type": "object",
                "properties": {
                    "lead_id": {"type": "integer"},
                    "message_text": {"type": "string"},
                },
                "required": ["lead_id", "message_text"],
            },
        },
    },
]

ToolExecutor = Callable[[str, dict[str, Any]], dict]

TOOL_REGISTRY: dict[str, tuple[type[BaseModel], ToolExecutor]] = {
    "list_leads": (
        ListLeadsInput,
        lambda owner, args: lead_service.list_leads(
            owner, args.get("status_filter")
        ),
    ),
    "get_stale_leads": (
        GetStaleLeadsInput,
        lambda owner, args: lead_service.get_stale_leads(
            owner, args.get("days_since_contact", 2)
        ),
    ),
    "search_leads": (
        SearchLeadsInput,
        lambda owner, args: lead_service.search_leads(owner, args["query"]),
    ),
    "get_lead_details": (
        GetLeadDetailsInput,
        lambda owner, args: lead_service.get_lead_details(owner, args["lead_id"]),
    ),
    "create_lead": (
        CreateLeadInput,
        lambda owner, args: lead_service.create_lead(
            owner,
            args["name"],
            args["phone"],
            args["source"],
            args.get("notes"),
        ),
    ),
    "update_lead_status": (
        UpdateLeadStatusInput,
        lambda owner, args: lead_service.update_lead_status(
            owner, args["lead_id"], args["new_status"]
        ),
    ),
    "add_lead_note": (
        AddLeadNoteInput,
        lambda owner, args: lead_service.add_lead_note(
            owner, args["lead_id"], args["note"]
        ),
    ),
    "add_lead_tags": (
        AddLeadTagsInput,
        lambda owner, args: lead_service.add_lead_tags(
            owner, args["lead_id"], args["tags"]
        ),
    ),
    "draft_followup_message": (
        DraftFollowupMessageInput,
        lambda owner, args: lead_service.draft_followup_message(
            owner,
            args["lead_id"],
            args.get("tone", "friendly"),
        ),
    ),
    "send_whatsapp_message": (
        SendWhatsappMessageInput,
        lambda owner, args: lead_service.send_whatsapp_message(
            owner, args["lead_id"], args["message_text"]
        ),
    ),
}


def _get_groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def _parse_tool_arguments(raw: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if not raw:
        return None, "I didn't quite catch the details — could you say that again?"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, "I didn't quite catch the details — could you say that again?"
    if not isinstance(parsed, dict):
        return None, "I didn't quite catch the details — could you say that again?"
    return parsed, None


def _validation_clarification(tool_name: str, args: dict[str, Any], exc: ValidationError) -> str:
    lead_id_missing = any(
        err.get("loc") == ("lead_id",) for err in exc.errors()
    )
    if lead_id_missing or "lead_id" not in args:
        return "Which lead do you mean? Please give me the name."

    for err in exc.errors():
        loc = err.get("loc", ())
        if "new_status" in loc:
            options = ", ".join(sorted(LEAD_STATUS_VALUES))
            return f"That status isn't valid. Please use one of: {options}."
        if err.get("type") == "value_error" and "new_status" in str(err.get("loc", "")):
            options = ", ".join(sorted(LEAD_STATUS_VALUES))
            return f"That status isn't valid. Please use one of: {options}."

    if tool_name == "search_leads":
        return "What should I search for? Give me a name, phone number, or keyword."

    return "I didn't quite catch that — could you rephrase?"


def validate_and_prepare_tool(
    tool_name: str,
    raw_arguments: str | None,
    owner_phone: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate tool name and arguments. Returns (validated_args, clarification)."""
    if tool_name not in TOOL_REGISTRY:
        return None, "I'm not sure how to do that. Could you rephrase?"

    args, parse_error = _parse_tool_arguments(raw_arguments)
    if parse_error:
        return None, parse_error

    args = dict(args or {})
    args["owner_phone"] = owner_phone

    # Drop null optional fields so Pydantic defaults apply
    args = {k: v for k, v in args.items() if v is not None}

    if tool_name in {
        "get_lead_details",
        "update_lead_status",
        "add_lead_note",
        "add_lead_tags",
        "draft_followup_message",
        "send_whatsapp_message",
    }:
        lead_id = args.get("lead_id")
        if lead_id is None:
            return None, "Which lead do you mean? Please give me the name."
        try:
            args["lead_id"] = int(lead_id)
        except (TypeError, ValueError):
            return None, "Which lead do you mean? Please give me the name."

    schema_cls, _ = TOOL_REGISTRY[tool_name]
    try:
        validated = schema_cls.model_validate(args)
    except ValidationError as exc:
        return None, _validation_clarification(tool_name, args, exc)

    return validated.model_dump(), None


def _pending_tool_name(pending: dict[str, Any]) -> str:
    return str(pending.get("tool") or pending.get("action") or "")


def _store_pending_send(
    owner_phone: str,
    lead_id: int,
    message_text: str,
    *,
    lead_name: str | None = None,
    lead_phone: str | None = None,
) -> None:
    pending_store.set_pending(
        owner_phone,
        {
            "tool": "send_whatsapp_message",
            "lead_id": lead_id,
            "message_text": message_text,
            "lead_name": lead_name,
            "lead_phone": lead_phone,
        },
    )


def _is_send_confirmation_question(text: str) -> bool:
    """True when the assistant reply is asking the owner to confirm sending."""
    if not text.strip():
        return False

    lower = text.lower()
    markers = (
        "send this",
        "send it",
        "shall i send",
        "should i send",
        "want me to send",
        "reply yes",
        "this will send",
        "confirm",
        "go ahead and send",
        "whatsapp",
        "भेज",
        "संदेश",
        "क्या मैं",
        "bhej do",
        "bhej du",
    )
    if any(marker in lower or marker in text for marker in markers):
        return True

    # Question mark plus send-related wording
    if "?" in text or "？" in text:
        return any(
            word in lower or word in text
            for word in ("send", "message", "whatsapp", "भेज", "संदेश")
        )

    return False


def _extract_draft_from_reply(text: str) -> str | None:
    """Pull a drafted message out of the assistant's confirmation reply."""
    for pattern in (
        r"\*([^*]+)\*",  # *italic draft*
        r"\"([^\"]+)\"",  # "quoted draft"
        r"「([^」]+)」",
    ):
        match = re.search(pattern, text, re.DOTALL)
        if match:
            candidate = match.group(1).strip()
            if len(candidate) > 10:
                return candidate
    return None


def _maybe_store_pending_after_draft_reply(
    owner_phone: str,
    reply: str,
    *,
    draft_tool_used: bool,
    last_draft_result: dict | None,
    last_lead: dict | None,
) -> None:
    """Store pending send when a draft was produced and the reply asks to confirm."""
    if not _is_send_confirmation_question(reply):
        return

    if draft_tool_used and last_draft_result and last_draft_result.get("success"):
        _store_pending_from_draft_result(owner_phone, last_draft_result)
        return

    if last_lead is None:
        return

    draft_text = _extract_draft_from_reply(reply)
    if not draft_text and last_draft_result and last_draft_result.get("success"):
        draft_text = last_draft_result["data"].get("draft")

    if draft_text:
        _store_pending_send(
            owner_phone,
            last_lead["id"],
            draft_text,
            lead_name=last_lead.get("name"),
            lead_phone=last_lead.get("phone"),
        )


def _store_pending_from_draft_result(owner_phone: str, draft_result: dict) -> None:
    if not draft_result.get("success"):
        return
    data = draft_result["data"]
    _store_pending_send(
        owner_phone,
        data["lead_id"],
        data["draft"],
        lead_name=data.get("lead_name"),
        lead_phone=data.get("lead_phone"),
    )


def _build_send_confirmation(owner_phone: str, args: dict[str, Any]) -> str:
    lead = lead_service.get_lead_details(owner_phone, args["lead_id"])
    if not lead.get("success"):
        return "I couldn't find that lead. Which lead do you mean? Please give me the name."

    lead_data = lead["data"]["lead"]
    name = lead_data["name"]
    phone = lead_data["phone"]
    message = args["message_text"]

    _store_pending_send(
        owner_phone,
        args["lead_id"],
        message,
        lead_name=name,
        lead_phone=phone,
    )
    return (
        f"This will send:\n\"{message}\"\n\n"
        f"to {name} ({phone}).\n\n"
        "Reply YES to confirm, or tell me what to change."
    )


def _build_status_confirmation(owner_phone: str, args: dict[str, Any]) -> str:
    lead = lead_service.get_lead_details(owner_phone, args["lead_id"])
    if not lead.get("success"):
        return "I couldn't find that lead. Which lead do you mean? Please give me the name."

    lead_data = lead["data"]["lead"]
    name = lead_data["name"]
    new_status = args["new_status"]

    pending_store.set_pending(
        owner_phone,
        {
            "tool": "update_lead_status",
            "lead_id": args["lead_id"],
            "new_status": new_status,
            "lead_name": name,
        },
    )
    return (
        f"This will mark {name} as {new_status}.\n\n"
        "Reply YES to confirm, or tell me to cancel."
    )


def _extract_lead_name_hint(message_text: str) -> str | None:
    """Pull a likely lead name from phrases like 'to Kavita' or 'for Ramesh'."""
    patterns = (
        r"(?:send|bhej)\s+(?:a\s+)?(?:follow[\s-]?up|message)\s+(?:to|for)\s+([A-Za-z][A-Za-z\s]{0,30})",
        r"(?:follow[\s-]?up|message|text|whatsapp|bhej(?:\s+do)?)\s+(?:to|for)\s+([A-Za-z][A-Za-z\s]{0,30})",
        r"(?:to|for)\s+([A-Za-z][A-Za-z\s]{0,30})(?:\s+on whatsapp|\s+via whatsapp|\s*$)",
    )
    for pattern in patterns:
        match = re.search(pattern, message_text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name:
                return name.split()[0]  # first name token
    return None


def _try_send_followup_fast_path(owner_phone: str, message_text: str) -> str | None:
    """
    Handle clear 'send follow-up to {name}' requests without waiting on Groq tone questions.
    Calls draft_followup_message and stores pending send action.
    """
    if not _user_wants_outbound_message(message_text):
        return None

    name_hint = _extract_lead_name_hint(message_text)
    if not name_hint:
        return None

    search = lead_service.search_leads(owner_phone, name_hint)
    if not search.get("success") or search["data"]["count"] == 0:
        return None

    lead = search["data"]["leads"][0]
    draft = lead_service.draft_followup_message(
        owner_phone, lead["id"], tone="friendly"
    )

    if draft.get("success"):
        message_text = draft["data"]["draft"]
    else:
        message_text = (
            f"Hi {lead['name']}, hope you're doing well! "
            "Just wanted to follow up — let me know if you have any questions."
        )

    _store_pending_send(
        owner_phone,
        lead["id"],
        message_text,
        lead_name=lead.get("name"),
        lead_phone=lead.get("phone"),
    )
    return (
        f"Here's a follow-up draft for {lead['name']}:\n\n"
        f"\"{message_text}\"\n\n"
        f"This will send to {lead['name']} ({lead['phone']}).\n"
        "Reply YES to confirm, or tell me what to change."
    )


def _user_wants_outbound_message(text: str) -> bool:
    """True when the owner likely wants to send a message to a lead."""
    lower = text.lower()
    keywords = (
        "send",
        "follow up",
        "follow-up",
        "followup",
        "bhej",
        "bhej do",
        "message karo",
        "msg",
        "text them",
        "whatsapp",
    )
    return any(k in lower for k in keywords)


_SEARCH_INTENT_WORDS = (
    "search",
    "find",
    "lookup",
    "dhoondo",
    "dhundho",
    "dhundo",
    "khojo",
    "khoj",
)

_VOICE_NAME_SKIP_WORDS = frozenset({
    "yes", "no", "ok", "okay", "hi", "hello", "hey", "thanks", "thank", "please",
    "list", "add", "mark", "send", "the", "a", "an", "my", "all", "leads", "lead",
    "who", "what", "when", "how", "stale", "converted", "lost", "warm", "hot", "new",
})

_SEARCH_BLOCK_PHRASES = (
    "add lead",
    "create lead",
    "list all",
    "mark ",
    "haven't i contacted",
    "contact nahi",
)


def _has_search_intent(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in _SEARCH_INTENT_WORDS)


def _extract_search_query(message_text: str, *, voice: bool = False) -> str | None:
    """Pull a searchable name/keyword from chat or voice transcripts."""
    text = message_text.strip()
    if not text:
        return None

    normalized = re.sub(r"[^\w\s\-'.]", " ", text)
    normalized = " ".join(normalized.split())
    lower = normalized.lower()

    prefix_patterns = (
        r"^search(?:\s+for)?\s+(.+)$",
        r"^find(?:\s+lead)?\s+(.+)$",
        r"^lookup\s+(.+)$",
        r"^show(?:\s+me)?(?:\s+lead)?\s+(.+)$",
        r"^get(?:\s+lead)?\s+(.+)$",
        r"^(?:dhoondo|dhundho|dhundo|khojo|khoj)\s+(.+)$",
        r"^(.+?)\s+(?:ko\s+)?(?:dhoondo|dhundho|dhundo|khojo)$",
        r"^(.+?)\s+ki\s+search$",
    )
    for pattern in prefix_patterns:
        match = re.match(pattern, lower, re.IGNORECASE)
        if match:
            query = match.group(1).strip(" .,!?:;")
            if query:
                return query

    latin_tokens = re.findall(r"[A-Za-z]{2,}", normalized)
    if latin_tokens:
        if _has_search_intent(lower):
            if latin_tokens[0].lower() in {"search", "find", "lookup", "show", "get"}:
                latin_tokens = latin_tokens[1:]
            if latin_tokens:
                return " ".join(latin_tokens)
        if voice and len(latin_tokens) <= 3:
            if latin_tokens[0].lower() not in _VOICE_NAME_SKIP_WORDS:
                return " ".join(latin_tokens)

    return None


def _format_search_results(result: dict) -> str:
    if not result.get("success"):
        return "Search failed. Please try again in a moment."

    data = result["data"]
    count = int(data.get("count", 0))
    query = data.get("query", "")
    if count == 0:
        return f'No leads found for "{query}".'

    lines = [f'Found {count} lead(s) for "{query}":']
    for lead in data.get("leads", [])[:10]:
        lines.append(
            f"• {lead['name']} — {lead['phone']} ({lead['status']}, {lead['source']})"
        )
    if count > 10:
        lines.append(f"...and {count - 10} more.")
    return "\n".join(lines)


def _format_list_results(result: dict) -> str:
    if not result.get("success"):
        return "Couldn't load leads. Please try again."

    leads = result["data"].get("leads", [])
    count = int(result["data"].get("count", len(leads)))
    if count == 0:
        return "You have no leads yet."

    lines = [f"Here are your {count} lead(s):\n"]
    for index, lead in enumerate(leads[:20], start=1):
        lines.append(
            f"{index}. {lead['name']} — {lead['phone']} — "
            f"{lead['source']} — {lead['status']}"
        )
    if count > 20:
        lines.append(f"\n...and {count - 20} more.")
    return "\n".join(lines)


def _format_stale_results(result: dict) -> str:
    if not result.get("success"):
        return "Couldn't check stale leads. Please try again."

    data = result["data"]
    days = int(data.get("days_since_contact", 2))
    count = int(data.get("count", 0))
    if count == 0:
        return f"No stale leads — everyone was contacted within the last {days} days."

    lines = [f"Leads not contacted in {days}+ days ({count}):\n"]
    for index, lead in enumerate(data.get("leads", [])[:15], start=1):
        lines.append(
            f"{index}. {lead['name']} — {lead['phone']} — {lead['status']}"
        )
    return "\n".join(lines)


def _format_create_lead_result(result: dict) -> str:
    if not result.get("success"):
        return result.get("error") or "Couldn't add that lead. Please try again."
    lead = result["data"]["lead"]
    return (
        f"Done! Added {lead['name']} ({lead['phone']}) from {lead['source']}."
    )


_DIRECT_REPLY_TOOLS: dict[str, Any] = {
    "list_leads": _format_list_results,
    "search_leads": _format_search_results,
    "get_stale_leads": _format_stale_results,
    "create_lead": _format_create_lead_result,
}


def _try_search_fast_path(
    owner_phone: str,
    message_text: str,
    *,
    voice: bool = False,
) -> str | None:
    """Direct DB search — reliable for voice transcripts and short name lookups."""
    lower = message_text.lower()
    if any(phrase in lower for phrase in _SEARCH_BLOCK_PHRASES):
        return None

    query = _extract_search_query(message_text, voice=voice)
    if not query:
        return None

    result = lead_service.search_leads(owner_phone, query)
    return _format_search_results(result)


_CREATE_LEAD_RE = re.compile(
    r"add\s+lead\s+(.+?)\s+phone\s+([+\d][\d\s]{4,})\s+from\s+(.+)",
    re.IGNORECASE,
)

_STATUS_UPDATE_RE = re.compile(
    r"mark\s+(.+?)\s+as\s+(new|contacted|warm|hot|converted|lost)\b",
    re.IGNORECASE,
)


def _try_list_fast_path(owner_phone: str, message_text: str) -> str | None:
    lower = message_text.lower()
    if not re.search(r"\blist\b", lower) or not re.search(r"\bleads?\b", lower):
        return None
    return _format_list_results(lead_service.list_leads(owner_phone))


def _try_stale_fast_path(owner_phone: str, message_text: str) -> str | None:
    lower = message_text.lower()
    stale_hints = (
        "stale",
        "haven't i contacted",
        "have not contacted",
        "not contacted",
        "contact nahi",
        "follow-up pending",
        "follow up pending",
    )
    if not any(hint in lower for hint in stale_hints):
        return None

    days = 2
    match = re.search(r"(\d+)\s*(?:din|days?)", lower)
    if match:
        days = max(1, int(match.group(1)))

    return _format_stale_results(lead_service.get_stale_leads(owner_phone, days))


def _try_create_lead_fast_path(owner_phone: str, message_text: str) -> str | None:
    match = _CREATE_LEAD_RE.search(message_text.strip())
    if not match:
        return None
    name, phone, source = match.group(1).strip(), match.group(2).strip(), match.group(3).strip()
    phone = re.sub(r"[\s\-]", "", phone)
    result = lead_service.create_lead(owner_phone, name, phone, source)
    return _format_create_lead_result(result)


def _try_status_update_fast_path(owner_phone: str, message_text: str) -> str | None:
    match = _STATUS_UPDATE_RE.search(message_text.strip())
    if not match:
        return None
    name_hint, new_status = match.group(1).strip(), match.group(2).lower()
    search = lead_service.search_leads(owner_phone, name_hint)
    if not search.get("success") or search["data"]["count"] == 0:
        return f'No lead found matching "{name_hint}".'

    lead = search["data"]["leads"][0]
    if requires_confirmation("update_lead_status", new_status=new_status):
        pending_store.set_pending(
            owner_phone,
            {
                "tool": "update_lead_status",
                "lead_id": lead["id"],
                "new_status": new_status,
                "lead_name": lead["name"],
            },
        )
        return (
            f"This will mark {lead['name']} as {new_status}.\n\n"
            "Reply YES to confirm, or tell me to cancel."
        )

    result = lead_service.update_lead_status(owner_phone, lead["id"], new_status)
    if result.get("success"):
        return f"Done! {lead['name']} is now marked as {new_status}."
    return result.get("error") or "Couldn't update that lead."


def _remember_lead_from_tool_result(
    tool_name: str, tool_output: str, last_lead: dict | None
) -> dict | None:
    try:
        parsed = json.loads(tool_output)
    except json.JSONDecodeError:
        return last_lead

    if not parsed.get("success"):
        return last_lead

    if tool_name == "get_lead_details":
        return parsed["data"]["lead"]

    if tool_name == "search_leads":
        leads = parsed["data"].get("leads", [])
        if leads:
            return leads[0]

    if tool_name == "draft_followup_message":
        data = parsed["data"]
        return {
            "id": data["lead_id"],
            "name": data.get("lead_name"),
            "phone": data.get("lead_phone"),
        }

    return last_lead


def execute_validated_tool(
    owner_phone: str,
    tool_name: str,
    args: dict[str, Any],
    *,
    user_message: str = "",
) -> tuple[str, bool]:
    """
    Execute or queue a validated tool call.
    Returns (reply_text, stop_loop). stop_loop=True means return reply directly to owner.
    """
    if tool_name == "send_whatsapp_message" and requires_confirmation("send_whatsapp_message"):
        return _build_send_confirmation(owner_phone, args), True

    if tool_name == "update_lead_status" and requires_confirmation(
        "update_lead_status", new_status=args.get("new_status")
    ):
        return _build_status_confirmation(owner_phone, args), True

    _, executor = TOOL_REGISTRY[tool_name]
    result = executor(owner_phone, args)

    if tool_name == "draft_followup_message" and result.get("success"):
        _store_pending_from_draft_result(owner_phone, result)

    formatter = _DIRECT_REPLY_TOOLS.get(tool_name)
    if formatter is not None:
        return formatter(result), True

    return json.dumps(result, default=str), False


def _format_pending_success(
    owner_phone: str, pending: dict[str, Any], result: dict
) -> str:
    tool = _pending_tool_name(pending)
    name = pending.get("lead_name", "the lead")

    if not result.get("success"):
        return (
            "I couldn't complete that action. Please try again in a moment."
        )

    if tool == "send_whatsapp_message":
        phone = pending.get("lead_phone", "")
        if not phone and pending.get("lead_id"):
            lead = lead_service.get_lead_details(owner_phone, pending["lead_id"])
            if lead.get("success"):
                phone = lead["data"]["lead"].get("phone", "")
                name = lead["data"]["lead"].get("name", name)
        return f"Done! Message sent to {name} ({phone})."

    if tool == "update_lead_status":
        status = pending.get("new_status", "")
        return f"Done! {name} is now marked as {status}."

    return "Done!"


def _execute_pending_action(owner_phone: str, pending: dict[str, Any]) -> dict:
    tool = _pending_tool_name(pending)

    if tool == "send_whatsapp_message":
        return lead_service.send_whatsapp_message(
            owner_phone,
            pending["lead_id"],
            pending["message_text"],
        )

    if tool == "update_lead_status":
        return lead_service.update_lead_status(
            owner_phone,
            pending["lead_id"],
            pending["new_status"],
        )

    return {"success": False, "error": "Unknown pending action"}


def _is_rate_limit_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status == 429:
        return True
    message = str(exc).lower()
    return "rate" in message and "limit" in message


async def _call_groq(
    client: Groq,
    messages: list[dict[str, Any]],
    *,
    retried: bool = False,
) -> Any:
    def _request() -> Any:
        return client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=GROQ_TOOLS,
            tool_choice="auto",
            temperature=0.3,
            max_tokens=1024,
        )

    try:
        return await asyncio.to_thread(_request)
    except Exception as exc:
        if _is_rate_limit_error(exc) and not retried:
            await asyncio.sleep(2)
            return await _call_groq(client, messages, retried=True)
        logger.exception("Groq API call failed")
        raise


async def _run_agent_loop(owner_phone: str, message_text: str) -> str:
    client = _get_groq_client()
    if client is None:
        return GENERIC_ERROR_REPLY

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": message_text},
    ]
    last_draft_result: dict | None = None
    draft_tool_used = False
    last_lead: dict | None = None

    try:
        for _ in range(MAX_AGENT_ITERATIONS):
            response = await _call_groq(client, messages)
            assistant_message = response.choices[0].message

            if not assistant_message.tool_calls:
                content = (assistant_message.content or "").strip()
                if not pending_store.has_pending(owner_phone):
                    _maybe_store_pending_after_draft_reply(
                        owner_phone,
                        content,
                        draft_tool_used=draft_tool_used,
                        last_draft_result=last_draft_result,
                        last_lead=last_lead,
                    )
                return content or "How can I help with your leads today?"

            # Append assistant turn with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
            )

            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                validated_args, clarification = validate_and_prepare_tool(
                    tool_name,
                    tool_call.function.arguments,
                    owner_phone,
                )

                if clarification:
                    return clarification

                assert validated_args is not None
                tool_output, stop_loop = execute_validated_tool(
                    owner_phone,
                    tool_name,
                    validated_args,
                    user_message=message_text,
                )

                if stop_loop:
                    return tool_output

                if tool_name == "draft_followup_message":
                    draft_tool_used = True
                    try:
                        parsed = json.loads(tool_output)
                        if parsed.get("success"):
                            last_draft_result = parsed
                    except json.JSONDecodeError:
                        pass

                last_lead = _remember_lead_from_tool_result(
                    tool_name, tool_output, last_lead
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_output,
                    }
                )

        return "I need a bit more back-and-forth to finish that. Could you try a simpler request?"
    except Exception:
        return GENERIC_ERROR_REPLY


async def handle_message(
    owner_phone: str,
    message_text: str,
    *,
    from_voice: bool = False,
) -> str:
    """
    Process an incoming WhatsApp message from a business owner.
    Returns plain-text reply to send back on WhatsApp.
    """
    text = (message_text or "").strip()
    if from_voice and text:
        text = romanize_query(text)
    if not text:
        return "Send me a message about your leads — e.g. 'list all my leads' or 'who haven't I called in 2 days?'"

    if not is_registered_owner(owner_phone):
        return "This number is not registered for this business account. Please contact your administrator."

    if _is_greeting(text):
        return WELCOME_REPLY

    pending = pending_store.get_pending(owner_phone)
    if pending is not None:
        if is_confirmation_message(text):
            pending_store.clear_pending(owner_phone)
            result = _execute_pending_action(owner_phone, pending)
            return _format_pending_success(owner_phone, pending, result)

        pending_store.clear_pending(owner_phone)
        reply = await _run_agent_loop(owner_phone, text)
        return f"{CANCELLED_PREFIX}{reply}"

    fast_path = _try_list_fast_path(owner_phone, text)
    if fast_path is not None:
        return fast_path

    stale_path = _try_stale_fast_path(owner_phone, text)
    if stale_path is not None:
        return stale_path

    create_path = _try_create_lead_fast_path(owner_phone, text)
    if create_path is not None:
        return create_path

    status_path = _try_status_update_fast_path(owner_phone, text)
    if status_path is not None:
        return status_path

    search_path = _try_search_fast_path(owner_phone, text, voice=from_voice)
    if search_path is not None:
        return search_path

    followup_path = _try_send_followup_fast_path(owner_phone, text)
    if followup_path is not None:
        return followup_path

    return await _run_agent_loop(owner_phone, text)


# Exposed for unit tests (gibberish tool-call scenario)
async def handle_tool_call_for_test(
    owner_phone: str,
    tool_name: str,
    raw_arguments: str | None,
) -> str:
    """Validate and handle a single tool call; returns reply text."""
    validated_args, clarification = validate_and_prepare_tool(
        tool_name, raw_arguments, owner_phone
    )
    if clarification:
        return clarification
    assert validated_args is not None
    reply, _ = execute_validated_tool(owner_phone, tool_name, validated_args)
    return reply
