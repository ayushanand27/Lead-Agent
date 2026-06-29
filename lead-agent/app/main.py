"""FastAPI app and Meta WhatsApp webhook routes."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from app import db
from app.admin.auth import get_session_secret, is_production
from app.admin.routes import router as admin_router
from app.agent import handle_message
from app.api.leads import router as api_leads_router
from app.logging_config import configure_logging
from app.security.headers import SecurityHeadersMiddleware
from app.media import transcribe_whatsapp_audio
from app.text_normalize import romanize_query
from app.whatsapp import send_whatsapp_reply, verify_webhook

load_dotenv()
configure_logging()

from app.monitoring import init_sentry

init_sentry()

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="LeadAgent",
    description="WhatsApp Lead Management Agent (MCP + Groq)",
    version="1.3.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    session_cookie="leadagent_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=is_production(),
)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(admin_router, prefix="/admin")
app.include_router(api_leads_router, prefix="/api")


@app.on_event("startup")
def on_startup() -> None:
    db.init_db()
    if db.check_connection():
        backend = "postgres" if os.getenv("DATABASE_URL") else "sqlite"
        logger.info("Database initialized (%s)", backend)
    else:
        logger.error("Database connection check failed on startup")


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


def _extract_incoming_message(payload: dict[str, Any]) -> tuple[str, str | None, str | None] | None:
    """Return (owner_phone, text_body, audio_media_id) for the first inbound message."""
    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages") or []
                if not messages:
                    continue

                message = messages[0]
                sender = message.get("from")
                if not sender:
                    continue

                msg_type = message.get("type")
                if msg_type == "text":
                    body = (message.get("text") or {}).get("body")
                    if body:
                        return str(sender), str(body), None
                elif msg_type == "audio":
                    media_id = (message.get("audio") or {}).get("id")
                    if media_id:
                        return str(sender), None, str(media_id)
    except (AttributeError, TypeError, KeyError, IndexError):
        logger.exception("Failed to parse webhook payload")

    return None


async def _process_incoming_message(
    owner_phone: str,
    message_text: str | None = None,
    audio_media_id: str | None = None,
) -> None:
    """Handle agent loop + outbound WhatsApp reply (runs after webhook ack)."""
    try:
        text = message_text
        if audio_media_id:
            logger.info("Transcribing voice note from owner %s", owner_phone)
            text = await transcribe_whatsapp_audio(audio_media_id)
            if not text:
                await send_whatsapp_reply(
                    owner_phone,
                    "Sorry, I couldn't understand that voice note. Please try again or type your message.",
                )
                return
            logger.info("Voice note transcribed for %s: %s", owner_phone, text[:120])
            text = romanize_query(text)

        if not text:
            return

        logger.info("Processing message from owner %s", owner_phone)
        reply = await handle_message(owner_phone, text, from_voice=bool(audio_media_id))
        sent = await send_whatsapp_reply(owner_phone, reply)
        if not sent:
            logger.error("Failed to send WhatsApp reply to owner %s", owner_phone)
    except Exception:
        logger.exception("Error handling webhook message from %s", owner_phone)


_public_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request) -> HTMLResponse:
    """Public landing — health snapshot + links to admin demo."""
    return _public_templates.TemplateResponse(
        request,
        "landing.html",
        {
            "health": health(),
            "app_version": app.version,
        },
    )


@app.head("/health")
def health_head() -> Response:
    """UptimeRobot and other monitors often use HEAD."""
    return Response(status_code=200)


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness probe — always 200 when the process is up (UptimeRobot / Render)."""
    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "database": "connected" if db.check_connection() else "unavailable",
        "cron_configured": bool(os.getenv("CRON_SECRET", "").strip()),
    }


@app.get("/health/ready")
def health_ready() -> Response:
    """Readiness probe — 503 when the database is unreachable."""
    if not db.check_connection():
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable"},
        )
    return JSONResponse(content={"status": "ready", "database": "connected"})


@app.api_route("/internal/cron/daily-summary", methods=["GET", "POST"])
async def cron_daily_summary(request: Request) -> JSONResponse:
    """Trigger morning lead summaries (CRON_SECRET via header or ?secret= query param)."""
    secret = os.getenv("CRON_SECRET", "").strip()
    provided = request.headers.get("X-Cron-Secret", "").strip()
    if not provided:
        provided = request.query_params.get("secret", "").strip()
    if not secret or not secrets.compare_digest(provided, secret):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    result = await send_daily_summaries()
    return JSONResponse(content={"status": "ok", **result})


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
async def webhook_receive(request: Request, background_tasks: BackgroundTasks) -> Response:
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

    extracted = _extract_incoming_message(payload)
    if extracted is None:
        return Response(status_code=200)

    owner_phone, message_text, audio_media_id = extracted
    logger.info("Webhook accepted message from %s", owner_phone)
    background_tasks.add_task(
        _process_incoming_message,
        owner_phone,
        message_text,
        audio_media_id,
    )
    return Response(status_code=200)
