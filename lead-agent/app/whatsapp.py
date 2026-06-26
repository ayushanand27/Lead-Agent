"""Meta WhatsApp Cloud API helpers."""

import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHATSAPP_GRAPH_API_VERSION = "v19.0"


def verify_webhook(mode: str | None, token: str | None, challenge: str | None) -> str | None:
    """
    Validate Meta webhook subscription challenge.
    Returns the challenge string if valid, else None.
    """
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if mode != "subscribe" or not expected_token or not token or not challenge:
        return None
    if token != expected_token:
        return None
    return challenge


def _normalize_recipient(phone: str) -> str:
    return phone.strip().lstrip("+")


async def send_whatsapp_reply(to_phone: str, message: str) -> bool:
    """
    Send a text reply via Meta WhatsApp Cloud API.
    Returns True on success, False on failure. Never raises.
    """
    token = os.getenv("WHATSAPP_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not token or not phone_number_id:
        logger.error("WhatsApp send failed: WHATSAPP_TOKEN or WHATSAPP_PHONE_NUMBER_ID not set")
        return False

    if not to_phone or not message:
        logger.error("WhatsApp send failed: missing recipient or message body")
        return False

    url = (
        f"https://graph.facebook.com/{WHATSAPP_GRAPH_API_VERSION}/"
        f"{phone_number_id}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalize_recipient(to_phone),
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        return True
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response is not None else str(exc)
        logger.error("WhatsApp API HTTP error: %s", detail)
        return False
    except Exception as exc:
        logger.error("WhatsApp send failed: %s", exc)
        return False
