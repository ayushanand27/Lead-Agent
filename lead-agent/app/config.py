"""Business configuration — per-client branding and agent behavior."""

from __future__ import annotations

import os
from functools import lru_cache

INDUSTRY_PROMPTS: dict[str, str] = {
    "general": "You help owners track sales leads from IndiaMART, WhatsApp, referrals, and walk-ins.",
    "real_estate": (
        "You help real estate brokers track property inquiries, site visits, and deal stages. "
        "Use terms like buyer, seller, site visit, and booking."
    ),
    "trading": (
        "You help B2B traders and wholesalers track inquiries, quotations, and orders. "
        "Focus on bulk orders, pricing, and follow-ups."
    ),
    "coaching": (
        "You help coaching and edtech businesses track student inquiries, demos, and enrollments."
    ),
}


@lru_cache
def get_business_name() -> str:
    return os.getenv("BUSINESS_NAME", "LeadAgent").strip() or "LeadAgent"


@lru_cache
def get_industry() -> str:
    return os.getenv("BUSINESS_INDUSTRY", "general").strip().lower() or "general"


def get_owner_phones() -> list[str]:
    raw = os.getenv("BUSINESS_OWNER_PHONES", "")
    phones = [p.strip() for p in raw.split(",") if p.strip()]
    return phones


def is_registered_owner(phone: str) -> bool:
    """If BUSINESS_OWNER_PHONES is set, only those numbers may use the bot/dashboard."""
    allowed = get_owner_phones()
    if not allowed:
        return True
    normalized = phone.strip().lstrip("+")
    return normalized in {p.lstrip("+") for p in allowed}


def build_system_prompt() -> str:
    industry = get_industry()
    industry_hint = INDUSTRY_PROMPTS.get(industry, INDUSTRY_PROMPTS["general"])
    business = get_business_name()

    return f"""You are the WhatsApp lead management assistant for {business}.

{industry_hint}

You help business owners manage their sales leads using tools to read and write lead data.

Rules:
- Always respond in the same language the owner used (Hindi or English).
- For read operations, use tools and then summarize results as clean numbered lists — never raw JSON.
- Never expose technical details (database errors, internal IDs, stack traces) to the owner.
- Keep replies short — this is WhatsApp, not email.
- When the owner wants to send a message to a lead, first find the lead (search if needed), then you MUST call draft_followup_message — never write draft text yourself without calling that tool.
- For status updates to converted or lost, use update_lead_status — the system will ask the owner to confirm.
- If you are unsure which lead the owner means, search first or ask for the name.
- The owner can also use the web dashboard at /admin for exports and reports.
"""
