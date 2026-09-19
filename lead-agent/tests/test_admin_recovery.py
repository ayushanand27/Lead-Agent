"""Admin password recovery flow."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from app.security.passwords import verify_admin_password
from app.security.rate_limit import reset_rate_limits_for_tests


def test_recover_generates_bcrypt_hash(isolated_test_env, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "cron-test-secret")
    reset_rate_limits_for_tests()
    client = TestClient(app)

    response = client.post(
        "/admin/recover",
        data={
            "recovery_secret": "cron-test-secret",
            "new_password": "NewSecure1!",
        },
        follow_redirects=False,
    )
    assert response.status_code == 200
    body = response.text
    match = re.search(r"ADMIN_DASHBOARD_PASSWORD=(\$2[^\s<]+)", body)
    assert match is not None
    assert verify_admin_password("NewSecure1!", match.group(1))


def test_recover_rejects_bad_secret(isolated_test_env, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "cron-test-secret")
    reset_rate_limits_for_tests()
    client = TestClient(app)

    response = client.post(
        "/admin/recover",
        data={"recovery_secret": "wrong", "new_password": "NewSecure1!"},
    )
    assert response.status_code == 403


def test_ops_status_requires_secret(isolated_test_env, monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "cron-test-secret")
    client = TestClient(app)
    assert client.get("/internal/ops/status").status_code == 403
    ok = client.get("/internal/ops/status?secret=cron-test-secret")
    assert ok.status_code == 200
    data = ok.json()
    assert "database" in data
    assert data["admin_password_configured"] is True
