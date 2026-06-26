#!/usr/bin/env python3
"""Integration tests for the Groq agent loop (handle_message)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from app import db, lead_service  # noqa: E402
from app.agent import (  # noqa: E402
    handle_message,
    handle_tool_call_for_test,
    validate_and_prepare_tool,
)
from app.pending_actions import pending_store  # noqa: E402

OWNER = "919111111111"


def safe_print(text: str) -> None:
    """Print without crashing on Windows console encoding."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def require_groq_key() -> None:
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY must be set in .env for this test.")
        sys.exit(1)


def setup_db() -> int:
    db_path = db.get_db_path()
    if db_path.exists():
        db_path.unlink()
    db.init_db()
    db.seed_test_leads(OWNER)

    result = lead_service.create_lead(
        OWNER,
        name="Kavita Rao",
        phone="+919555666777",
        source="Referral",
        notes="Met at trade fair",
    )
    return result["data"]["lead_id"]


async def test_list_leads() -> None:
    print("\n--- Test 1: list all my leads ---")
    reply = await handle_message(OWNER, "list all my leads")
    safe_print(f"Reply:\n{reply}\n")

    lower = reply.lower()
    assert any(
        word in lower for word in ("lead", "leads", "1.", "ramesh", "kavita")
    ), f"Expected a readable lead list, got: {reply!r}"
    print("PASS: readable list returned")


async def test_followup_confirmation(kavita_id: int) -> None:
    print("\n--- Test 2: send a follow up to Kavita ---")
    pending_store.clear_pending(OWNER)

    reply = await handle_message(OWNER, "send a follow up to Kavita")
    safe_print(f"Reply:\n{reply}\n")

    lower = reply.lower()
    assert pending_store.has_pending(OWNER), "Expected a pending send action"
    pending = pending_store.get_pending(OWNER)
    assert pending is not None
    assert pending.get("tool") == "send_whatsapp_message"
    assert pending.get("lead_id") is not None
    assert pending.get("message_text")
    assert any(
        kw in lower or kw in reply.lower()
        for kw in (
            "confirm",
            "yes",
            "reply yes",
            "this will send",
            "whatsapp",
            "भेज",
            "संदेश",
            "क्या",
        )
    ), f"Expected confirmation prompt, got: {reply!r}"
    assert "kavita" in lower, "Expected Kavita's name in confirmation"
    print("PASS: confirmation prompt returned (not sent immediately)")


async def test_confirm_send() -> None:
    print("\n--- Test 3: yes (confirm pending send) ---")
    assert pending_store.has_pending(OWNER), "Test 2 must leave a pending action"

    with patch("app.lead_service._send_via_whatsapp_cloud_api") as mock_send:
        mock_send.return_value = {"success": True, "data": {"api_response": {"ok": True}}}
        reply = await handle_message(OWNER, "yes")

    safe_print(f"Reply:\n{reply}\n")

    assert mock_send.called, "Expected WhatsApp send to be attempted"
    assert not pending_store.has_pending(OWNER), "Pending action should be cleared"
    lower = reply.lower()
    assert any(
        word in lower for word in ("done", "sent", "message")
    ), f"Expected success message, got: {reply!r}"
    print("PASS: send attempted after confirmation")


async def test_gibberish_tool_call() -> None:
    print("\n--- Test 4: gibberish / invalid tool arguments ---")

    # Direct validation: missing lead_id
    _, clarification = validate_and_prepare_tool(
        "send_whatsapp_message",
        '{"message_text": "hello"}',
        OWNER,
    )
    assert clarification is not None
    assert "which lead" in clarification.lower()
    print(f"Missing lead_id -> {clarification}")

    # Direct validation: invalid lead_id type
    _, clarification = validate_and_prepare_tool(
        "update_lead_status",
        '{"lead_id": "not-a-number", "new_status": "warm"}',
        OWNER,
    )
    assert clarification is not None
    assert "which lead" in clarification.lower()
    print(f"Invalid lead_id -> {clarification}")

    # Through handle_tool_call_for_test with garbage JSON
    reply = await handle_tool_call_for_test(
        OWNER,
        "search_leads",
        "not valid json{{{",
    )
    assert "didn't quite catch" in reply.lower() or "rephrase" in reply.lower()
    print(f"Garbage JSON -> {reply}")

    # Invalid status
    _, clarification = validate_and_prepare_tool(
        "update_lead_status",
        f'{{"lead_id": 1, "new_status": "superhot"}}',
        OWNER,
    )
    assert clarification is not None
    assert "status" in clarification.lower() or "valid" in clarification.lower()
    print(f"Invalid status -> {clarification}")

    print("PASS: clarifying questions returned for bad tool calls")


async def main() -> None:
    require_groq_key()
    kavita_id = setup_db()
    print(f"Database ready (Kavita lead id={kavita_id})")

    await test_list_leads()
    await test_followup_confirmation(kavita_id)
    await test_confirm_send()
    await test_gibberish_tool_call()

    print("\nAll agent tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
