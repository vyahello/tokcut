# tokcut

Personal auto-editor that turns raw phone footage into tight, high-quality
vertical TikTok clips. Motion analysis drives speed-ramps (boring stretches
fast-forwarded, action kept real-time), a persistent styled caption is
auto-placed where it won't cover the action, and an optional synthesized
dark-synthwave / phonk track is mixed under the ambient audio.

Built for a personal hacker-gadget / maker blog (flashing firmware,
terminals, M5Stick, etc.).

## Install

```bash
python3 -m venv venv
venv/bin/pip install -e ".[dev]"   # needs ffmpeg + DejaVu/Noto fonts on the system
```

System requirements: `ffmpeg`/`ffprobe` with libx265, fonts
`fonts-dejavu` + `fonts-noto-color-emoji`.

## Use

```bash
# preview the cut plan (instant, no encode)
tokcut clip.MOV -c "Flashing Bruce 1.15 on M5StickC Plus2 ⚡" --target 50 --dry-run

# render, no music (you add a trending sound in TikTok)
tokcut clip.MOV -c "Flashing Bruce 1.15 on M5StickC Plus2 ⚡" --target 50

# render with a synthesized phonk track baked in
tokcut clip.MOV -c "Flashing Bruce 1.15 on M5StickC Plus2 ⚡" --target 50 --music --music-style phonk

# or your own audio file
tokcut clip.MOV -c "..." --music ~/tracks/mytrack.mp3
```

(`python -m tokcut ...` works too if you didn't `pip install`.)

## How it works

1. **Probe** the source (dimensions/rotation/fps/duration/audio).
2. **Motion analysis** — decode tiny grayscale frames at 6 fps, score by
   mean frame-to-frame difference.
3. **Classify** the timeline into dead / lag / action tiers (adaptive
   percentile thresholds; short runs merged so cuts feel intentional).
4. **Speeds** — action 1x, lag ≈1.7x, dead ≈3.2x; `--target N` solves the
   fast-tier speeds to land at N seconds.
5. **Caption** — Pillow renders purple bold-italic on rounded white boxes
   (emoji supported). A saliency map places it over the calmest region
   inside TikTok's UI safe zone, so it never covers the screen/device.
6. **Music** (optional) — `tokcut.music` synthesizes a royalty-free
   dark-synthwave/phonk track to exact length and ducks it under the
   ambient audio. Zero copyright risk.
7. **Render** — one ffmpeg `filter_complex`: per-segment trim/setpts +
   atempo, concat, lanczos scale into 1080x1920, caption overlay, encode
   **libx265 main10 crf 18** preserving the iPhone HLG color tags.

## Layout

```
tokcut/            package
  analysis.py        probe, motion scoring, saliency, edit decision list
  caption.py         caption rendering + TikTok-eligibility checks
  layout.py          canvas layout + saliency-aware caption placement
  music.py           procedural dark-synthwave/phonk generator
  render.py          ffmpeg filtergraph + encode
  cli.py             argparse entry point
tests/             pytest suite (logic-level, no GPU/network needed)
docs/              USAGE.md, IDEAS.md
.github/workflows/ CI (lint + test; deploy stage stubbed for the VPS)
```

## Develop

```bash
venv/bin/pytest          # run tests
venv/bin/ruff check .    # lint
```

## Roadmap

Phone → private Telegram bot → edited file back (approve / redo loop),
plus beat-aligned music cuts. See [`docs/IDEAS.md`](docs/IDEAS.md).

Licensed MIT.
