"""One-time helper: make sure the token you pasted is a long-lived one.

The dashboard's "Generate token" button may hand out a token that's already
long-lived (~60 days) or a short-lived one (~1 hour) depending on the flow.
The weekly refresh only works on long-lived tokens, so run this once before
saving the token as the IG_ACCESS_TOKEN secret:

    IG_ACCESS_TOKEN=... IG_APP_SECRET=... python scripts/check_token.py

- It first tries a refresh: if that works, the token was long-lived and the
  printed token is good for ~60 days.
- Otherwise it exchanges the short-lived token for a long-lived one, which
  needs the app's Instagram app secret (App dashboard → Instagram → API setup
  with Instagram login → Business login settings → Instagram app secret).
It prints the token to save and which account it belongs to.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

GRAPH = "https://graph.instagram.com"


def get(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode(errors="replace")) from exc


def main() -> None:
    token = os.environ.get("IG_ACCESS_TOKEN") or sys.exit("Set IG_ACCESS_TOKEN.")
    try:
        result = get(f"{GRAPH}/refresh_access_token?" + urllib.parse.urlencode(
            {"grant_type": "ig_refresh_token", "access_token": token}))
        kind = "long-lived (refreshed)"
    except RuntimeError as refresh_error:
        secret = os.environ.get("IG_APP_SECRET")
        if not secret:
            sys.exit(f"Refresh failed, so this is probably a short-lived token.\n"
                     f"Set IG_APP_SECRET and run again to exchange it.\n{refresh_error}")
        result = get(f"{GRAPH}/access_token?" + urllib.parse.urlencode(
            {"grant_type": "ig_exchange_token", "client_secret": secret, "access_token": token}))
        kind = "exchanged short-lived -> long-lived"

    new = result["access_token"]
    me = get(f"{GRAPH}/me?" + urllib.parse.urlencode(
        {"fields": "user_id,username", "access_token": new}))
    days = int(result.get("expires_in", 0)) // 86400
    print(f"{kind}; account @{me.get('username')} (user_id {me.get('user_id')}); ~{days} days",
          file=sys.stderr)
    print(new)


if __name__ == "__main__":
    main()
