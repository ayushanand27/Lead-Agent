"""Tests for analytics and source queries."""

from app import db


def test_fetch_lead_sources_empty():
    db.init_db()
    owner = "919999999999"
    assert db.fetch_lead_sources(owner) == []


def test_fetch_analytics_empty():
    db.init_db()
    owner = "919999999999"
    data = db.fetch_analytics(owner, days=14)
    assert data["total"] == 0
    assert data["conversion_rate"] == 0
    assert data["by_status"] == {}
    assert data["by_source"] == {}
    assert data["leads_by_day"] == []
