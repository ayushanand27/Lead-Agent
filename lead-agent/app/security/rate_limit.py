"""In-memory login rate limiting per client IP."""

from __future__ import annotations

import time
from collections import defaultdict

_WINDOW_SECONDS = 900  # 15 minutes
_MAX_ATTEMPTS = 5

_failures: dict[str, list[float]] = defaultdict(list)


def is_login_blocked(client_ip: str) -> bool:
    now = time.time()
    recent = [ts for ts in _failures[client_ip] if now - ts < _WINDOW_SECONDS]
    _failures[client_ip] = recent
    return len(recent) >= _MAX_ATTEMPTS


def record_login_failure(client_ip: str) -> None:
    _failures[client_ip].append(time.time())


def clear_login_failures(client_ip: str) -> None:
    _failures.pop(client_ip, None)


def reset_rate_limits_for_tests() -> None:
    """Clear in-memory state between test runs."""
    _failures.clear()
