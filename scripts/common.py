"""Paths, config and card bookkeeping shared by every script.

cards/<date>/<id>.json is the single source of truth (same layout as
Semifeed): it holds the text, when it was made, whether it was published and
the permalink. De-duplication and the daily cap both read these files, so the
state lives in git and survives across GitHub Actions runs without a database.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
CARDS_DIR = Path(os.environ.get("CARDS_DIR", ROOT / "cards"))
STOP_FILE = ROOT / "STOP"


def load_config() -> dict:
    return json.loads((CONFIG_DIR / "bot.json").read_text(encoding="utf-8"))


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [l.strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def all_cards() -> list[dict]:
    """Every card JSON, oldest first."""
    cards = []
    for path in sorted(CARDS_DIR.glob("*/*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        card["_path"] = str(path)
        cards.append(card)
    return sorted(cards, key=lambda c: c.get("created_at", 0))


def save_card(card: dict) -> None:
    path = Path(card["_path"])
    data = {k: v for k, v in card.items() if not k.startswith("_")}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def published_last_24h(cards: list[dict], now: float | None = None) -> int:
    cutoff = (now or time.time()) - 24 * 3600
    return sum(1 for c in cards
               if c.get("status") == "published" and c.get("published_at", 0) >= cutoff)


def notify_slack(text: str) -> None:
    """Post-hoc notice (not an approval). A Slack hiccup never fails a run."""
    hook = os.environ.get("SLACK_WEBHOOK_URL")
    if not hook:
        return
    req = urllib.request.Request(hook, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as exc:
        print(f"[slack] notify failed: {exc}")


def set_output(name: str, value: str) -> None:
    """Expose a value to later GitHub Actions steps (no-op locally)."""
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")
