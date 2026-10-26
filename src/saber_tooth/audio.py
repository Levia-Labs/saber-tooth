"""Audio encoding through ffmpeg."""

import subprocess
from pathlib import Path


class AudioError(Exception):
    """ffmpeg is missing or failed."""


def encode_egg(wav: Path, egg: Path) -> None:
    """Encode `wav` to Ogg Vorbis at `egg` (Beat Saber's .egg container)."""
    argv = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", str(egg),
    ]  # fmt: skip
    try:
        subprocess.run(argv, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise AudioError("ffmpeg is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
        raise AudioError(f"ffmpeg failed: {detail}") from exc
