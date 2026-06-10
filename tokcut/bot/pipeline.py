"""Deterministic helpers the bot runs in-process — no Telegram, no Claude.

Thin wrappers over tokcut's analysis so the bot can show an edit plan
before any rendering. Rendering will hang off render.render() in step 2.
"""

from ..analysis import (
    assign_speeds,
    classify,
    motion_scores,
    probe,
    smooth,
    to_segments,
)
from ..types import SourceInfo, SpeedSegment


def dry_run_plan(
    input_path: str, target: float | None = None
) -> tuple[SourceInfo, list[SpeedSegment], float]:
    """Probe + score + solve speeds. Returns (src, segments, est_seconds)."""
    src = probe(input_path)
    raw_scores, _frames = motion_scores(input_path, src)
    segs, est = assign_speeds(
        to_segments(classify(smooth(raw_scores))), target)
    return src, segs, est


def format_plan(
    src: SourceInfo, segs: list[SpeedSegment], est: float
) -> str:
    """Render the edit decision list as a Telegram-friendly message."""
    lines = [
        f"📹 {src['w']}x{src['h']} · {src['duration']:.1f}s "
        f"@ {src['fps']:.0f}fps",
        f"✂️ {len(segs)} segments → ~{est:.1f}s output",
        "",
    ]
    for s, e, sp in segs:
        tag = "▶️ 1.00x" if round(sp, 2) == 1.0 else f"⏩ {sp:.2f}x"
        lines.append(f"`{s:6.1f}–{e:6.1f}`  {tag}")
    return "\n".join(lines)
