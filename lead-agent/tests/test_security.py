# Security and API tests

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security.passwords import hash_password, verify_admin_password
from app.security.rate_limit import is_login_blocked, record_login_failure, reset_rate_limits_for_tests


def test_bcrypt_password_roundtrip():
    hashed = hash_password("TestPass123!")
    assert hashed.startswith("$2")
    assert verify_admin_password("TestPass123!", hashed)
    assert not verify_admin_password("wrong", hashed)


def test_plain_password_still_works():
    assert verify_admin_password("secret", "secret")
    assert not verify_admin_password("other", "secret")


def test_login_rate_limit_blocks_after_five():
    reset_rate_limits_for_tests()
    ip = "203.0.113.99"
    for _ in range(5):
        record_login_failure(ip)
    assert is_login_blocked(ip)
    reset_rate_limits_for_tests()


def test_lead_webhook_requires_secret(isolated_test_env, monkeypatch):
    monkeypatch.setenv("LEAD_WEBHOOK_SECRET", "test-lead-secret")
    client = TestClient(app)

    response = client.post(
        "/api/leads",
        json={"name": "Webhook Lead", "phone": "919900001122", "source": "test"},
    )
    assert response.status_code == 403

    response = client.post(
        "/api/leads",
        headers={"X-Lead-Webhook-Secret": "test-lead-secret"},
        json={
            "name": "Webhook Lead",
            "phone": "919900001122",
            "source": "website",
            "consent_source": "unit_test",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "ok"
    assert data["lead_id"] >= 1


def test_security_headers_on_health(isolated_test_env):
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
