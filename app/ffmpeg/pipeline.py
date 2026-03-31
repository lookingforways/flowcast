"""FFmpeg audiogram pipeline.

Builds and executes an FFmpeg command that composites:
  - A static background image (looped for the audio duration)
  - An animated waveform driven by the audio
  - Episode title text overlay
  - Optional duration indicator
  - Optional watermark / logo overlay

Output: 1920x1080 H.264/AAC MP4 optimised for YouTube.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from app.config import settings
from app.ffmpeg.escape import escape_drawtext, format_duration
from app.models.template import Template

logger = logging.getLogger(__name__)

VIDEO_W = 1920
VIDEO_H = 1080
FPS = 25


def _clamp(val: object, lo: int, hi: int) -> int:
    """Clamp a template numeric value to a safe range, preventing FFmpeg filter injection."""
    return max(lo, min(hi, int(val)))  # type: ignore[arg-type]


def _resolve_font(template: Template) -> str:
    """Return the font path to use, falling back to system default."""
    if template.title_font_path and Path(template.title_font_path).exists():
        return template.title_font_path
    # Try system font
    system = settings.default_font_path
    if Path(system).exists():
        return system
    # Last resort: let FFmpeg find a font itself (may fail on minimal systems)
    return ""


def build_filter_complex(
    template: Template,
    title: str,
    duration_secs: int | None,
    has_watermark: bool,
) -> str:
    """Return the -filter_complex string for the FFmpeg command."""
    font = _resolve_font(template)
    font_clause = f"fontfile='{font}':" if font else ""
    safe_title = escape_drawtext(title)

    parts: list[str] = []

    # ── 1. Scale background to 1920x1080 ────────────────────────────────────
    parts.append(f"[0:v]scale={VIDEO_W}:{VIDEO_H},setsar=1[bg]")

    # ── 2. Waveform from audio ───────────────────────────────────────────────
    ww = _clamp(template.waveform_w, 1, 3840)
    wh = _clamp(template.waveform_h, 1, 2160)
    wcolor = template.waveform_color.lstrip("#")

    if template.waveform_mode == "showfreqs":
        wave_filter = (
            f"[1:a]showfreqs="
            f"s={ww}x{wh}:"
            f"win_func=hann:"
            f"fscale=log:"
            f"colors=#{wcolor},"
            f"format=yuva420p[wave]"
        )
    else:
        wave_filter = (
            f"[1:a]showwaves="
            f"s={ww}x{wh}:"
            f"mode={template.waveform_mode}:"
            f"colors=#{wcolor}:"
            f"rate={FPS},"
            f"format=yuva420p[wave]"
        )
    parts.append(wave_filter)

    # ── 3. Overlay waveform on background ───────────────────────────────────
    wx = _clamp(template.waveform_x, 0, 3840)
    wy = _clamp(template.waveform_y, 0, 2160)
    parts.append(f"[bg][wave]overlay=x={wx}:y={wy}[comp1]")
    current = "comp1"

    # ── 4. Episode title drawtext ────────────────────────────────────────────
    title_drawtext = (
        f"[{current}]drawtext="
        f"{font_clause}"
        f"text='{safe_title}':"
        f"fontcolor={template.title_color}:"
        f"fontsize={_clamp(template.title_font_size, 8, 500)}:"
        f"x={_clamp(template.title_x, 0, 3840)}:"
        f"y={_clamp(template.title_y, 0, 2160)}:"
        f"line_spacing=4"
        f"[comp2]"
    )
    parts.append(title_drawtext)
    current = "comp2"

    # ── 5. Duration overlay (top-left corner) ───────────────────────────────
    if template.show_duration and duration_secs:
        dur_text = escape_drawtext(format_duration(duration_secs))
        dur_font = _resolve_font(template)
        dur_font_clause = f"fontfile='{dur_font}':" if dur_font else ""
        dur_drawtext = (
            f"[{current}]drawtext="
            f"{dur_font_clause}"
            f"text='{dur_text}':"
            f"fontcolor=#CCCCCC:"
            f"fontsize=36:"
            f"x=40:y=40"
            f"[comp3]"
        )
        parts.append(dur_drawtext)
        current = "comp3"

    # ── 6. Watermark overlay ─────────────────────────────────────────────────
    if has_watermark and template.watermark_path:
        wm_scale = _clamp(template.watermark_scale, 10, 1920)
        parts.append(
            f"[{current}]null[pre_wm];"
            f"[2:v]scale={wm_scale}:-1[wm_scaled];"
            f"[pre_wm][wm_scaled]overlay="
            f"x={_clamp(template.watermark_x, 0, 3840)}:"
            f"y={_clamp(template.watermark_y, 0, 2160)}"
            f"[out]"
        )
    else:
        parts.append(f"[{current}]null[out]")

    return ";".join(parts)


def build_ffmpeg_cmd(
    background_path: str | None,
    mp3_path: str,
    output_path: str,
    template: Template,
    title: str,
    duration_secs: int | None,
) -> list[str]:
    """Return the full FFmpeg argument list."""
    has_watermark = bool(template.watermark_path and Path(str(template.watermark_path)).exists())

    # Use bundled default background if none configured
    if background_path and Path(background_path).exists():
        bg = background_path
    else:
        bg = str(Path(__file__).parent.parent / "static" / "img" / "default_bg.png")

    filter_complex = build_filter_complex(template, title, duration_secs, has_watermark)

    cmd = [
        "ffmpeg", "-y",
        # Input 0: background image (looped)
        "-loop", "1", "-i", bg,
        # Input 1: audio
        "-i", mp3_path,
    ]

    if has_watermark:
        cmd += ["-i", str(template.watermark_path)]

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    return cmd


async def run_pipeline(
    mp3_path: str,
    output_path: str,
    template: Template,
    title: str,
    duration_secs: int | None,
) -> tuple[list[str], str]:
    """Execute the FFmpeg pipeline. Returns (cmd, stderr_log).

    Raises RuntimeError on non-zero FFmpeg exit code.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found in PATH. Install it with: apt-get install ffmpeg")

    bg = template.background_path if template.background_path else None
    cmd = build_ffmpeg_cmd(bg, mp3_path, output_path, template, title, duration_secs)

    cmd_str = " ".join(cmd)
    logger.info("FFmpeg command: %s", cmd_str)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    stderr_log = stderr.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        logger.error("FFmpeg failed (exit %d):\n%s", proc.returncode, stderr_log[-3000:])
        raise RuntimeError(
            f"FFmpeg exited with code {proc.returncode}. "
            f"Last output:\n{stderr_log[-1000:]}"
        )

    logger.info("FFmpeg completed successfully → %s", output_path)
    return cmd, stderr_log
