"""Claude Code judgment layer: caption writing and output review.

Division of labor: Python does everything deterministic (frame extraction,
prompts, parsing, validation); Claude Code — running headless on the
subscription OAuth token (`claude setup-token` → CLAUDE_CODE_OAUTH_TOKEN,
or an interactive login on a dev machine) — does the judgment: reading
the frames, deciding what the video shows, wording the caption, and
reviewing the rendered result.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

from .caption import MAX_CAPTION_CHARS, check_caption

CLAUDE_TIMEOUT_SEC = 240
FRAME_WIDTH = 640
N_FRAMES = 6


class JudgeUnavailable(RuntimeError):
    """Claude Code could not be invoked — caller should fall back."""


def claude_available() -> bool:
    return shutil.which("claude") is not None


# ------------------------------------------------------------ deterministic

def spread_times(duration: float, n: int = N_FRAMES,
                 margin: float = 0.05) -> list[float]:
    """N timestamps spread evenly through the video, edges skipped."""
    lo, hi = duration * margin, duration * (1 - margin)
    if n == 1 or hi <= lo:
        return [duration / 2]
    step = (hi - lo) / (n - 1)
    return [lo + i * step for i in range(n)]


def extract_frames(video: str, times: list[float], outdir: str,
                   width: int = FRAME_WIDTH) -> list[str]:
    """Decode one frame per timestamp as a small JPEG; returns paths."""
    paths = []
    for i, t in enumerate(times):
        out = os.path.join(outdir, f"frame_{i:02d}_t{t:.1f}s.jpg")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video,
             "-frames:v", "1", "-vf", f"scale={width}:-2", "-y", out],
            check=True)
        paths.append(out)
    return paths


def parse_json_obj(text: str) -> dict:
    """Extract the first JSON object from a (possibly chatty) reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON object in reply: {text[:200]!r}")
    return json.loads(match.group(0))


def pick_valid_caption(candidates: list[str]) -> str | None:
    """First candidate that passes the eligibility check and length cap."""
    for cand in candidates:
        cand = (cand or "").strip().strip('"')
        if cand and len(cand) <= MAX_CAPTION_CHARS and not check_caption(cand):
            return cand
    return None


# ----------------------------------------------------------------- claude

def run_claude(prompt: str,
               timeout: int = CLAUDE_TIMEOUT_SEC) -> str:
    """Run Claude Code headless; return its final text reply.

    Auth comes from the environment: CLAUDE_CODE_OAUTH_TOKEN (subscription
    token from `claude setup-token`) or an existing `claude` login.
    """
    if not claude_available():
        raise JudgeUnavailable("claude CLI not found on PATH")
    cmd = ["claude", "-p", prompt,
           "--output-format", "json",
           "--allowedTools", "Read"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise JudgeUnavailable(f"claude timed out after {timeout}s") from exc
    if res.returncode != 0:
        raise JudgeUnavailable(
            f"claude exited {res.returncode}: {res.stderr.strip()[-300:]}")
    try:
        envelope = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        raise JudgeUnavailable(
            f"unparseable claude output: {res.stdout[:200]!r}") from exc
    return str(envelope.get("result", ""))


CAPTION_PROMPT = """\
You are a professional TikTok video editor writing the on-video caption.

Read (view) these frames, sampled in chronological order from one video:
{frames}

1. Work out what the video shows — name the exact tool/app/subject if
   identifiable from UI text.
2. Write ONE caption that makes a viewer stop scrolling.

Hard rules for the caption:
- max {max_chars} characters, plain text, no hashtags, no quotes
- specific beats clever: name the thing ("btop — the terminal system
  monitor"), don't be vague ("check this out")
- no sensational or policy-risky wording (hack/hacking, attack, exploit,
  deauth, crack, bypass, spy, payload, steal, free wifi)
- at most one emoji, only at the end

Reply with ONLY a JSON object, no other text:
{{"subject": "<what the video shows, one line>",
 "caption": "<your best caption>",
 "alternatives": ["<option 2>", "<option 3>"]}}
"""


def suggest_caption(video: str, duration: float) -> tuple[str, str]:
    """Have Claude watch sampled frames and write the caption.

    Returns (caption, subject). Raises JudgeUnavailable / ValueError on
    failure — callers fall back to a deterministic caption.
    """
    tmp = tempfile.mkdtemp(prefix="tokcut_judge_")
    try:
        frames = extract_frames(video, spread_times(duration), tmp)
        prompt = CAPTION_PROMPT.format(
            frames="\n".join(frames), max_chars=MAX_CAPTION_CHARS - 4)
        reply = parse_json_obj(run_claude(prompt))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    candidates = [str(reply.get("caption", ""))]
    candidates += [str(a) for a in reply.get("alternatives", [])]
    caption = pick_valid_caption(candidates)
    if caption is None:
        raise ValueError(f"no eligible caption among {candidates!r}")
    return caption, str(reply.get("subject", ""))


REVIEW_PROMPT = """\
You are a professional TikTok editor reviewing a finished vertical
(1080x1920) edit before it is posted.

Read (view) these frames, sampled in chronological order from the
FINISHED video:
{frames}

The on-video caption should read: "{caption}"
The first frame listed IS the video's opening (the cold-open hook).

Check, strictly:
1. The caption is fully visible, legible, and not covering the action.
2. The opening frame works as a scroll-stopping hook (action, not setup).
3. The content itself is readable/judgeable at phone size.
4. The final frame ends on something worth seeing (not a desktop/cutoff).

The editor can fix: caption text, caption position, output length,
hook on/off, auto-zoom on/off. It cannot increase source resolution or
re-record. Say "redo" ONLY for problems those controls can fix; put
source-quality limitations in "notes" instead.

Reply with ONLY a JSON object, no other text:
{{"verdict": "approve" or "redo",
 "issues": ["<each concrete problem, if any>"],
 "notes": "<one-line overall impression>"}}
"""


def review_output(video: str, duration: float, caption: str) -> dict:
    """Have Claude review the rendered output. Returns the verdict dict."""
    tmp = tempfile.mkdtemp(prefix="tokcut_review_")
    try:
        # first sample inside the opening second — that's the hook frame
        times = [min(0.4, duration / 10)] + spread_times(
            duration, n=4, margin=0.2)
        frames = extract_frames(video, times, tmp)
        prompt = REVIEW_PROMPT.format(
            frames="\n".join(frames), caption=caption)
        reply = parse_json_obj(run_claude(prompt))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    verdict = str(reply.get("verdict", "")).lower()
    if verdict not in ("approve", "redo"):
        raise ValueError(f"unexpected verdict: {reply!r}")
    return {"verdict": verdict,
            "issues": [str(i) for i in reply.get("issues", [])],
            "notes": str(reply.get("notes", ""))}
