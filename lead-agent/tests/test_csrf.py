"""CSRF protection on authenticated admin dashboard forms."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app import db
from app.main import app

OWNER = "919111111111"
PASSWORD = "test-admin-password"


def _logged_in_client() -> TestClient:
    client = TestClient(app)
    response = client.post(
        "/admin/login",
        data={"owner_phone": OWNER, "password": PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "csrf_token hidden field not found in rendered page"
    return match.group(1)


def test_edit_lead_rejected_without_csrf_token(isolated_test_env):
    lead_id = db.insert_lead(
        owner_phone=OWNER, name="Kavita", phone="9000000000", source="X", status="new"
    )
    client = _logged_in_client()

    response = client.post(
        f"/admin/leads/{lead_id}/edit",
        data={"status": "converted", "notes": "", "tags": ""},
        follow_redirects=False,
    )
    assert response.status_code == 303

    lead = db.fetch_lead_by_id(OWNER, lead_id)
    assert lead["status"] == "new"  # unchanged


def test_edit_lead_succeeds_with_valid_csrf_token(isolated_test_env):
    lead_id = db.insert_lead(
        owner_phone=OWNER, name="Kavita", phone="9000000000", source="X", status="new"
    )
    client = _logged_in_client()

    edit_page = client.get(f"/admin/leads/{lead_id}/edit")
    token = _extract_csrf_token(edit_page.text)

    response = client.post(
        f"/admin/leads/{lead_id}/edit",
        data={"status": "converted", "notes": "", "tags": "", "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303

    lead = db.fetch_lead_by_id(OWNER, lead_id)
    assert lead["status"] == "converted"


def test_logout_rejected_without_csrf_token_keeps_session():
    client = _logged_in_client()

    client.post("/admin/logout", follow_redirects=False)

    # Session should still be active — the forged logout was ignored.
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 200


def test_logout_succeeds_with_valid_csrf_token():
    client = _logged_in_client()

    dashboard = client.get("/admin/")
    token = _extract_csrf_token(dashboard.text)

    client.post("/admin/logout", data={"csrf_token": token}, follow_redirects=False)

    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 303  # bounced to login — session cleared


def test_dashboard_delete_rejected_without_csrf_token(isolated_test_env):
    lead_id = db.insert_lead(
        owner_phone=OWNER, name="Kavita", phone="9000000000", source="X", status="new"
    )
    client = _logged_in_client()

    client.post(f"/admin/leads/{lead_id}/delete", follow_redirects=False)

    assert db.fetch_lead_by_id(OWNER, lead_id) is not None  # still there


def test_dashboard_delete_succeeds_with_valid_csrf_token(isolated_test_env):
    lead_id = db.insert_lead(
        owner_phone=OWNER, name="Kavita", phone="9000000000", source="X", status="new"
    )
    client = _logged_in_client()

    edit_page = client.get(f"/admin/leads/{lead_id}/edit")
    token = _extract_csrf_token(edit_page.text)

    response = client.post(
        f"/admin/leads/{lead_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "deleted=1" in response.headers["location"]

    assert db.fetch_lead_by_id(OWNER, lead_id) is None
    actions = [e["action"] for e in db.fetch_action_log(OWNER)]
    assert "lead_deleted" in actions


def test_dashboard_cannot_delete_another_owners_lead(isolated_test_env):
    other_owner_lead_id = db.insert_lead(
        owner_phone="919222222222", name="Not Mine", phone="9000000001", source="X", status="new"
    )
    client = _logged_in_client()

    dashboard = client.get("/admin/")
    token = _extract_csrf_token(dashboard.text)

    client.post(
        f"/admin/leads/{other_owner_lead_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )

    assert db.fetch_lead_by_id("919222222222", other_owner_lead_id) is not None
