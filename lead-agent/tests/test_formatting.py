"""Tests for display formatting helpers."""

from app.utils.formatting import mask_phone


def test_mask_phone_hides_middle_digits():
    assert mask_phone("919876543210") == "91******3210"


def test_mask_phone_short_number_unchanged():
    assert mask_phone("12345") == "12345"


def test_mask_phone_none():
    assert mask_phone(None) == "—"
