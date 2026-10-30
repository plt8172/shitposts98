"""Step 2 of a run: publish a committed card to Instagram via the Graph API.

Uses "Instagram API with Unified Login" (graph.facebook.com) through the shared
"plutogram" Meta app. The token is a Business Integration System User Access
Token, so API calls address the Instagram account by its numeric ID
(config/bot.json → ig_user_id), never "me" (which would be the system user).
No Facebook Page needed. Instagram downloads the image
from the card's raw.githubusercontent.com URL, which is why the repo must be
public and why this runs only after the card has been pushed.

Usage: python scripts/publish.py cards/<date>/<id>.json
Env:   IG_ACCESS_TOKEN (required), SLACK_WEBHOOK_URL (optional)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import ROOT, load_config, notify_slack, save_card



def _request(url: str, data: dict | None = None) -> dict:
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url.split('?')[0]}: {detail}") from exc


def wait_until_public(url: str, attempts: int = 12, delay: float = 5) -> None:
    """raw.githubusercontent.com can lag a few seconds behind a push."""
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=15) as r:
                if r.status == 200:
                    return
        except urllib.error.URLError:
            pass
        time.sleep(delay)
    raise RuntimeError(f"Image never became reachable: {url} (is the repo public?)")


def publish_image(image_url: str, caption: str, *, token: str, user_id: str, version: str,
                  host: str = "https://graph.facebook.com") -> dict:
    base = f"{host.rstrip('/')}/{version}"
    container = _request(f"{base}/{user_id}/media",
                         {"image_url": image_url, "caption": caption, "access_token": token})["id"]
    for _ in range(20):
        status = _request(f"{base}/{container}?" + urllib.parse.urlencode(
            {"fields": "status_code", "access_token": token}))
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Media container {container} failed: {status}")
        time.sleep(3)
    media_id = _request(f"{base}/{user_id}/media_publish",
                        {"creation_id": container, "access_token": token})["id"]
    info = _request(f"{base}/{media_id}?" + urllib.parse.urlencode(
        {"fields": "permalink", "access_token": token}))
    return {"media_id": media_id, "permalink": info.get("permalink")}


def publish(card_path: Path, publisher=publish_image) -> dict:
    cfg = load_config()
    card = json.loads(card_path.read_text(encoding="utf-8"))
    card["_path"] = str(card_path)
    if card.get("status") == "published":
        print(f"[publish] already published: {card.get('permalink')}")
        return card

    token = os.environ.get("IG_ACCESS_TOKEN")
    if not token:
        raise SystemExit("IG_ACCESS_TOKEN is not set.")
    image_url = f"{cfg['cards_raw_base'].rstrip('/')}/{card['date']}/{card['id']}.jpg"
    try:
        if publisher is publish_image:
            wait_until_public(image_url)
        if not str(cfg["ig_user_id"]).isdigit():
            raise RuntimeError("config/bot.json ig_user_id must be the numeric Instagram "
                               "account ID (run scripts/check_token.py to find it).")
        result = publisher(image_url, cfg.get("caption", ""), token=token,
                           user_id=cfg["ig_user_id"], version=cfg["ig_api_version"],
                           host=cfg.get("graph_host", "https://graph.facebook.com"))
    except Exception as exc:
        card.update(status="failed", error=str(exc)[:500])
        save_card(card)
        hint = ("\n토큰이 만료됐거나 끊긴 것 같아요. plutogram 앱에서 토큰을 다시 생성해 "
                "IG_ACCESS_TOKEN secret을 바꿔주세요.") if '"code":190' in str(exc).replace(" ", "") else ""
        notify_slack(f"❌ shitposts98 publish failed: {exc}{hint}")
        raise

    card.update(status="published", published_at=time.time(), **result)
    card.pop("error", None)
    save_card(card)
    notify_slack(f"✅ posted: {result.get('permalink')}\n> {card['text']}")
    print(f"[publish] {result.get('permalink')}")
    return card


def main() -> None:
    ap = argparse.ArgumentParser(description="Publish a committed card to Instagram.")
    ap.add_argument("card", type=Path)
    a = ap.parse_args()
    path = a.card if a.card.is_absolute() else ROOT / a.card
    publish(path)
    sys.exit(0)


if __name__ == "__main__":
    main()
