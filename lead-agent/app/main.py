"""FastAPI app and Meta WhatsApp webhook routes."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import db
from app.agent import handle_message
from app.whatsapp import send_whatsapp_reply, verify_webhook

load_dotenv()

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="WhatsApp Lead Management Agent")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()
    logger.info("Database initialized")


def _verify_meta_signature(raw_body: bytes, signature_header: str | None) -> bool:
    app_secret = os.getenv("WHATSAPP_APP_SECRET")
    if not app_secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False

    expected = signature_header.removeprefix("sha256=")
    digest = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, expected)


def _extract_incoming_text_message(payload: dict[str, Any]) -> tuple[str, str] | None:
    """Return (owner_phone, message_text) for the first inbound text message."""
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages") or []
                if not messages:
                    continue

                message = messages[0]
                if message.get("type") != "text":
                    return None

                body = (message.get("text") or {}).get("body")
                sender = message.get("from")
                if sender and body:
                    return str(sender), str(body)
    except (AttributeError, TypeError, KeyError, IndexError):
        logger.exception("Failed to parse webhook payload")

    return None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "timestamp": int(time.time())}


@app.get("/webhook")
async def webhook_verify(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    result = verify_webhook(mode, token, challenge)
    if result is None:
        return Response(status_code=403)

    return PlainTextResponse(content=result)


@app.post("/webhook")
@limiter.limit("30/minute")
async def webhook_receive(request: Request) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not _verify_meta_signature(raw_body, signature):
        logger.warning("Webhook rejected: invalid X-Hub-Signature-256")
        return Response(status_code=403)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.exception("Webhook received invalid JSON body")
        return Response(status_code=200)

    extracted = _extract_incoming_text_message(payload)
    if extracted is None:
        return Response(status_code=200)

    owner_phone, message_text = extracted

    try:
        reply = await handle_message(owner_phone, message_text)
        sent = await send_whatsapp_reply(owner_phone, reply)
        if not sent:
            logger.error("Failed to send WhatsApp reply to owner %s", owner_phone)
    except Exception:
        logger.exception("Error handling webhook message from %s", owner_phone)

    return Response(status_code=200)
