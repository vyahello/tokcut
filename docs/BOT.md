# Running the Telegram bot

Status: **step 3** — Claude in the loop. Send a clip, Claude watches it
and writes the caption, the bot renders the 1080x1920 edit (hook,
auto-zoom, speed-ramps, muted for an in-app sound), Claude reviews the
result, and the finished file comes back as a document. The approve/redo
conversation is step 4 (see `BOT_ARCHITECTURE.md`).

## How a clip flows

1. You send a video **as a file**. If you add a message caption, that
   exact text is used on-video. If not, **Claude watches sampled frames
   and writes the caption itself** (subject + caption are messaged to you).
2. The caption passes the eligibility check; warnings are forwarded.
3. The render queues (one at a time — parallel encodes can OOM the box)
   and a status message live-updates with the edit plan and progress.
4. **Claude reviews the rendered output** (hook, caption legibility,
   ending) and its verdict is attached to the reply.
5. The finished `.mp4` comes back as a **document** (no recompression),
   ready to upload to TikTok.

## Claude auth (subscription OAuth)

The judgment layer runs Claude Code headless (`claude -p`). On a dev
machine an existing `claude` login is enough. On a server, generate a
long-lived token from your subscription with `claude setup-token` and set
`CLAUDE_CODE_OAUTH_TOKEN` in the bot's environment. Set `TOKCUT_CLAUDE=off`
to disable the judgment layer entirely (filename captions, no review).

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
