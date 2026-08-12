#!/usr/bin/env python3
"""Local smoke test for write tools, action_log, and owner isolation."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_support import configure_test_environment  # noqa: E402

configure_test_environment(ROOT)

from app import db, lead_service  # noqa: E402
from app.pending_actions import (  # noqa: E402
    is_confirmation_message,
    pending_store,
    requires_confirmation,
)

OWNER_A = "919111111111"
OWNER_B = "919222222222"


def pp(label: str, result: dict) -> None:
    print(f"\n{'=' * 60}")
    print(label)
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))


def assert_success(result: dict, label: str) -> dict:
    if not result.get("success"):
        raise AssertionError(f"{label} failed: {result.get('error')}")
    return result["data"]


def main() -> None:
    db_path = db.get_db_path()
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database at {db_path}")

    print("Initializing schema...")
    db.init_db()
    db.seed_test_leads(OWNER_A)

    # 1. Create a new lead
    print("\n--- 1. create_lead ---")
    data = assert_success(
        lead_service.create_lead(
            OWNER_A,
            name="Kavita Rao",
            phone="+919555666777",
            source="Referral",
            notes="Met at trade fair",
        ),
        "create_lead",
    )
    new_lead_id = data["lead_id"]
    print(f"Created lead id={new_lead_id}, name={data['lead']['name']}")

    # 2. Update status
    print("\n--- 2. update_lead_status ---")
    data = assert_success(
        lead_service.update_lead_status(OWNER_A, new_lead_id, "contacted"),
        "update_lead_status",
    )
    print(f"Status updated: {data['old_status']} -> {data['new_status']}")

    # 3. Add a note
    print("\n--- 3. add_lead_note ---")
    data = assert_success(
        lead_service.add_lead_note(
            OWNER_A,
            new_lead_id,
            "Called twice, will follow up Monday",
        ),
        "add_lead_note",
    )
    print(f"Notes now:\n{data['lead']['notes']}")

    # 4. Draft follow-up (mock Groq unless USE_REAL_GROQ=1)
    print("\n--- 4. draft_followup_message ---")
    mock_draft = (
        "Hi Kavita! Just checking in about the products you saw at the trade fair. "
        "Happy to share pricing whenever you're ready."
    )

    if os.getenv("USE_REAL_GROQ") == "1" and os.getenv("GROQ_API_KEY"):
        draft_result = lead_service.draft_followup_message(
            OWNER_A, new_lead_id, tone="friendly"
        )
    else:
        print("Using mocked Groq response (set USE_REAL_GROQ=1 to hit live API)")
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content=mock_draft))
        ]
        with patch("app.lead_service.Groq") as mock_groq:
            mock_groq.return_value.chat.completions.create.return_value = mock_response
            draft_result = lead_service.draft_followup_message(
                OWNER_A, new_lead_id, tone="friendly"
            )

    draft_data = assert_success(draft_result, "draft_followup_message")
    print(f"Draft: {draft_data['draft']}")

    # 5. Verify action_log
    print("\n--- 5. action_log ---")
    log_entries = db.fetch_action_log(OWNER_A)
    actions = [entry["action"] for entry in log_entries]
    print(f"Logged actions ({len(log_entries)}): {actions}")

    expected_actions = {"lead_created", "status_updated", "note_added"}
    missing = expected_actions - set(actions)
    if missing:
        raise AssertionError(f"action_log missing entries: {missing}")

    # PendingActionStore + confirmation helpers
    print("\n--- PendingActionStore ---")
    pending_store.set_pending(
        OWNER_A,
        {
            "action": "send_whatsapp_message",
            "lead_id": new_lead_id,
            "message_text": draft_data["draft"],
        },
    )
    pending = pending_store.get_pending(OWNER_A)
    assert pending is not None and pending["action"] == "send_whatsapp_message"
    assert is_confirmation_message("haan bhej do") is True
    assert is_confirmation_message("maybe later") is False
    assert requires_confirmation("send_whatsapp_message") is True
    assert requires_confirmation("update_lead_status", new_status="converted") is True
    assert requires_confirmation("update_lead_status", new_status="warm") is False
    pending_store.clear_pending(OWNER_A)
    assert pending_store.get_pending(OWNER_A) is None
    print("PendingActionStore and confirmation helpers OK")

    # 6. Owner isolation for writes
    print("\n--- 6. write owner isolation ---")

    isolation_checks = [
        (
            "update_lead_status",
            lead_service.update_lead_status(OWNER_B, new_lead_id, "lost"),
        ),
        (
            "add_lead_note",
            lead_service.add_lead_note(OWNER_B, new_lead_id, "Hacked note"),
        ),
        (
            "send_whatsapp_message",
            lead_service.send_whatsapp_message(
                OWNER_B, new_lead_id, "Unauthorized message"
            ),
        ),
        (
            "delete_lead",
            lead_service.delete_lead(OWNER_B, new_lead_id),
        ),
    ]

    for name, result in isolation_checks:
        assert result["success"] is False, f"{name} should fail for wrong owner"
        print(f"  {name}: blocked for owner B [OK]")

    # Owner A's lead should be unchanged by owner B's attempts
    lead = assert_success(
        lead_service.get_lead_details(OWNER_A, new_lead_id),
        "get_lead_details",
    )["lead"]
    assert lead["status"] == "contacted"
    assert "Hacked note" not in (lead.get("notes") or "")
    print("  Lead data unchanged after failed cross-owner writes [OK]")

    # Optional: send_whatsapp_message with mocked API (no real send)
    print("\n--- send_whatsapp_message (mocked API) ---")
    with patch("app.lead_service._send_via_whatsapp_cloud_api") as mock_send:
        mock_send.return_value = {"success": True, "data": {"api_response": {"ok": True}}}
        send_result = lead_service.send_whatsapp_message(
            OWNER_A,
            new_lead_id,
            "Test follow-up message",
        )
    send_data = assert_success(send_result, "send_whatsapp_message")
    print(f"Message logged for {send_data['message_sent_to']}")
    assert "message_sent" in [e["action"] for e in db.fetch_action_log(OWNER_A)]

    # 7. delete_lead — owner A deletes their own lead
    print("\n--- 7. delete_lead ---")
    delete_data = assert_success(
        lead_service.delete_lead(OWNER_A, new_lead_id), "delete_lead"
    )
    print(f"Deleted lead id={delete_data['deleted_lead_id']} ({delete_data['name']})")
    assert lead_service.get_lead_details(OWNER_A, new_lead_id)["success"] is False
    assert "lead_deleted" in [e["action"] for e in db.fetch_action_log(OWNER_A)]

    print("\nAll write-tool checks passed.")


if __name__ == "__main__":
    main()
