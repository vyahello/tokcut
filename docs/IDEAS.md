# Ideas: making these videos pop on TikTok

The niche — hacker-gadget / maker POV (flashing firmware, Kali, M5Stick,
Flipper-adjacent content) — performs very well on TikTok because the visuals
are inherently "forbidden-tech" aesthetic: dark room, glowing terminal,
purple device UI. Lean into that.

## Format playbook (what tikedit already does + what to add)

1. **Hook in the first 1.5 s** — never open on a static docs page.
   *Idea (next version):* `--hook` flag that finds the highest-motion or
   most colorful moment (e.g. the Bruce shark boot screen) and prepends
   1–1.5 s of it as a cold-open teaser before cutting to the start.
   "Watch the payoff first, then how I got there" massively lifts retention.
2. **Persistent specific caption** (done) — tool + version + device.
   Specificity = credibility = saves/shares from people who want to do it.
3. **Speed ramps instead of cuts** (done) — time-lapse feel keeps the
   process honest ("no fake, he really did it") which builds the trust you
   asked about. Viewers rewatch to catch details — that's the loop signal
   TikTok rewards.
4. **End on the win** — finish on the device working / green terminal
   output, not on reading docs. The current motion analysis usually does
   this naturally; a future `--end-on-action` flag could guarantee it.
5. **Loop-friendly ending** — if the last frame visually resembles the
   first (laptop + device on desk), the video loops seamlessly and TikTok
   counts the rewatch. Worth framing your shots with this in mind.

## Content ideas for the blog (series > one-offs)

- **"Flashing X on Y" series** — same caption template, same purple
  caption style every episode → instantly recognizable brand.
- **Before/after split** — 0.5 s of stock firmware UI → flash → Bruce UI.
- **"What this $30 device can do" follow-ups** — each Bruce feature
  (WiFi tools, IR, BadUSB demo *on your own gear*) is its own clip.
- **Fail clips** — a flash that bricks/errors and the recovery. Fail+fix
  outperforms clean success for engagement.
- Post 3–5 per week at consistent times; reply to every technical comment
  (comments are the strongest ranking signal in small niches).

## Trust & quality signals

- 10-bit HEVC + HLG preserved (done) — footage keeps the rich phone-camera
  look instead of going gray after upload.
- Real-time audio kept under speed-ups (done) — keyboard/device sounds
  read as authentic even under music.
- No AI voice-over, no stock transitions — raw POV is the brand.

## Roadmap: Telegram bot (the ideal workflow)

Goal: film on phone → share to Telegram bot → get back the edited file.

**Architecture (simple and sufficient):**

```
phone ──(video file, NOT photo-compressed)──> Telegram bot (python-telegram-bot)
   bot downloads file → asks for caption text (or takes it from the
   message caption) → runs tikedit.py → sends result back as *document*
```

**Conversation flow (owner-approved design):**

```
1. Owner uploads raw clip (as file/document)
2. Bot analyses it fully automatically:
     - motion edit plan (tikedit)
     - caption text (vision model reads the frames → "Flashing X on Y ⚡")
     - caption position (saliency auto-placement, already implemented)
3. Bot renders and sends the result back as a document
4. Owner reviews on the phone: [✅ Approve] [🔁 Redo]
     - Redo asks what to change (shorter/longer, different caption,
       caption elsewhere, more/less speed-up) via inline buttons,
       re-renders with adjusted params
```

Key implementation notes for when we build it:

- Use `python-telegram-bot` v21+, polling mode (no public server needed).
- **Always send/receive as `document`**, not `video` — Telegram re-compresses
  `video` uploads and would destroy the quality we worked for. Document
  uploads are bit-exact. Bot API file limit is 50 MB down / 2 GB up via a
  local Bot API server — a 95 s iPhone HEVC clip is ~250 MB, so we will
  need `telegram-bot-api` (local server) or have the phone trim/transcode
  first. Plan for the local Bot API server from day one.
- Inline keyboard for the approve/redo loop; keep the raw upload cached
  until approval so redos don't need a re-upload.
- Queue renders (one at a time) — x265 is CPU-heavy.
- Allow-list your own Telegram user ID; this bot should be private.

## Roadmap: automatic audio (cybersecurity / pentesting vibe)

Owner wants the bot to eventually set music too. Two realities to balance:

- **In-app TikTok sounds rank better** — trending sounds feed discovery
  and "use this sound" traffic, and commercial tracks added outside the
  app can get the video muted by copyright detection.
- **Baked-in audio saves time** and lets us sync edits to the beat.

Plan:

1. Maintain a local library of **royalty-free dark synthwave / phonk /
   cyberpunk tracks** (the pentesting aesthetic), tagged by BPM and mood.
2. Bot picks a track matching the clip duration/energy, mixes it under
   the ambient audio (music ~ -8 dB, ambient keyboard sounds kept low —
   authenticity signal).
3. **Beat-aligned editing** (the killer feature): snap speed-ramp segment
   boundaries to the track's beat grid, so cuts land on the beat —
   instantly looks professionally edited.
4. Approve/redo flow gets a [🎵 Change track] button; "no music" stays
   an option for posts where a trending in-app sound is the better play.

**Stretch ideas:**

- Auto-caption suggestion: OCR a few frames (tesseract) to detect the tool
  name/version on screen and propose the caption automatically.
- `--hook` cold-open (see above) as a bot toggle.
- Auto-generate 3 caption/hashtag suggestions per upload.
- Optional 1.05x micro speed-up of ACTION segments — keeps perceived pace
  high without looking sped-up (common pro-editor trick).
