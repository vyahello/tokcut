# Design proposal: Claude-orchestrated Telegram editing bot

Status: **proposal / analysis** — not built yet. This documents the target
architecture for the "film → Telegram → Claude edits → approve/redo" loop.

## The one idea that makes this work

**Claude directs and critiques; `tokcut` + ffmpeg execute.**

`tokcut` already does the deterministic, expensive work — motion scoring,
cut detection, speed-ramps, caption rendering, encoding — fast, free, and
reproducibly. Claude is slower and costs tokens per call, so it must not
re-derive any of that. Claude's job is the part code can't do well:

| Claude (judgment) | Deterministic code (`tokcut`) |
|---|---|
| Read frames → understand what's happening → **write the caption** | Motion analysis, tier classification, cut points |
| Run `check_caption` reasoning + pick safe wording | Speed solving to hit `--target` |
| Pick the **hook** moment (most striking frame) | Caption rendering + saliency placement |
| **Review the rendered output** and fix mistakes | 10-bit HEVC encode, HLG color |
| Turn NL "redo" feedback → concrete param changes | The hard `check_caption` eligibility gate |

This division is what keeps it cheap and reliable. Claude orchestrates a
deterministic tool; it doesn't hand-edit pixels.

## Surface: Claude API + tool use (self-hosted on the VPS)

Two Anthropic surfaces exist: **Claude API + tool use** (you host the
compute and define the tools) and **Managed Agents** (Anthropic hosts a
container where tools run). For this pipeline the answer is clearly the
former, because:

- The source clips are large (a 95 s iPhone HEVC clip is ~250 MB) and
  `ffmpeg`/`x265` must run where the file lives — your VPS — not inside
  Anthropic's sandbox.
- The tool surface is small and well-defined (run `tokcut`, extract
  frames, send to Telegram).

So: a Python service on the VPS holds the Telegram connection **and** the
Anthropic client, exposes a few tools, and runs the agent loop (SDK tool
runner, or a manual loop for human-in-the-loop gating). Default model
`claude-opus-4-8` with adaptive thinking.

### Tool surface Claude gets

Constrained, typed tools — **not** raw bash — so the harness validates
every action:

| Tool | Does | Returns |
|---|---|---|
| `analyze_plan(target)` | `tokcut --dry-run` | edit decision list (JSON) |
| `extract_frames(timestamps[])` | ffmpeg keyframes | images for Claude to view |
| `render(caption, target, caption_pos, music, keep_audio)` | `tokcut` | output path |
| `inspect_output()` | frames from the *rendered* file | images — for self-review |
| `send_to_telegram(file, message)` | deliver as **document** | delivery status |

`render` validates its args (clamps target, runs `check_caption` as a hard
gate) regardless of what Claude proposes — Claude proposes, code disposes.

## The loop

```
1. You upload a clip to the bot (as a file/document, not video).
2. Bot starts a Claude conversation:
     system = "You are a TikTok editor. Produce a post-worthy vertical clip.
               Use the tools. Verify your own output before sending."
3. Claude: extract_frames + analyze_plan → reason → decide caption + target
   → render → inspect_output → critique → maybe re-render (bounded) →
   send_to_telegram.
4. You tap [✅ Approve] or [🔁 Redo].
5. Redo text is appended to the SAME conversation (multi-turn), so Claude
   has full context of what it did and why → it adjusts params → re-renders.
```

The "review your own output" step (`inspect_output` → critique) is what
"make it more reliable" actually means: Claude looks at the rendered frames
and catches a chopped reveal or a mis-worded caption *before* you ever see
it. Bound re-renders (e.g. max 2) to cap latency/cost.

## Auth: "claude code via oauth" vs API key

Both work. The honest tradeoff:

- **Subscription OAuth** (your Claude Max plan, via `ant auth login` /
  Claude Code's `setup-token`): no per-token bill. But interactive OAuth
  login is designed for **dev machines**; for an always-on server
  Anthropic's documented path is Workload Identity Federation, and running
  a personal subscription token in an automated bot is a gray area worth
  checking against current terms.
- **API key**: unambiguous for programmatic/server use, pay-as-you-go.

**Recommendation: start with an API key.** The volume here is tiny — a few
Claude calls per video, each viewing ~10 small frames — so cost is roughly
**$0.30–0.50 per video** on `claude-opus-4-8` (less with prompt caching of
the system prompt). That's cheap enough that the API key's reliability and
clean ToS story beat the subscription's "free" tokens. We can switch to
profile-based OAuth later if you'd rather burn Max-plan quota — the SDK
honors `ant auth login` profiles, so it's a config change, not a rewrite.

## Reliability & safety

- **Allow-list your Telegram user ID** — the bot is private.
- **Constrained tools, not bash** — Claude can only run `tokcut` with
  validated arguments; it can't run arbitrary commands on the VPS.
- **`check_caption` stays a hard gate** in `render`, independent of Claude.
- **Secrets in env / a secrets manager** on the VPS, never in the repo.
- **Send/receive as `document`** — `video` uploads get re-compressed by
  Telegram. Files >50 MB need a local Bot API server (see IDEAS.md).
- **Bounded self-review** — cap re-renders so a critique loop can't run
  away on cost or time.

## Honest limitations (don't oversell)

- **Claude can't watch video — only frames.** ffmpeg decodes keyframes to
  images; Claude reasons over those. So the deterministic motion analysis
  stays the source of truth for *where* to cut; Claude judges *whether* the
  plan looks right and owns caption/hook decisions. Don't expect Claude to
  pick frame-exact cut points by "watching."
- **Latency is real** — x265 encodes take minutes; plus Claude round-trips.
  The async approve/redo design already absorbs this, but it's not instant.
- **Non-deterministic wording** — Claude may phrase the caption differently
  run to run. Fine here; pin with low effort if you want stability.

## Build order (when we start)

1. Bot skeleton: `python-telegram-bot`, allow-list, receive document.
2. Wrap `tokcut` calls as the tool functions above.
3. Wire the Anthropic client + tool loop (API key).
4. Approve/redo inline keyboard + multi-turn session continuity.
5. Local Bot API server for >50 MB files.
6. (Later) auto-music, beat-aligned cuts, OAuth-profile auth if wanted.
