"""Owner phone normalization and admin login helpers."""

from app.admin.auth import login_owner
from app.utils.phone import normalize_owner_phone


def test_normalize_owner_phone_formats():
    assert normalize_owner_phone("917073245149") == "917073245149"
    assert normalize_owner_phone("+91 70732 45149") == "917073245149"
    assert normalize_owner_phone("7073245149") == "917073245149"
    assert normalize_owner_phone("07073245149") == "917073245149"


def test_login_accepts_10_digit_indian_mobile(isolated_test_env, monkeypatch):
    monkeypatch.setenv("BUSINESS_OWNER_PHONES", "917073245149")
    monkeypatch.setenv("ADMIN_DASHBOARD_PASSWORD", "Ayush@123")

    class FakeRequest:
        session: dict = {}

    req = FakeRequest()
    assert login_owner(req, "7073245149", "Ayush@123") is True
    assert req.session["owner_phone"] == "917073245149"


def test_login_rejects_wrong_password(isolated_test_env, monkeypatch):
    monkeypatch.setenv("BUSINESS_OWNER_PHONES", "917073245149")
    monkeypatch.setenv("ADMIN_DASHBOARD_PASSWORD", "Ayush@123")

    class FakeRequest:
        session: dict = {}

    assert login_owner(FakeRequest(), "917073245149", "wrong") is False


def test_password_with_at_sign_and_quotes(isolated_test_env, monkeypatch):
    from app.security.passwords import verify_admin_password

    assert verify_admin_password("Ayush@123", "Ayush@123")
    assert verify_admin_password("Ayush@123", '"Ayush@123"')
    assert verify_admin_password("  Ayush@123  ", "Ayush@123")
