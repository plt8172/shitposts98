"""The line queue: Claude writes lines ahead of time, the workflow posts them.

Design intent:
- Writing a joke is the one step that needs taste, so a Claude Code scheduled
  task does it once a day (see docs/WRITE.md) and commits the lines here.
  Rendering and publishing stay on GitHub Actions, where the Instagram token
  already lives — the Claude task needs no Instagram token and no extra
  network access, only push access to this repo.
- One file per line (queue/<timestamp>-<hash>.txt) so the Claude task adding
  lines and the workflow consuming one never edit the same file, and a git
  rebase between them can't conflict. Oldest file is posted first.
- Lines go through the same writer.check() on the way in (so Claude sees a
  rejection while it can still rewrite) and again on the way out (past posts
  may have changed since it was queued). A line that fails on the way out is
  dropped rather than posted.

Usage (from the Claude task):
  python scripts/queue_lines.py add "line one" "nobody: / me at 3am: ..."
  python scripts/queue_lines.py list
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import common
import writer
from common import all_cards

KST = timezone(timedelta(hours=9))


def pending() -> list[Path]:
    return sorted(common.QUEUE_DIR.glob("*.txt"))


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def add(lines: list[str]) -> list[tuple[str, str | None]]:
    """Queue each line that passes the checks. Returns (line, rejection or None)."""
    history = [c["text"] for c in all_cards()] + [_text(p) for p in pending()]
    common.QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for i, raw in enumerate(lines):
        text = writer.clean(raw)
        reason = writer.check(text, history)
        if reason is None:
            stamp = datetime.now(KST).strftime("%Y%m%d%H%M%S")
            digest = hashlib.sha1(f"{time.time()}:{i}:{text}".encode()).hexdigest()[:6]
            (common.QUEUE_DIR / f"{stamp}-{i:02d}-{digest}.txt").write_text(text + "\n", encoding="utf-8")
            history.append(text)
        results.append((text, reason))
    return results


def take(history: list[str], consume: bool = True) -> str | None:
    """Return the oldest queued line that still passes the checks, or None.

    With consume=False (dry run) nothing is deleted."""
    for path in pending():
        text = _text(path)
        reason = writer.check(text, history)
        if consume:
            path.unlink()
        if reason is None:
            return text
        print(f"[queue] dropped {path.name} ({reason}): {text!r}")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("add").add_argument("lines", nargs="+")
    sub.add_parser("list")
    args = ap.parse_args()

    if args.cmd == "add":
        rejected = 0
        for text, reason in add(args.lines):
            flat = text.replace("\n", " / ")
            if reason:
                rejected += 1
                print(f"REJECTED ({reason}): {flat}")
            else:
                print(f"queued: {flat}")
        print(f"[queue] {len(pending())} line(s) pending")
        sys.exit(1 if rejected else 0)
    for path in pending():
        print(f"{path.name}: {_text(path).replace(chr(10), ' / ')}")
    print(f"[queue] {len(pending())} line(s) pending")


if __name__ == "__main__":
    main()
