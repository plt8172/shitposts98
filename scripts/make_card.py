"""Step 1 of a run: write a line and render it into cards/<date>/<id>.{json,jpg}.

The card is only *made* here; publishing is a separate step because Instagram
fetches the image from its raw.githubusercontent.com URL, so the JPEG has to
be committed and pushed in between (the workflow does that).

Exit without making anything when:
- a STOP file exists at the repo root (pause the bot from the GitHub app by
  adding a file named STOP; delete it to resume),
- the daily cap of published posts is already reached,
- every generated line is rejected by the writer's checks.

Prints the card JSON path, and exposes it as the `card` step output.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import writer
from common import (CARDS_DIR, ROOT, STOP_FILE, all_cards, load_config,
                    notify_slack, published_last_24h, set_output)

KST = timezone(timedelta(hours=9))


def make(llm=writer.call_llm, render=None) -> Path | None:
    if STOP_FILE.exists():
        print("[make] STOP file present; not posting.")
        return None

    cfg = load_config()
    cards = all_cards()
    # A dry run posts nothing, so it shouldn't be blocked by the posting cap.
    dry_run = os.environ.get("DRY_RUN") == "true"
    if not dry_run and published_last_24h(cards) >= cfg["daily_cap"]:
        print(f"[make] daily cap {cfg['daily_cap']} reached; not posting.")
        return None

    text = writer.write_post([c["text"] for c in cards], llm=llm)
    if text is None:
        notify_slack("⚠️ shitposts98: every generated line was rejected; nothing posted.")
        print("[make] no acceptable line; nothing posted.")
        return None

    now = time.time()
    card_id = hashlib.sha1(f"{now}:{text}".encode()).hexdigest()[:10]
    day = datetime.fromtimestamp(now, KST).strftime("%Y-%m-%d")
    json_path = CARDS_DIR / day / f"{card_id}.json"
    jpg_path = json_path.with_suffix(".jpg")

    if render is None:
        from render import render
    avatar = ROOT / cfg["avatar"] if cfg.get("avatar") else None
    render(text, jpg_path, name=cfg["name"], handle=cfg["handle"],
           theme=cfg["theme"], avatar=avatar)

    card = {"id": card_id, "date": day, "text": text, "created_at": now, "status": "made",
            "llm_model": writer.LAST_MODEL}
    json_path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[make] {json_path.relative_to(ROOT) if json_path.is_relative_to(ROOT) else json_path}\n{text}")
    annotate(text, writer.LAST_MODEL)
    return json_path


def annotate(text: str, model: str | None) -> None:
    """On GitHub Actions, show the line on the run's summary page (as a notice
    annotation), so it can be read without downloading the artifact."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    body = text.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    print(f"::notice title=card ({model or 'unknown model'})::{body}")


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    path = make()
    set_output("card", str(path.relative_to(ROOT)) if path else "")
    sys.exit(0)


if __name__ == "__main__":
    main()
