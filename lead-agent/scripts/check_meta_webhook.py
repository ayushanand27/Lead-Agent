#!/usr/bin/env python3
"""Check Meta WhatsApp token and webhook subscription (uses Render API or local .env)."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

RENDER_KEY = os.environ.get("RENDER_API_KEY", "")
SERVICE_ID = "srv-d8v8obgk1i2s73c1bq20"
WABA_ID = "1682424813032373"


def fetch_render_env() -> dict[str, str]:
    if not RENDER_KEY:
        return {}
    req = urllib.request.Request(
        f"https://api.render.com/v1/services/{SERVICE_ID}/env-vars",
        headers={"Authorization": f"Bearer {RENDER_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return {item["envVar"]["key"]: item["envVar"]["value"] for item in data}


def graph_get(path: str, token: str) -> dict:
    url = f"https://graph.facebook.com/v19.0/{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    render_env = fetch_render_env()
    token = render_env.get("WHATSAPP_TOKEN") or os.environ.get("WHATSAPP_TOKEN", "")
    phone_id = render_env.get("WHATSAPP_PHONE_NUMBER_ID") or os.environ.get(
        "WHATSAPP_PHONE_NUMBER_ID", ""
    )

    if not token:
        print("No WHATSAPP_TOKEN found")
        sys.exit(1)

    print("--- Token check (phone number) ---")
    try:
        info = graph_get(f"{phone_id}?fields=display_phone_number,verified_name", token)
        print("OK:", json.dumps(info))
    except Exception as exc:
        print("TOKEN ERROR:", exc)

    print("\n--- WABA subscribed apps ---")
    try:
        subs = graph_get(f"{WABA_ID}/subscribed_apps", token)
        print(json.dumps(subs, indent=2))
    except Exception as exc:
        print("SUBSCRIPTION ERROR:", exc)


if __name__ == "__main__":
    main()
