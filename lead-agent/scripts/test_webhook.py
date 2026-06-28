#!/usr/bin/env python3
"""Local tests for FastAPI webhook routes (Meta verification + signature)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_support import configure_test_environment  # noqa: E402

configure_test_environment(ROOT)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

APP_SECRET = os.environ["WHATSAPP_APP_SECRET"]
VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]


def sign_body(body: bytes) -> str:
    digest = hmac.new(APP_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def sample_webhook_payload(owner_phone: str = "919111111111", text: str = "hello") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "123456789",
                            },
                            "messages": [
                                {
                                    "from": owner_phone,
                                    "id": "wamid.test",
                                    "timestamp": "1710000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def main() -> None:
    from app import db

    db_file = Path(os.environ["DATABASE_PATH"])
    if db_file.exists():
        db_file.unlink()
    db.init_db()

    client = TestClient(app)

    # 1. GET /webhook verification
    print("\n--- Test 1: GET /webhook verification ---")
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "challenge_token_12345",
        },
    )
    assert response.status_code == 200, response.text
    assert response.text == "challenge_token_12345"
    print("PASS: challenge returned")

    # 2. POST /webhook with valid signature
    print("\n--- Test 2: POST /webhook valid signature ---")
    payload = sample_webhook_payload(text="list all my leads")
    body = json.dumps(payload).encode("utf-8")

    with (
        patch("app.main.handle_message", new_callable=AsyncMock) as mock_handle,
        patch("app.main.send_whatsapp_reply", new_callable=AsyncMock) as mock_send,
    ):
        mock_handle.return_value = "Here are your leads."
        mock_send.return_value = True

        response = client.post(
            "/webhook",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sign_body(body),
            },
        )

    assert response.status_code == 200, response.text
    mock_handle.assert_awaited_once_with("919111111111", "list all my leads")
    mock_send.assert_awaited_once_with("919111111111", "Here are your leads.")
    print("PASS: valid webhook returns 200 and routes to agent")

    # 3. POST /webhook with invalid signature
    print("\n--- Test 3: POST /webhook invalid signature ---")
    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=invalidsignature",
        },
    )
    assert response.status_code == 403, response.text
    print("PASS: invalid signature returns 403")

    # 4. POST non-text message skipped with 200
    print("\n--- Test 4: POST non-text message skipped ---")
    status_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": "wamid.test",
                                    "status": "delivered",
                                    "timestamp": "1710000000",
                                }
                            ]
                        },
                        "field": "messages",
                    }
                ]
            }
        ]
    }
    status_body = json.dumps(status_payload).encode("utf-8")

    with patch("app.main.handle_message", new_callable=AsyncMock) as mock_handle:
        response = client.post(
            "/webhook",
            content=status_body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sign_body(status_body),
            },
        )

    assert response.status_code == 200
    mock_handle.assert_not_called()
    print("PASS: status update skipped with 200")

    # 5. GET /health
    print("\n--- Test 5: GET /health ---")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["timestamp"], int)
    assert data["database"] == "connected"
    print("PASS: health check ok")

    # 6. GET /health/ready
    print("\n--- Test 6: GET /health/ready ---")
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    print("PASS: readiness check ok")

    # 7. Admin login + dashboard
    print("\n--- Test 7: Admin dashboard login ---")
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert "LeadAgent" in response.text or "login" in response.text.lower()

    response = client.post(
        "/admin/login",
        data={"owner_phone": "919111111111", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 401

    response = client.post(
        "/admin/login",
        data={
            "owner_phone": "919111111111",
            "password": os.environ["ADMIN_DASHBOARD_PASSWORD"],
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/"

    response = client.get("/admin/", cookies=response.cookies)
    assert response.status_code == 200
    assert "Dashboard" in response.text
    print("PASS: admin login and dashboard")

    print("\nAll webhook tests passed.")


if __name__ == "__main__":
    main()
