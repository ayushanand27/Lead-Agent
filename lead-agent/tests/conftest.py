"""Pytest fixtures — isolated SQLite, no production database."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def isolated_test_env(tmp_path, monkeypatch):
    """Every test uses a fresh SQLite file; never production Postgres."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test_leads.db"))
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "test_verify_token")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test_app_secret")
