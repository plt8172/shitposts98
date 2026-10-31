# Writing task (Claude Code scheduled task)

A Claude Code scheduled task follows this file once a day. Its only job is to
write good lines and queue them. It never renders or posts. GitHub Actions
(`.github/workflows/post.yml`) takes the oldest queued line on each scheduled
run, renders it and publishes it.

Why the split: the joke is the only step that needs taste. Everything after it
is deterministic and already works on Actions, which also holds the Instagram
token. So this task needs push access to this repo and nothing else: no
Instagram token, no Slack token, no network allowlist.

## Each run

1. Sync with main (the workflow commits to it several times a day):
   ```bash
   git fetch origin main && git checkout -B main origin/main
   ```
2. If a `STOP` file exists at the repo root, stop here without writing.
3. See what's left: `python scripts/queue_lines.py list`.
   The target is **6 pending lines** (two days of posts at 3/day), so one
   missed run doesn't leave the account empty. Write `6 - pending` lines. If 6
   or more are already pending, stop here.
4. Read the voice before writing:
   - `config/style_examples.txt`: the owner's picks. These set the tone. Never reuse or paraphrase them.
   - The last 20 posted lines: `cat cards/*/*.json | grep '"text"' | tail -20`. Don't repeat a premise.
5. Write about 3× as many candidates as you need, then keep the best ones by the bar below.
6. Queue them, one argument per line (`" / "` = line break on the card):
   ```bash
   python scripts/queue_lines.py add "line one" "nobody: / me at 3am: buying a lamp"
   ```
   Any `REJECTED` line failed a check (banned topic, too long, hashtag or
   mention, too close to a past post). Write a replacement and add it.
7. Commit and push to main:
   ```bash
   git add queue && git commit -m "queue: <n> lines" && git pull --rebase origin main && git push origin main
   ```

## The bar

The page is an English, chronically online shitpost account. Run each
candidate through these and cut anything that fails one:

- **It has a turn.** The last few words flip, escalate or undercut the setup. "Relatable observation, no punchline" fails. Example: "me in the mirror trying to fix my hair" is a situation, not a joke.
- **Deadpan or unhinged, not wholesome.** No motivational tone, no "we've all been there 😅" mom-page energy.
- **Short.** Most lines should fit in 1–2 short sentences. Cut every word the joke survives without.
- **Specific beats generic.** "a 2am Wikipedia article about medieval spoons" beats "doing random stuff late at night".
- **Mix formats** across a batch: one-liners, `pov:`, `nobody: / me:`, fake lists with " / ", anti-jokes, fake-deep lines. Don't queue three `pov:` lines in a row.
- **Clean English.** Lowercase and slang (ts, js, cuh, bro, mfs, nd) are on purpose. Typos and grammar slips that aren't on purpose ("a apocalypse") are not.
- **Text alone.** No "this image", nothing that needs a picture.
- **Safe to post unattended:** no real named people, politics, tragedy, sexual content or slurs. Everyday brands are fine.
- At most three emoji, and only when they add something (🥀😭🙏💔 fit the page).
