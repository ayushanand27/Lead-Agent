"""Optional IP allowlist for admin dashboard access."""

from __future__ import annotations

import os


def get_admin_ip_allowlist() -> list[str]:
    raw = os.getenv("ADMIN_IP_ALLOWLIST", "").strip()
    if not raw:
        return []
    return [ip.strip() for ip in raw.split(",") if ip.strip()]


def is_ip_allowed(client_ip: str) -> bool:
    allowed = get_admin_ip_allowlist()
    if not allowed:
        return True
    return client_ip in allowed
