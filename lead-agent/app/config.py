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

INDUSTRY_FOLLOWUP_HINTS: dict[str, str] = {
    "general": (
        "Follow-up tone: polite, short, mention their original inquiry. "
        "Example opener: 'Hi {name}, following up on your enquiry from {source}.'"
    ),
    "real_estate": (
        "Mention site visit, budget, location preference, possession timeline. "
        "Example: 'Hi {name}, any update on the site visit for the property you enquired about?'"
    ),
    "trading": (
        "Mention quotation, MOQ, delivery timeline, and payment terms. "
        "Example: 'Hi {name}, checking if you received our rate for the bulk order.'"
    ),
    "coaching": (
        "Mention demo class, batch timing, fees, and learning goals. "
        "Example: 'Hi {name}, would you like to book a free demo session this week?'"
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


def get_owner_scope(acting_phone: str) -> list[str]:
    """
    Phones whose leads are visible to the acting owner.
    Registered partners (all in BUSINESS_OWNER_PHONES) share one pool.
  Unregistered numbers only see their own owner_phone rows.
    """
    allowed = get_owner_phones()
    normalized = acting_phone.strip().lstrip("+")
    if allowed:
        allowed_set = sorted({p.strip().lstrip("+") for p in allowed if p.strip()})
        if normalized in allowed_set:
            return allowed_set
        return [normalized] if normalized else []
    return [normalized] if normalized else []


def primary_owner_phone() -> str | None:
    phones = get_owner_phones()
    if not phones:
        return None
    return phones[0].strip().lstrip("+")


def build_system_prompt() -> str:
    industry = get_industry()
    industry_hint = INDUSTRY_PROMPTS.get(industry, INDUSTRY_PROMPTS["general"])
    followup_hint = INDUSTRY_FOLLOWUP_HINTS.get(industry, INDUSTRY_FOLLOWUP_HINTS["general"])
    business = get_business_name()

    return f"""You are the WhatsApp lead management assistant for {business}.

{industry_hint}

Follow-up style for this business:
{followup_hint}

You help business owners manage their sales leads using tools to read and write lead data.

Rules:
- Always respond in the same language the owner used (Hindi or English).
- For read operations, use tools and then summarize results as clean numbered lists — never raw JSON.
- Never expose technical details (database errors, internal IDs, stack traces) to the owner.
- Keep replies short — this is WhatsApp, not email.
- When the owner wants to send a message to a lead, first find the lead (search if needed), then you MUST call draft_followup_message — never write draft text yourself without calling that tool.
- For status updates to converted or lost, use update_lead_status — the system will ask the owner to confirm.
- If you are unsure which lead the owner means, search first or ask for the name.
- NEVER say a lead was not found unless you called search_leads and it returned zero matches.
- The owner can also use the web dashboard at /admin for exports and reports.
- Leads captured via website webhook include consent metadata for compliance.
- Use add_lead_tags to label leads (e.g. site-visit, urgent, noida) — comma-separated tags.
- Multiple registered owners share the same lead database for this business.
"""
