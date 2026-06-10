# Running the Telegram bot

Status: **step 2** — full round-trip. Send a clip, get back the finished
1080x1920 edit as a document: hook, auto-zoom, speed-ramps, caption, muted
for an in-app TikTok sound. The Claude-written caption and the
approve/redo loop come in later steps (see `BOT_ARCHITECTURE.md`).

## How a clip flows

1. You send a video **as a file** (optionally with a message caption —
   that text becomes the on-video caption; otherwise the filename is used).
2. The bot downloads it, runs the caption eligibility check, and queues
   the render (one at a time — parallel encodes can OOM the box).
3. A status message updates live with the edit plan and progress.
4. The finished `.mp4` comes back as a **document** (no recompression),
   ready to upload to TikTok.

## Setup

```bash
venv/bin/pip install -e ".[bot]"     # installs python-telegram-bot
cp .env.example .env                 # then fill in the values
```

Get the two required values:
- **`TELEGRAM_BOT_TOKEN`** — create a bot via [@BotFather](https://t.me/BotFather).
- **`TOKCUT_ALLOWED_USER_ID`** — your numeric Telegram id from
  [@userinfobot](https://t.me/userinfobot). The bot only answers this user.

## Run

```bash
set -a; . ./.env; set +a      # load .env into the environment
venv/bin/tokcut-bot           # or: venv/bin/python3 -m tokcut.bot.app
```

Then in Telegram: send `/start`, then send a clip. **Send it as a *file*
(document), not as a video** — Telegram re-compresses videos and would
ruin the quality. The bot edits it and sends the finished vertical clip
back as a document.

> The standard Bot API caps downloads at **50 MB**. A 95 s iPhone HEVC clip
> is ~250 MB, so for full clips you'll need a local Bot API server — that's
> step 5 on the roadmap.

## What runs where

- **Python** (this code): Telegram I/O, allow-list, downloads, running
  `tokcut` — everything deterministic.
- **Claude Code** (subscription OAuth, later): caption wording, reviewing
  the rendered output, the approve/redo conversation. Set
  `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) now so it's ready.
