"""Have an LLM write one shitpost line in the account's voice.

Design intent:
- Any OpenAI-compatible chat endpoint works. The default is OpenRouter's
  `openrouter/free` router, which sends each request to a random free model —
  no cost, and a different voice per post. The key comes from LLM_API_KEY;
  endpoint and model are in config/bot.json, so switching providers or pinning
  one model is a config change, not a code change.
- Because the model is random, some picks are reasoning models that wrap
  their answer in <think>…</think> or spend tokens thinking first. The token
  budget is generous and thinking is stripped, and a failed or empty call just
  counts as a rejected attempt instead of crashing the run.
- The voice is steered by config/style_examples.txt: lines you think are funny. The
  model sees them as tone reference only and is told not to reuse them, so
  editing that file is how you tune the humor without touching code.
- Because posts go out unattended, every candidate passes cheap local checks
  before it's accepted: banned topics, length, and near-duplicates of anything
  already posted (word-overlap similarity). A rejected line is regenerated a
  few times; if nothing passes, the run posts nothing rather than something bad.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request

from common import CONFIG_DIR, load_config, read_lines as _read_lines

STYLE_FILE = CONFIG_DIR / "style_examples.txt"
BANNED_FILE = CONFIG_DIR / "banned_words.txt"

MAX_CHARS = 220
SIMILARITY_LIMIT = 0.6
MAX_ATTEMPTS = 4

# Topics that are a bad fit for an unattended account: real people, politics,
# tragedy, sexual content, slurs. Extend banned_words.txt to tighten further.
BASE_BANNED = [
    "trump", "biden", "election", "israel", "palestine", "ukraine", "russia",
    "shooting", "suicide", "rape", "nazi", "hitler", "terror", "cancer",
    "porn", "sex", "nsfw",
]

PROMPT = """You write single-post shitposts for an English-language Instagram meme page.
The page's humor: deadpan, absurd, mildly unhinged, chronically-online. Short and punchy beats long
and wholesome. Anti-jokes, dumb puns, fake-deep lines, "excuse vs reality" lists and gen-z slang
(ts, js, cuh, bro, mfs, nd) all fit. Never sound like a motivational or "relatable mom" page.

Voice reference (lines in the page's style; " / " is a line break; do NOT reuse, paraphrase or continue them):
{examples}

Write ONE new post.
Rules:
- Original joke. Never quote or rework a famous tweet or an existing meme caption, including the ones above.
- Max {max_chars} characters. Lowercase or ALL CAPS both fine. Up to three emoji (🥀😭🙏💔 fit the page).
- Use " / " for a line break if the joke needs one.
- It must work as text alone: no "this image", no describing a picture.
- No hashtags, no @mentions.
- No real, named people; no politics, tragedy, sexual content, or slurs. Everyday brands are fine.

Recently posted (don't repeat their premise):
{recent}

Reply with the post text only."""


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", text.lower()))


def similarity(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def check(text: str, history: list[str]) -> str | None:
    """Return a rejection reason, or None if the line is OK to post."""
    if not text:
        return "empty"
    if len(text) > MAX_CHARS:
        return f"too long ({len(text)} chars)"
    if "#" in text or "@" in text:
        return "contains hashtag or mention"
    lowered = text.lower()
    banned = BASE_BANNED + [w.lower() for w in _read_lines(BANNED_FILE)]
    for word in banned:
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            return f"banned word: {word}"
    for example in _read_lines(STYLE_FILE):
        if similarity(text, example) >= SIMILARITY_LIMIT:
            return "too close to a style example"
    for past in history:
        if similarity(text, past) >= SIMILARITY_LIMIT:
            return "too close to a past post"
    return None


def call_llm(prompt: str) -> str:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Set LLM_API_KEY (OpenAI-compatible key; OpenRouter by default).")
    global LAST_MODEL
    cfg = load_config()
    payload = json.dumps({
        "model": os.environ.get("LLM_MODEL", cfg["llm_model"]),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 1500,
    }).encode()
    req = urllib.request.Request(
        os.environ.get("LLM_API_BASE", cfg["llm_api_base"]),
        data=payload, method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                 # Optional OpenRouter attribution headers; ignored by other providers.
                 "HTTP-Referer": "https://github.com/plt8172/shitposts98",
                 "X-Title": "shitposts98"},
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = json.loads(resp.read())
    LAST_MODEL = body.get("model")
    content = body["choices"][0]["message"].get("content") or ""
    print(f"[writer] model: {LAST_MODEL}")
    return content


LAST_MODEL: str | None = None


def clean(raw: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S | re.I)
    text = text.split("</think>")[-1]  # unclosed opening tag case
    text = text.strip().strip('"').strip("“”").strip()
    text = text.replace(" / ", "\n")  # line-break marker from the prompt
    return re.sub(r"\n{3,}", "\n\n", text)


def write_post(history: list[str], llm=call_llm) -> str | None:
    """Generate one checked line, or None if every attempt was rejected."""
    examples = "\n".join(f"- {e}" for e in _read_lines(STYLE_FILE)[:30]) or "- (none yet)"
    recent = "\n".join(f"- {h}" for h in history[-15:]) or "- (none yet)"
    prompt = PROMPT.format(examples=examples, recent=recent, max_chars=MAX_CHARS)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            text = clean(llm(prompt))
        except Exception as exc:  # rate limit, provider hiccup, odd response
            print(f"[writer] attempt {attempt} failed: {exc}")
            time.sleep(5)
            continue
        reason = check(text, history)
        if reason is None:
            return text
        print(f"[writer] attempt {attempt} rejected ({reason}): {text!r}")
    return None
