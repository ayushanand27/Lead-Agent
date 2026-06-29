"""Voice search and case-insensitive lead lookup."""

import asyncio

import pytest

from app import db
from app.agent import (
    _extract_search_query,
    _format_search_results,
    _try_search_fast_path,
    handle_message,
)
from app.lead_service import search_leads


def test_extract_search_query_from_phrase():
    assert _extract_search_query("search Priya").lower() == "priya"
    assert _extract_search_query("Search Priya.").lower() == "priya"
    assert "rahul" in _extract_search_query("find lead Rahul").lower()


def test_extract_search_query_voice_name_only():
    assert _extract_search_query("Priya", voice=True) == "Priya"
    assert _extract_search_query("priya mehta", voice=True) == "priya mehta"


def test_search_case_insensitive(isolated_test_env):
    owner = "919111111111"
    db.insert_lead(
        owner_phone=owner,
        name="Priya Mehta",
        phone="9876543210",
        source="LinkedIn",
        status="new",
    )
    result = search_leads(owner, "priya")
    assert result["data"]["count"] == 1
    assert result["data"]["leads"][0]["name"] == "Priya Mehta"


def test_search_fast_path_voice(isolated_test_env):
    owner = "919111111111"
    db.insert_lead(
        owner_phone=owner,
        name="Priya Mehta",
        phone="9876543210",
        source="LinkedIn",
        status="new",
    )
    reply = _try_search_fast_path(owner, "search priya", voice=True)
    assert reply is not None
    assert "Priya Mehta" in reply
    assert "Found 1 lead" in reply


@pytest.mark.parametrize(
    "transcript",
    ["search priya", "Search Priya.", "priya"],
)
def test_handle_message_voice_search(isolated_test_env, transcript):
    owner = "919111111111"
    db.insert_lead(
        owner_phone=owner,
        name="Priya Mehta",
        phone="9876543210",
        source="LinkedIn",
        status="new",
    )
    reply = asyncio.run(
        handle_message(owner, transcript, from_voice=True)
    )
    assert "Priya Mehta" in reply


def test_format_search_results_empty():
    text = _format_search_results(
        {"success": True, "data": {"count": 0, "query": "nobody", "leads": []}}
    )
    assert "No leads found" in text
