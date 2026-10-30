"""Pipeline tests with a stub LLM and stub Instagram: python -m pytest -q tests"""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common  # noqa: E402
import make_card  # noqa: E402
import publish  # noqa: E402
import writer  # noqa: E402


@pytest.fixture
def cards_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "CARDS_DIR", tmp_path)
    monkeypatch.setattr(make_card, "CARDS_DIR", tmp_path)
    monkeypatch.setattr(make_card, "STOP_FILE", tmp_path / "STOP")
    monkeypatch.setenv("IG_ACCESS_TOKEN", "test-token")
    cfg = {**common.load_config(), "ig_user_id": "17841400000000000"}
    monkeypatch.setattr(publish, "load_config", lambda: cfg)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    return tmp_path


def fake_render(text, out, **kw):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"\xff\xd8fake")
    return out


def test_writer_checks():
    assert writer.check("vote for trump lol", []).startswith("banned")
    assert writer.check("my sleep schedule is just a suggestion at this point", []) is not None
    assert writer.check("socks vanish in the dryer", ["socks vanish in the dryer"]) is not None
    assert writer.check("x" * 300, []).startswith("too long")
    assert writer.check("follow @someone", []) is not None
    assert writer.check("my fridge has more going on than my social life", []) is None


def test_writer_gives_up_instead_of_posting_bad_line():
    calls = []
    assert writer.write_post([], llm=lambda p: calls.append(p) or "election day vibes") is None
    assert len(calls) == writer.MAX_ATTEMPTS


def test_make_then_publish(cards_dir):
    path = make_card.make(llm=lambda p: "my plants are thriving and i take that personally",
                          render=fake_render)
    card = json.loads(path.read_text())
    assert card["status"] == "made" and path.with_suffix(".jpg").exists()

    seen = {}
    def fake_publisher(url, caption, **kw):
        seen.update(url=url, host=kw["host"], user_id=kw["user_id"])
        return {"media_id": "1", "permalink": "https://instagram.com/p/x"}

    publish.publish(path, publisher=fake_publisher)
    assert seen["host"] == "https://graph.facebook.com" and seen["user_id"].isdigit()
    card = json.loads(path.read_text())
    assert card["status"] == "published" and card["permalink"].endswith("/x")
    assert seen["url"].endswith(f"/{card['date']}/{card['id']}.jpg")

    # Publishing twice is a no-op, not a duplicate post.
    publish.publish(path, publisher=lambda *a, **k: pytest.fail("published twice"))


def test_failed_publish_is_recorded(cards_dir):
    path = make_card.make(llm=lambda p: "the wifi goes out and suddenly i'm a philosopher",
                          render=fake_render)
    def boom(*a, **k):
        raise RuntimeError("instagram said no")
    with pytest.raises(RuntimeError):
        publish.publish(path, publisher=boom)
    card = json.loads(path.read_text())
    assert card["status"] == "failed" and "instagram said no" in card["error"]


def test_stop_file_and_daily_cap(cards_dir):
    (cards_dir / "STOP").touch()
    assert make_card.make(llm=lambda p: pytest.fail("should not write"), render=fake_render) is None
    (cards_dir / "STOP").unlink()

    day = cards_dir / "2026-10-30"
    day.mkdir()
    for i in range(common.load_config()["daily_cap"]):
        (day / f"c{i}.json").write_text(json.dumps({
            "id": f"c{i}", "date": "2026-10-30", "text": f"post {i}",
            "created_at": time.time(), "status": "published", "published_at": time.time()}))
    assert make_card.make(llm=lambda p: pytest.fail("cap ignored"), render=fake_render) is None


def test_real_render_is_jpeg(tmp_path):
    pytest.importorskip("playwright")
    from render import render
    out = render("me when the code works on the first try 💀", tmp_path / "c.jpg",
                 name="shitposts98", handle="shitposts98")
    assert out.read_bytes()[:2] == b"\xff\xd8"


def test_publish_refuses_placeholder_account_id(cards_dir, monkeypatch):
    monkeypatch.setattr(publish, "load_config",
                        lambda: {**common.load_config(), "ig_user_id": "FILL_ME"})
    path = make_card.make(llm=lambda p: "my alarm and i are in a toxic relationship",
                          render=fake_render)
    with pytest.raises(RuntimeError, match="numeric"):
        publish.publish(path, publisher=lambda *a, **k: pytest.fail("should not call"))


def test_clean_strips_reasoning_blocks():
    assert writer.clean("<think>user wants a joke...</think>\n\"my fridge hums louder than my ambitions\"") \
        == "my fridge hums louder than my ambitions"
    assert writer.clean("planning the joke</think>my wifi has commitment issues") \
        == "my wifi has commitment issues"


def test_llm_errors_count_as_failed_attempts(monkeypatch):
    monkeypatch.setattr(writer.time, "sleep", lambda s: None)
    calls = iter([RuntimeError("429 rate limited"), "", "my calendar is just a list of things i will avoid"])
    def flaky(prompt):
        item = next(calls)
        if isinstance(item, Exception):
            raise item
        return item
    assert writer.write_post([], llm=flaky) == "my calendar is just a list of things i will avoid"
