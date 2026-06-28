"""Shared environment for local/CI test scripts — no production secrets."""

from __future__ import annotations

import os
from pathlib import Path


def configure_test_environment(root: Path | None = None) -> None:
    """
    Force isolated SQLite and dummy API keys before importing app modules.
    Call this at the top of every scripts/test_*.py before `from app import ...`.
    """
    if root is not None:
        from dotenv import load_dotenv

        load_dotenv(root / ".env")  # optional local file; never use prod DB in tests
        test_db = root / "test_runtime.db"
        os.environ["DATABASE_PATH"] = str(test_db)
        if test_db.exists():
            test_db.unlink()

    # Never hit production Supabase from CI or local script tests
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("DATABASE_PASSWORD", None)

    os.environ["GROQ_API_KEY"] = "test-groq-key"
    os.environ["WHATSAPP_VERIFY_TOKEN"] = "test_verify_token"
    os.environ["WHATSAPP_APP_SECRET"] = "test_app_secret"
    os.environ["WHATSAPP_TOKEN"] = "test_whatsapp_token"
    os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "123456789"
    os.environ["ADMIN_SESSION_SECRET"] = "test-session-secret"
    os.environ["ADMIN_DASHBOARD_PASSWORD"] = "test-admin-password"
    os.environ["BUSINESS_OWNER_PHONES"] = "919111111111"
    os.environ["BUSINESS_NAME"] = "LeadAgent Test"
