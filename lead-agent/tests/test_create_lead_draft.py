"""Multi-turn add-lead flow (WhatsApp context)."""

import asyncio

from app import db
from app.agent import handle_message
from app.pending_actions import pending_store


def _owner() -> str:
    return "919111111111"


def test_add_lead_without_phone_then_phone_number(isolated_test_env):
    owner = _owner()
    pending_store.clear_pending(owner)

    reply1 = asyncio.run(
        handle_message(owner, "add lead aryan from muj without phone no")
    )
    assert "phone number" in reply1.lower()

    reply2 = asyncio.run(handle_message(owner, "89076968382"))
    assert "Done! Added Aryan" in reply2 or "Done! Added aryan" in reply2
    assert "89076968382" in reply2

    search = asyncio.run(handle_message(owner, "search aryan"))
    assert "Found" in search and "aryan" in search.lower()


def test_save_name_source_for_this_phone(isolated_test_env):
    owner = _owner()
    pending_store.clear_pending(owner)

    reply1 = asyncio.run(
        handle_message(owner, "save aryan muj for this phone no")
    )
    assert "phone number" in reply1.lower()

    reply2 = asyncio.run(handle_message(owner, "89076968383"))
    assert "89076968383" in reply2
    assert "Done!" in reply2


def test_add_lead_loose_format_without_phone_keyword(isolated_test_env):
    owner = _owner()
    pending_store.clear_pending(owner)
    reply = asyncio.run(
        handle_message(owner, "add lead Demo Person 9876501234 from website")
    )
    assert "Done! Added Demo Person" in reply


def test_add_lead_name_phone_then_source_in_followup(isolated_test_env):
    owner = _owner()
    pending_store.clear_pending(owner)

    reply1 = asyncio.run(
        handle_message(owner, "add lead Priya Test 9876509999")
    )
    assert "source" in reply1.lower()

    reply2 = asyncio.run(handle_message(owner, "Instagram"))
    assert "Done! Added Priya Test" in reply2
