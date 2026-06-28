"""Google Sheets sync tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.integrations.sheets import sync_lead_to_sheet


def test_sync_serializes_postgres_datetime(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")

    lead = {
        "id": 1,
        "name": "Ramesh",
        "phone": "919876543210",
        "source": "WhatsApp",
        "status": "new",
        "notes": None,
        "consent_source": None,
        "consent_at": None,
        "last_contacted_at": None,
        "created_at": datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
        "owner_phone": "917073245149",
    }

    post_response = MagicMock()
    post_response.status_code = 302
    post_response.headers = {"Location": "https://script.googleusercontent.com/macros/echo?token=abc"}
    post_response.text = ""

    get_response = MagicMock()
    get_response.status_code = 200
    get_response.text = '{"ok":true}'

    mock_client = MagicMock()
    mock_client.post.return_value = post_response
    mock_client.get.return_value = get_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.integrations.sheets.httpx.Client", return_value=mock_client):
        assert sync_lead_to_sheet(lead) is True

    mock_client.post.assert_called_once()
    mock_client.get.assert_called_once()
    posted_body = mock_client.post.call_args.kwargs.get("content") or mock_client.post.call_args.args[1]
    assert "2026-06-28" in posted_body


def test_sync_treats_gas_redirect_as_success_without_get(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")

    post_response = MagicMock()
    post_response.status_code = 302
    post_response.headers = {}
    post_response.text = ""

    mock_client = MagicMock()
    mock_client.post.return_value = post_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    lead = {"id": 2, "name": "Test", "phone": "91", "source": "x", "status": "new", "owner_phone": "91"}

    with patch("app.integrations.sheets.httpx.Client", return_value=mock_client):
        assert sync_lead_to_sheet(lead) is True
