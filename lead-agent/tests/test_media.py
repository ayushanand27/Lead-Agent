"""Voice transcription: optional Sarvam path, always falling back to Groq Whisper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.media import transcribe_whatsapp_audio

FAKE_AUDIO = (b"\x00\x01fake-ogg-bytes", "ogg")


def _run(coro):
    return asyncio.run(coro)


def test_sarvam_skipped_when_no_api_key(isolated_test_env, monkeypatch):
    """Default state (no SARVAM_API_KEY) — behavior identical to before this change."""
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)

    with (
        patch("app.media.download_whatsapp_media", new=AsyncMock(return_value=FAKE_AUDIO)),
        patch("app.media._transcribe_with_sarvam", new=AsyncMock()) as mock_sarvam,
        patch("app.media.transcribe_audio_bytes", return_value="list all my leads") as mock_whisper,
    ):
        result = _run(transcribe_whatsapp_audio("media-123"))

    mock_sarvam.assert_not_called()
    mock_whisper.assert_called_once()
    assert result == "list all my leads"


def test_sarvam_used_when_configured_and_successful(isolated_test_env, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-sarvam-key")

    with (
        patch("app.media.download_whatsapp_media", new=AsyncMock(return_value=FAKE_AUDIO)),
        patch(
            "app.media._transcribe_with_sarvam",
            new=AsyncMock(return_value="தமிழில் தேடு ரமேஷ்"),
        ) as mock_sarvam,
        patch("app.media.transcribe_audio_bytes") as mock_whisper,
    ):
        result = _run(transcribe_whatsapp_audio("media-123"))

    mock_sarvam.assert_called_once()
    mock_whisper.assert_not_called()
    assert result == "தமிழில் தேடு ரமேஷ்"


def test_falls_back_to_whisper_when_sarvam_fails(isolated_test_env, monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "test-sarvam-key")

    with (
        patch("app.media.download_whatsapp_media", new=AsyncMock(return_value=FAKE_AUDIO)),
        patch("app.media._transcribe_with_sarvam", new=AsyncMock(return_value=None)) as mock_sarvam,
        patch("app.media.transcribe_audio_bytes", return_value="search priya") as mock_whisper,
    ):
        result = _run(transcribe_whatsapp_audio("media-123"))

    mock_sarvam.assert_called_once()
    mock_whisper.assert_called_once()
    assert result == "search priya"


def test_sarvam_http_call_shape():
    """Sarvam request uses the documented multipart form fields, without hitting the network."""
    import httpx

    from app.media import _transcribe_with_sarvam

    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"transcript": "hata do ramesh", "language_code": "hi-IN"}

    async def fake_post(self, url, headers=None, data=None, files=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["files"] = files
        return FakeResponse()

    with (
        patch.dict("os.environ", {"SARVAM_API_KEY": "test-key"}),
        patch.object(httpx.AsyncClient, "post", new=fake_post),
    ):
        result = asyncio.run(_transcribe_with_sarvam(b"audio-bytes", "voice.ogg"))

    assert result == "hata do ramesh"
    assert captured["headers"]["api-subscription-key"] == "test-key"
    assert captured["data"]["model"] == "saarika:v2"
