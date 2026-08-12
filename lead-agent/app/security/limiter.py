"""Shared slowapi Limiter instance — imported by main.py and API routers alike.

A single module-level instance avoids circular imports (main.py includes routers
from app.api.leads, so that router can't import the limiter back out of main.py).
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
