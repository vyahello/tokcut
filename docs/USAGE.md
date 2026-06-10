# Using tokcut

## Quick start

```bash
cd ~/tkprop
tokcut YOUR_CLIP.MOV -c "Your caption text ⚡"      # if pip-installed
# or, without installing:
venv/bin/python3 -m tokcut YOUR_CLIP.MOV -c "Your caption text ⚡"
```

Output lands next to the input as `YOUR_CLIP_tokcut.mp4` unless you pass
`-o out.mp4`.

## Options

| Flag | Default | Meaning |
|------|---------|---------|
| `-c / --caption` | required | Persistent caption. Emoji supported (⚡🔥🧪💻…). Auto-balanced onto two lines. |
| `-o / --output` | `<input>_tokcut.mp4` | Output path. |
| `--target N` | none | Solve speed-ups so the result is ≈ N seconds. Without it, base speeds are used (dead 3.2x, lag 1.7x, action 1x). |
| `--caption-pos` | `auto` | `auto` builds a saliency map (motion + detail + brightness over the whole video) and places the caption over the calmest region inside the TikTok safe zone, so it never covers the screen/device. `top` pins it just below the top UI bar; `bottom` uses a letterboxed band below the video (legacy style — risks TikTok UI overlap). |
| `--music [FILE]` | off | Bare flag synthesizes a royalty-free track; pass a path to use your own audio. Mixed under the ambient sound. |
| `--music-style` | synthwave | `synthwave` or `phonk` (the darker, heavier pentesting vibe). |
| `--music-bpm N` | 84 | Tempo of the synthesized track. |
| `--crf N` | 18 | x265 quality (lower = better/bigger). 18 is visually lossless for screen content. |
| `--preset P` | medium | x265 preset. Use `fast` if you're in a hurry, `slow` for max quality. |
| `--dry-run` | off | Print the edit decision list (segments + speeds) and exit — no encode. |

## Recommended workflow

1. **Dry run first** to sanity-check the cut plan:
   ```bash
   venv/bin/python3 -m tokcut clip.MOV -c "..." --target 50 --dry-run
   ```
   You'll see which time ranges are kept at 1x (ACTION) vs fast-forwarded.
2. If the plan looks too aggressive/too soft, adjust `--target`
   (longer target = gentler speed-ups).
3. Render, check on your phone, post.

## Music: baked-in vs in-app

- **In-app TikTok sound (no `--music`)** ranks better — trending sounds
  drive discovery, and the app won't mute you for copyright. Default to this.
- **Baked-in (`--music`)** is for when you want the dark-synthwave/phonk
  vibe guaranteed, or to post the same clip off-platform. The track is
  synthesized (zero copyright risk) and ducked under your ambient audio.

## Picking a target duration

- TikTok sweet spot for this format: **35–60 s**.
- Rule of thumb: target ≈ 55 % of the raw duration for desk/screen footage.
- Don't go below ~35 % of raw length — fast-forward above ~5x starts to
  look like a glitch instead of a time-lapse.

## Caption guidelines (what works for the blog)

- Name the **exact tool + version + device**: "Flashing Bruce 1.15 on
  M5StickC Plus2 ⚡" — specificity reads as competence and is searchable.
- Keep it under ~40 characters so both lines stay big and readable.
- One caption for the whole video — no mid-video text changes.

### TikTok eligibility (avoid getting flagged or shadowbanned)

TikTok OCRs on-screen text and its moderation reacts to offensive-security
wording, especially combined with hacking-tool visuals. `tikedit` warns
automatically (`check_caption`) about risky terms — heed the warnings:

- **Avoid in captions**: hack/hacking/hacker, attack, exploit, deauth,
  crack, bypass, payload, spy, jam, steal, "free wifi".
- **Use instead**: flashing, firmware, modding, testing *my own* device,
  setup, tinkering. Descriptive beats edgy — "Flashing Bruce 1.15" is
  safe; "Hacking WiFi with this $30 device" risks removal under the
  criminal-activities policy.
- Same rule applies to the TikTok description/hashtags you type when
  posting: prefer #firmware #esp32 #m5stack #maker #cybersecurity
  (allowed, educational) over #hacked #wifihack type tags.
- Framing matters: "on my own gear / in my lab" keeps demos clearly
  educational, which is the carve-out TikTok's policy allows.

## Quality notes

- Output: 1080x1920, 60 fps, HEVC main10 (`hvc1`), HLG color preserved,
  AAC 192k audio, faststart. This survives TikTok's re-encode well.
- Encode time: roughly 2–4 minutes per 30 s of output on this machine
  with `--preset medium`.

## Troubleshooting

- **Washed-out colors** → the input probably wasn't iPhone HLG; the color
  tags in `tikedit.py:render()` are hardcoded for HLG sources. For SDR
  sources remove the three `-color_*` arguments.
- **Caption missing emoji** → the glyph isn't in Noto Color Emoji, or the
  char's codepoint is below U+2600 (the simple emoji detector threshold).
- **Too many tiny speed changes** → raise `MIN_SEG_SEC` in `tikedit.py`.
