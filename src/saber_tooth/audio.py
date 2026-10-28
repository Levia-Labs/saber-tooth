"""Audio encoding through ffmpeg."""

import subprocess  # nosec B404 - fixed ffmpeg argv, no shell
from pathlib import Path


class AudioError(Exception):
    """ffmpeg is missing or failed."""


def _run(argv: list[str]) -> None:
    try:
        subprocess.run(argv, check=True, capture_output=True)  # nosec B603 - list argv, no shell
    except FileNotFoundError as exc:
        raise AudioError("ffmpeg is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
        raise AudioError(f"ffmpeg failed: {detail}") from exc


def encode_egg(wav: Path, egg: Path) -> None:
    """Encode `wav` to Ogg Vorbis at `egg` (Beat Saber's .egg container)."""
    argv = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", str(egg),
    ]  # fmt: skip
    _run(argv)


def cut_egg(
    src: Path,
    dst: Path,
    start_s: float,
    length_s: float,
    lead_s: float,
    fade_in_s: float,
    fade_out_s: float,
) -> None:
    """Cut `length_s` seconds from `start_s`, put `lead_s` of silence before them, fade in at the
    music start and out over the last `fade_out_s`; Ogg Vorbis at `dst`."""
    filters = []
    if lead_s > 0:
        filters.append(f"adelay={round(lead_s * 1000)}:all=1")
    filters.append(f"afade=t=in:st={lead_s:.3f}:d={fade_in_s:.3f}")
    filters.append(f"afade=t=out:st={lead_s + length_s - fade_out_s:.3f}:d={fade_out_s:.3f}")
    argv = [
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start_s:.3f}", "-t", f"{length_s:.3f}",
        "-i", str(src), "-af", ",".join(filters),
        "-c:a", "libvorbis", "-q:a", "6", "-f", "ogg", str(dst),
    ]  # fmt: skip
    _run(argv)
