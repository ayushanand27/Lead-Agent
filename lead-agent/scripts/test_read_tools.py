#!/usr/bin/env python3
"""Local smoke test for SQLite schema, seed data, and MCP read tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as: python scripts/test_read_tools.py
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_support import configure_test_environment  # noqa: E402

configure_test_environment(ROOT)

from app import db, lead_service  # noqa: E402
from app.mcp_server import (  # noqa: E402
    get_lead_details,
    get_stale_leads,
    list_leads,
    search_leads,
)

OWNER_A = "919111111111"
OWNER_B = "919222222222"


def pp(label: str, payload: str) -> None:
    print(f"\n{'=' * 60}")
    print(label)
    print("=" * 60)
    parsed = json.loads(payload)
    print(json.dumps(parsed, indent=2, default=str))


def main() -> None:
    db_path = db.get_db_path()
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database at {db_path}")

    print("Initializing schema...")
    db.init_db()

    print(f"Seeding leads for owner {OWNER_A}...")
    count = db.seed_test_leads(OWNER_A)
    print(f"Inserted {count} seed leads.")

    # --- Direct service-layer calls ---
    print("\n--- Service layer (lead_service) ---")

    result = lead_service.list_leads(OWNER_A)
    print(f"list_leads: {result['data']['count']} leads")

    result = lead_service.list_leads(OWNER_A, status_filter="warm")
    print(f"list_leads(warm): {result['data']['count']} leads")

    result = lead_service.get_stale_leads(OWNER_A, days_since_contact=2)
    print(f"get_stale_leads(2 days): {result['data']['count']} stale leads")
    for lead in result["data"]["leads"]:
        print(f"  - {lead['name']} ({lead['status']}), last_contacted={lead['last_contacted_at']}")

    result = lead_service.search_leads(OWNER_A, "IndiaMART")
    print(f"search_leads(IndiaMART): {result['data']['count']} matches")

    result = lead_service.get_lead_details(OWNER_A, lead_id=1)
    print(f"get_lead_details(id=1): {result['data']['lead']['name']}")

    # Owner isolation: owner B should see nothing
    result = lead_service.get_lead_details(OWNER_B, lead_id=1)
    assert result["success"] is False, "Owner B must not access Owner A's lead"
    print(f"Owner isolation check passed: owner B cannot read lead id=1")

    # --- MCP tool wrappers (same logic, JSON string output) ---
    print("\n--- MCP tool layer (mcp_server) ---")

    pp("MCP list_leads", list_leads(OWNER_A))
    pp("MCP get_stale_leads (2 days)", get_stale_leads(OWNER_A, days_since_contact=2))
    pp("MCP search_leads (Ramesh)", search_leads(OWNER_A, query="Ramesh"))
    pp("MCP get_lead_details (id=2)", get_lead_details(OWNER_A, lead_id=2))

    print("\nAll read-tool checks passed.")


if __name__ == "__main__":
    main()
