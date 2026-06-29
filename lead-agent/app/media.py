"""Download WhatsApp media and transcribe voice notes via Groq Whisper."""

from __future__ import annotations

import io
import logging
import os

import httpx
from groq import Groq

from app.whatsapp import WHATSAPP_GRAPH_API_VERSION

logger = logging.getLogger(__name__)

WHISPER_MODEL = os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")


async def download_whatsapp_media(media_id: str) -> bytes | None:
    token = os.getenv("WHATSAPP_TOKEN")
    if not token or not media_id:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    meta_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_API_VERSION}/{media_id}"

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            meta_resp = await client.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            media_url = meta_resp.json().get("url")
            if not media_url:
                return None
            file_resp = await client.get(media_url, headers=headers)
            file_resp.raise_for_status()
            return file_resp.content
    except Exception:
        logger.exception("Failed to download WhatsApp media id=%s", media_id)
        return None


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "voice.ogg") -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not audio_bytes:
        return None

    try:
        client = Groq(api_key=api_key)
        result = client.audio.transcriptions.create(
            file=(filename, io.BytesIO(audio_bytes)),
            model=WHISPER_MODEL,
        )
        text = (result.text or "").strip()
        return text or None
    except Exception:
        logger.exception("Groq Whisper transcription failed")
        return None


async def transcribe_whatsapp_audio(media_id: str) -> str | None:
    audio_bytes = await download_whatsapp_media(media_id)
    if not audio_bytes:
        return None
    return transcribe_audio_bytes(audio_bytes)
