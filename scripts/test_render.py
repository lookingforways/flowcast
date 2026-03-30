"""Smoke test for the FFmpeg pipeline.

Generates a short test audio with FFmpeg's lavfi source, then renders
a full audiogram. Run from the project root:

    python scripts/test_render.py

Requires: ffmpeg in PATH, Python dependencies installed.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Minimal .env for the test
os.environ.setdefault("RSS_FEED_URL", "")
os.environ.setdefault("GOOGLE_CLIENT_ID", "")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "")
os.environ.setdefault("DATA_DIR", "/tmp/flowcast_test")

from app.config import settings
from app.ffmpeg.pipeline import run_pipeline
from app.models.template import Template


async def main() -> None:
    settings.ensure_dirs()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate a 10-second test audio using FFmpeg lavfi
        test_mp3 = Path(tmpdir) / "test_audio.mp3"
        output_mp4 = Path(tmpdir) / "test_output.mp4"

        print("Generating test audio (10 seconds)...")
        gen_proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(test_mp3),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await gen_proc.communicate()
        if gen_proc.returncode != 0:
            print("Failed to generate test audio:")
            print(stderr.decode())
            return

        print(f"Test audio: {test_mp3} ({test_mp3.stat().st_size} bytes)")

        # Create a minimal template object (not saved to DB)
        tmpl = Template(
            id=1,
            name="Test Template",
            is_default=True,
            background_path=None,  # Use default background
            waveform_color="#00FF88",
            waveform_mode="cline",
            waveform_x=0,
            waveform_y=810,
            waveform_w=1920,
            waveform_h=270,
            title_color="#FFFFFF",
            title_font_size=64,
            title_x="(w-text_w)/2",
            title_y=680,
            show_duration=True,
        )

        print("Running FFmpeg pipeline...")
        try:
            cmd, log = await run_pipeline(
                mp3_path=str(test_mp3),
                output_path=str(output_mp4),
                template=tmpl,
                title="Test Episode: Hello World!",
                duration_secs=600,
            )
            size_mb = output_mp4.stat().st_size / 1_048_576
            print(f"\nSUCCESS! Output: {output_mp4} ({size_mb:.1f} MB)")
            print(f"Command: {' '.join(cmd[:6])}...")
        except Exception as exc:
            print(f"\nFAILED: {exc}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
