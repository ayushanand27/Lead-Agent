#!/usr/bin/env python3
"""Generate a bcrypt hash for ADMIN_DASHBOARD_PASSWORD (recommended for production)."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.security.passwords import hash_password  # noqa: E402


def main() -> None:
    plain = getpass.getpass("Admin password to hash: ")
    if len(plain) < 8:
        print("Use at least 8 characters.")
        sys.exit(1)
    print("\nSet on Render:\n")
    print(f"ADMIN_DASHBOARD_PASSWORD={hash_password(plain)}")
    print("\n(Starts with $2 — the app auto-detects bcrypt hashes.)")


if __name__ == "__main__":
    main()
