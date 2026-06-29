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
WHISPER_PROMPT = (
    "Latin script only. WhatsApp lead commands: search Priya Mittal, list all my leads, "
    "add lead Rahul phone 9876543210 from website, who have not been contacted in 2 days."
)

_MIME_TO_EXT = {
    "audio/ogg": "ogg",
    "audio/opus": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/aac": "aac",
    "audio/amr": "amr",
}


def _extension_for_mime(mime_type: str | None) -> str:
    if not mime_type:
        return "ogg"
    base = mime_type.split(";")[0].strip().lower()
    return _MIME_TO_EXT.get(base, "ogg")


async def download_whatsapp_media(media_id: str) -> tuple[bytes, str] | None:
    token = os.getenv("WHATSAPP_TOKEN")
    if not token or not media_id:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    meta_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_API_VERSION}/{media_id}"

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            meta_resp = await client.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            meta = meta_resp.json()
            media_url = meta.get("url")
            if not media_url:
                return None
            file_resp = await client.get(media_url, headers=headers)
            file_resp.raise_for_status()
            ext = _extension_for_mime(meta.get("mime_type"))
            return file_resp.content, ext
    except Exception:
        logger.exception("Failed to download WhatsApp media id=%s", media_id)
        return None


def transcribe_audio_bytes(
    audio_bytes: bytes,
    filename: str = "voice.ogg",
) -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or not audio_bytes:
        return None

    try:
        client = Groq(api_key=api_key)
        result = client.audio.transcriptions.create(
            file=(filename, io.BytesIO(audio_bytes)),
            model=WHISPER_MODEL,
            prompt=WHISPER_PROMPT,
            response_format="text",
        )
        if isinstance(result, str):
            text = result.strip()
        else:
            text = (getattr(result, "text", None) or "").strip()
        return text or None
    except Exception:
        logger.exception("Groq Whisper transcription failed")
        return None


async def transcribe_whatsapp_audio(media_id: str) -> str | None:
    downloaded = await download_whatsapp_media(media_id)
    if not downloaded:
        return None
    audio_bytes, ext = downloaded
    return transcribe_audio_bytes(audio_bytes, filename=f"voice.{ext}")
