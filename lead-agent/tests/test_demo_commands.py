"""Demo script commands — fast paths must work without Groq."""

import asyncio

from app import db
from app.agent import handle_message


def _seed_priya(owner: str) -> None:
    db.insert_lead(
        owner_phone=owner,
        name="Priya Mittal",
        phone="9087654321",
        source="X",
        status="new",
    )


def test_demo_list_leads(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    reply = asyncio.run(handle_message(owner, "list all my leads"))
    assert "Priya Mittal" in reply


def test_demo_search_priya(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    reply = asyncio.run(handle_message(owner, "search priya"))
    assert "Priya Mittal" in reply
    assert "Found 1 lead" in reply


def test_demo_search_full_name(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    reply = asyncio.run(handle_message(owner, "search priya mittal"))
    assert "Priya Mittal" in reply


def test_demo_add_lead(isolated_test_env):
    owner = "919111111111"
    reply = asyncio.run(
        handle_message(
            owner,
            "add lead Demo User phone 9876543210 from LinkedIn",
        )
    )
    assert "Done! Added Demo User" in reply


def test_demo_stale_query(isolated_test_env):
    owner = "919111111111"
    reply = asyncio.run(
        handle_message(owner, "who haven't I contacted in 2 days?")
    )
    assert "stale" in reply.lower() or "contacted" in reply.lower()


def test_demo_mark_converted_prompt(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    reply = asyncio.run(
        handle_message(owner, "mark Priya Mittal as converted")
    )
    assert "YES to confirm" in reply
    assert "Priya Mittal" in reply


def test_voice_search_hindi_transcript(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    reply = asyncio.run(
        handle_message(owner, "प्रिया मित्तल", from_voice=True)
    )
    assert "Priya Mittal" in reply


def test_demo_delete_lead_prompt(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    reply = asyncio.run(handle_message(owner, "delete Priya Mittal"))
    assert "YES to confirm" in reply
    assert "permanently delete" in reply.lower()
    assert "Priya Mittal" in reply

    # Not deleted yet — still present until the owner confirms.
    leads = db.fetch_leads_for_owner(owner)
    assert any(lead["name"] == "Priya Mittal" for lead in leads)


def test_demo_delete_lead_confirmed(isolated_test_env):
    owner = "919111111111"
    _seed_priya(owner)
    prompt = asyncio.run(handle_message(owner, "delete Priya Mittal"))
    assert "YES to confirm" in prompt

    confirmed = asyncio.run(handle_message(owner, "YES"))
    assert "permanently deleted" in confirmed.lower()
    assert "Priya Mittal" in confirmed

    listing = asyncio.run(handle_message(owner, "list all my leads"))
    assert "Priya Mittal" not in listing
