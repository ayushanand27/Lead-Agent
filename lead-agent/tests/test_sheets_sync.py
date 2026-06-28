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

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"ok":true}'

    mock_client = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with patch("app.integrations.sheets.httpx.Client", return_value=mock_client):
        sync_lead_to_sheet(lead)

    assert mock_client.post.called
    posted_body = mock_client.post.call_args[1].get("content") or mock_client.post.call_args[0][1]
    assert "2026-06-28" in posted_body
    assert "datetime" not in posted_body


def test_sync_follows_gas_redirect_with_post(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEETS_WEBHOOK_URL", "https://script.google.com/macros/s/test/exec")

    redirect = MagicMock()
    redirect.status_code = 302
    redirect.headers = {"Location": "https://script.googleusercontent.com/macros/echo?token=abc"}

    ok = MagicMock()
    ok.status_code = 200
    ok.text = '{"ok":true}'

    mock_client = MagicMock()
    mock_client.post.side_effect = [redirect, ok]
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    lead = {"id": 2, "name": "Test", "phone": "91", "source": "x", "status": "new", "owner_phone": "91"}

    with patch("app.integrations.sheets.httpx.Client", return_value=mock_client):
        sync_lead_to_sheet(lead)

    assert mock_client.post.call_count == 2
