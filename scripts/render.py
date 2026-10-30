"""Render one shitpost line as a tweet-style card (1080x1350 JPEG).

Design intent:
- 4:5 portrait is the ratio that takes the most room in the Instagram feed.
- Laid out like a text post (avatar, name, handle, text) but with no X/Twitter
  logo or UI chrome: it reads as the familiar format while being clearly *your*
  post under *your* handle, not a capture of someone else's tweet — which is
  also what makes it count as original content.
- A headless browser (Playwright) does the layout so wrapping, emoji and mixed
  scripts come from a real text engine. Inter is bundled in fonts/ so the card
  looks identical on a laptop and on a GitHub Actions runner.
- Instagram's publishing API accepts JPEG only.

Usage: python scripts/render.py "text" -o out.jpg [--theme dark]
"""
from __future__ import annotations

import argparse
import base64
import html
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "fonts"
WIDTH, HEIGHT = 1080, 1350

THEMES = {
    "light": {"bg": "#ffffff", "text": "#0f1419", "sub": "#536471"},
    "dark":  {"bg": "#000000", "text": "#e7e9ea", "sub": "#71767b"},
}


def font_size_for(text: str) -> int:
    """Shorter text -> bigger type; ~280 chars still fits."""
    n = len(text)
    if n <= 40:
        return 64
    if n <= 90:
        return 54
    if n <= 160:
        return 46
    return 38


def _font_face(weight: int, file: str) -> str:
    path = FONTS / file
    if not path.exists():
        return ""
    return (f"@font-face {{ font-family:'CardInter'; font-weight:{weight}; "
            f"src:url('{path.as_uri()}'); }}")


def _avatar(avatar: Path | None, name: str) -> str:
    if avatar and avatar.exists():
        mime = mimetypes.guess_type(avatar.name)[0] or "image/jpeg"
        data = base64.b64encode(avatar.read_bytes()).decode()
        return f'<img class="avatar" src="data:{mime};base64,{data}">'
    initial = html.escape(name[:1].upper() or "?")
    return f'<div class="avatar fallback">{initial}</div>'


def build_html(text: str, *, name: str, handle: str, theme: str = "light",
               avatar: Path | None = None) -> str:
    t = THEMES[theme]
    body = html.escape(text).replace("\n", "<br>")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  {_font_face(400, "Inter-Regular.otf")}
  {_font_face(700, "Inter-Bold.otf")}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:{WIDTH}px; height:{HEIGHT}px; background:{t['bg']}; }}
  body {{ display:flex; align-items:center; justify-content:center;
         font-family:'CardInter','Inter','Noto Sans CJK KR','Noto Color Emoji',sans-serif; }}
  .card {{ width:{WIDTH - 120}px; padding:0 8px; }}
  .head {{ display:flex; align-items:center; gap:24px; margin-bottom:32px; }}
  .avatar {{ width:110px; height:110px; border-radius:50%; object-fit:cover; flex:none; }}
  .fallback {{ background:#7856ff; color:#fff; font-size:52px; font-weight:700;
              display:flex; align-items:center; justify-content:center; }}
  .name {{ color:{t['text']}; font-size:40px; font-weight:700; line-height:1.15; }}
  .handle {{ color:{t['sub']}; font-size:36px; line-height:1.3; }}
  .text {{ color:{t['text']}; font-size:{font_size_for(text)}px; line-height:1.3;
          overflow-wrap:anywhere; }}
</style></head><body>
  <div class="card">
    <div class="head">{_avatar(avatar, name)}
      <div><div class="name">{html.escape(name)}</div>
           <div class="handle">@{html.escape(handle)}</div></div>
    </div>
    <div class="text">{body}</div>
  </div>
</body></html>"""


def render(text: str, out: Path, **kw) -> Path:
    from playwright.sync_api import sync_playwright

    out.parent.mkdir(parents=True, exist_ok=True)
    # Written to a file (not set_content) so file:// font URLs are allowed.
    page_file = out.with_suffix(".render.html")
    page_file.write_text(build_html(text, **kw), encoding="utf-8")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
            page.goto(page_file.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(out), type="jpeg", quality=95)
            browser.close()
    finally:
        page_file.unlink(missing_ok=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Render text as a tweet-style card.")
    ap.add_argument("text")
    ap.add_argument("-o", "--out", type=Path, default=Path("card.jpg"))
    ap.add_argument("--theme", choices=THEMES, default="light")
    ap.add_argument("--name", default="shitposts98")
    ap.add_argument("--handle", default="shitposts98")
    ap.add_argument("--avatar", type=Path)
    a = ap.parse_args()
    print(render(a.text, a.out, name=a.name, handle=a.handle, theme=a.theme, avatar=a.avatar))


if __name__ == "__main__":
    main()
