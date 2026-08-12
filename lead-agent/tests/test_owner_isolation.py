"""Owner isolation tests — expanded in security checklist phase."""

import pytest

from app import db, lead_service


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_leads.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    db.init_db()
    db.seed_test_leads("919111111111")
    yield


def test_owner_cannot_read_another_owners_lead():
    result = lead_service.get_lead_details("919222222222", lead_id=1)
    assert result["success"] is False


def test_owner_cannot_list_another_owners_leads():
    result = lead_service.list_leads("919222222222")
    assert result["success"] is True
    assert result["data"]["count"] == 0


def test_owner_cannot_search_another_owners_leads():
    result = lead_service.search_leads("919222222222", "Ramesh")
    assert result["success"] is True
    assert result["data"]["count"] == 0


def test_owner_cannot_delete_another_owners_lead():
    result = lead_service.delete_lead("919222222222", lead_id=1)
    assert result["success"] is False

    # Lead A still exists, untouched.
    original_owner_result = lead_service.get_lead_details("919111111111", lead_id=1)
    assert original_owner_result["success"] is True


def test_owner_can_delete_own_lead():
    result = lead_service.delete_lead("919111111111", lead_id=1)
    assert result["success"] is True

    gone = lead_service.get_lead_details("919111111111", lead_id=1)
    assert gone["success"] is False
