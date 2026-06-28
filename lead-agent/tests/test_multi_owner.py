"""Multi-owner shared lead pool tests."""

from __future__ import annotations

import pytest

from app import db, lead_service


@pytest.fixture(autouse=True)
def two_owner_env(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "multi_owner.db"))
    monkeypatch.setenv(
        "BUSINESS_OWNER_PHONES",
        "919111111111,919222222222",
    )
    db.init_db()


def test_partner_sees_leads_created_by_other_owner():
    db.insert_lead(
        owner_phone="919111111111",
        name="Shared Lead",
        phone="919900001111",
        source="Referral",
    )
    result = lead_service.list_leads("919222222222")
    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["leads"][0]["name"] == "Shared Lead"


def test_add_lead_tags_via_service():
    lead_id = db.insert_lead(
        owner_phone="919111111111",
        name="Tagged Lead",
        phone="919900002222",
        source="Test",
    )
    result = lead_service.add_lead_tags("919222222222", lead_id, "site-visit, urgent")
    assert result["success"] is True
    assert "site-visit" in result["data"]["lead"]["tags"]
