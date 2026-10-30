"""One-time helper: check a Unified Login token and find the Instagram account ID.

After "Generate token" in the plutofeed app dashboard, run:

    IG_ACCESS_TOKEN=... python scripts/check_token.py
    # optional, to also print the expiry:
    IG_ACCESS_TOKEN=... META_APP_ID=... META_APP_SECRET=... python scripts/check_token.py

Why this exists: with Unified Login the token is a *system user* token, so
`/me` is the system user, not your Instagram account. The account ID you post
as comes from `/me/assigned_instagram_accounts`; it goes into
config/bot.json → ig_user_id. The expiry is whatever the login configuration
was set to — "never" is what an unattended bot wants.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://graph.facebook.com/v26.0"


def get(path: str, **params) -> dict:
    url = f"{HOST}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{path}: HTTP {exc.code} {exc.read().decode(errors='replace')}")


def main() -> None:
    token = os.environ.get("IG_ACCESS_TOKEN") or sys.exit("Set IG_ACCESS_TOKEN.")

    me = get("me", fields="id,name,client_business_id", access_token=token)
    print(f"system user: {me.get('name')} (id {me.get('id')}), "
          f"business: {me.get('client_business_id')}")

    accounts = get("me/assigned_instagram_accounts", access_token=token).get("data", [])
    if not accounts:
        print("No Instagram account is assigned to this token. Re-run Generate token "
              "and make sure the account is selected during login.")
    for acc in accounts:
        print(f"instagram account: @{acc.get('username', '?')}  id {acc.get('id')}"
              "   <- put this id in config/bot.json ig_user_id")

    app_id, secret = os.environ.get("META_APP_ID"), os.environ.get("META_APP_SECRET")
    if app_id and secret:
        info = get("debug_token", input_token=token,
                   access_token=f"{app_id}|{secret}").get("data", {})
        exp = info.get("expires_at", 0)
        when = "never" if not exp else time.strftime("%Y-%m-%d", time.localtime(exp))
        print(f"valid: {info.get('is_valid')}  expires: {when}  "
              f"scopes: {', '.join(info.get('scopes', []))}")
        if exp:
            print("This token expires. For an unattended bot, set the login "
                  "configuration's token expiration to 'never' and generate again.")


if __name__ == "__main__":
    main()
