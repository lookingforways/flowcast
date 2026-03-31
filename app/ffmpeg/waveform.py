"""Python-based waveform renderer for audiogram overlays.

Replaces FFmpeg's showwaves with a higher-quality renderer that uses FFT
frequency analysis and Pillow to draw smooth, symmetric bars with glow.
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ── Constants ────────────────────────────────────────────────────────────────
_SAMPLE_RATE = 44100
_N_BARS = 64
_BAR_GAP = 0.25        # fraction of bar slot used as gap
_SMOOTHING = 0.55      # temporal smoothing (0 = none, closer to 1 = more smooth)
_MIN_H_RATIO = 0.04    # minimum bar height as fraction of total height
_GLOW_SIGMA = 5        # gaussian blur radius for glow effect
_GLOW_ALPHA = 55       # glow transparency (0-255)


# ── Audio loading ─────────────────────────────────────────────────────────────

def _load_pcm(mp3_path: str) -> np.ndarray:
    """Decode audio to mono float32 PCM via FFmpeg."""
    result = subprocess.run(
        [
            "ffmpeg", "-i", mp3_path,
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "-ar", str(_SAMPLE_RATE),
            "-ac", "1",
            "-",
        ],
        capture_output=True,
    )
    return np.frombuffer(result.stdout, dtype=np.float32)


# ── Frequency analysis ────────────────────────────────────────────────────────

def _fft_size(samples_per_frame: int) -> int:
    """Next power of 2 >= samples_per_frame * 4, capped at 8192."""
    n = samples_per_frame * 4
    n = 1 << (n - 1).bit_length()
    return min(n, 8192)


def _compute_bars(
    audio: np.ndarray,
    frame_idx: int,
    samples_per_frame: int,
    fft_size: int,
) -> np.ndarray:
    """Return N_BARS amplitude values for this frame using log-spaced FFT bands."""
    center = frame_idx * samples_per_frame + samples_per_frame // 2
    half = fft_size // 2
    start = max(0, center - half)
    end = min(len(audio), start + fft_size)
    chunk = audio[start:end]

    if len(chunk) < 64:
        return np.zeros(_N_BARS)

    # Zero-pad to fft_size and apply Hanning window
    padded = np.zeros(fft_size, dtype=np.float32)
    padded[: len(chunk)] = chunk
    padded *= np.hanning(fft_size)

    spectrum = np.abs(np.fft.rfft(padded))
    n_bins = len(spectrum)

    # Log-spaced band edges (skip DC at index 0)
    edges = np.logspace(np.log10(2), np.log10(n_bins - 1), _N_BARS + 1).astype(int)
    edges = np.clip(edges, 1, n_bins - 1)

    bars = np.array([
        np.mean(spectrum[edges[i] : max(edges[i] + 1, edges[i + 1])])
        for i in range(_N_BARS)
    ])

    # Square-root compression for more natural visual dynamics
    return np.sqrt(bars)


# ── Frame rendering ───────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _render_frame(
    amps: np.ndarray,
    width: int,
    height: int,
    color: tuple[int, int, int],
) -> bytes:
    """Draw symmetric bars with rounded caps and a glow layer. Returns raw RGBA bytes."""
    r, g, b = color
    bar_slot = width / _N_BARS
    bar_w = max(2.0, bar_slot * (1.0 - _BAR_GAP))
    cy = height // 2
    min_h = max(3, int(height * _MIN_H_RATIO))
    radius = max(1, int(bar_w / 2))

    # ── Glow layer ──────────────────────────────────────────────────────────
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i, amp in enumerate(amps):
        bh = max(min_h, int(amp * height * 0.46))
        x0 = int(i * bar_slot + (bar_slot - bar_w) / 2) - 4
        x1 = x0 + int(bar_w) + 8
        gd.rounded_rectangle(
            [x0, cy - bh - 4, x1, cy + bh + 4],
            radius=radius + 4,
            fill=(r, g, b, _GLOW_ALPHA),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=_GLOW_SIGMA))

    # ── Bar layer ────────────────────────────────────────────────────────────
    bars = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bars)
    for i, amp in enumerate(amps):
        bh = max(min_h, int(amp * height * 0.46))
        x0 = int(i * bar_slot + (bar_slot - bar_w) / 2)
        x1 = x0 + int(bar_w)
        bd.rounded_rectangle(
            [x0, cy - bh, x1, cy + bh],
            radius=radius,
            fill=(r, g, b, 255),
        )

    return Image.alpha_composite(glow, bars).tobytes()


# ── Main entry point ──────────────────────────────────────────────────────────

def _generate_sync(
    mp3_path: str,
    width: int,
    height: int,
    fps: int,
    color_hex: str,
) -> str:
    """Render waveform overlay to a lossless MKV. Returns the temp file path."""
    audio = _load_pcm(mp3_path)
    duration = len(audio) / _SAMPLE_RATE
    n_frames = max(1, int(duration * fps))
    spf = max(1, len(audio) // n_frames)
    fft_sz = _fft_size(spf)
    color = _hex_to_rgb(color_hex)

    tmp = tempfile.NamedTemporaryFile(suffix=".mkv", delete=False)
    out_path = tmp.name
    tmp.close()

    proc = subprocess.Popen(
        [
            "ffmpeg", "-y",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgba",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "ffv1",
            out_path,
        ],
        stdin=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    prev_amps = np.zeros(_N_BARS)
    for fi in range(n_frames):
        raw = _compute_bars(audio, fi, spf, fft_sz)
        peak = raw.max()
        if peak > 0:
            raw /= peak
        # Temporal smoothing
        amps = _SMOOTHING * prev_amps + (1.0 - _SMOOTHING) * raw
        prev_amps = amps.copy()

        proc.stdin.write(_render_frame(amps, width, height, color))

    proc.stdin.close()
    proc.wait()
    return out_path


async def generate_waveform_overlay(
    mp3_path: str,
    width: int,
    height: int,
    fps: int,
    color_hex: str,
) -> str:
    """Async entry point. Returns a temp MKV path to use as FFmpeg overlay input."""
    return await asyncio.to_thread(_generate_sync, mp3_path, width, height, fps, color_hex)
