"""Valleys: the quiet stretches of a song where a crop may start or end.

A cut sits in a valley when the audio is low around it and few notes, summed over every
difficulty, fall near it; zero notes is best. Pure functions over 1 s bins.
"""

from itertools import accumulate

from saber_tooth.analysis import WEIGHTS, Analysis

NEAR_BINS = 2  # a cut is judged on the NEAR_BINS seconds on each side
TONAL_WEIGHT = 0.5  # bass, chord and melody onsets count half as much as a drum hit
AUDIO_REF_Q = 0.9  # the audio level a cut is compared with: the 90th percentile of the song


def audio_series(analysis: Analysis | None, duration_s: float) -> list[float]:
    """Weighted onsets per 1 s bin over the whole analysis; empty without one."""
    if analysis is None:
        return []
    n = max(1, int(duration_s) + 1)
    out = [0.0] * n
    sources = [(getattr(analysis, k), w) for k, w in WEIGHTS.items()]
    sources += [(getattr(analysis, k), TONAL_WEIGHT) for k in ("bass", "chords", "melody")]
    for times, weight in sources:
        for t in times:
            if 0 <= t < n:
                out[int(t)] += weight
    return out


def _span(pre: list[float], second: float) -> tuple[int, int]:
    n = len(pre) - 1
    c = round(second)
    return max(0, c - NEAR_BINS), min(n, c + NEAR_BINS)


def note_total(pre_notes: list[float], second: float) -> float:
    """Notes of every difficulty within NEAR_BINS seconds of the cut."""
    a, b = _span(pre_notes, second)
    return pre_notes[b] - pre_notes[a] if b > a else 0.0


def audio_level(pre_audio: list[float], second: float) -> float:
    """Mean audio energy per second around the cut."""
    a, b = _span(pre_audio, second)
    return (pre_audio[b] - pre_audio[a]) / (b - a) if b > a else 0.0


def audio_reference(audio: list[float]) -> float:
    """The loud-end level of the song, the scale a cut's audio level is read against."""
    if not audio:
        return 0.0
    s = sorted(audio)
    return s[min(len(s) - 1, int(AUDIO_REF_Q * len(s)))]


def cut_valley(
    pre_notes: list[float], pre_audio: list[float], audio_ref: float, second: float
) -> float:
    """1.0 for a cut with no notes near it and silent audio, falling to 0 as either rises."""
    notes = 1.0 / (1.0 + note_total(pre_notes, second))  # 0 notes 1.0, 1 note 0.5, 3 notes 0.25
    if not pre_audio or audio_ref <= 0:
        return notes
    quiet = 1.0 - min(1.0, audio_level(pre_audio, second) / audio_ref)
    return 0.5 * notes + 0.5 * quiet


def prefix(series: list[float]) -> list[float]:
    return [0.0, *accumulate(series)]
