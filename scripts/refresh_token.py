"""Refresh the long-lived Instagram token and print the new one to stdout.

Long-lived tokens die ~60 days after their last refresh. The weekly workflow
pipes this script's output into `gh secret set IG_ACCESS_TOKEN`, so the bot
never quietly stops two months from now. (Semifeed does the same job from its
Worker cron with KV storage; here the token lives in a GitHub secret.)

Env: IG_ACCESS_TOKEN
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def main() -> None:
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        sys.exit("IG_ACCESS_TOKEN is not set.")
    query = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
    try:
        with urllib.request.urlopen(
                f"https://graph.instagram.com/refresh_access_token?{query}", timeout=30) as r:
            result = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"refresh failed: HTTP {exc.code} {exc.read().decode(errors='replace')}")
    days = int(result.get("expires_in", 0)) // 86400
    print(f"token refreshed, valid for ~{days} days", file=sys.stderr)
    print(result["access_token"])


if __name__ == "__main__":
    main()
