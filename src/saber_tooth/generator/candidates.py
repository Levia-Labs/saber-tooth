import math
from dataclasses import dataclass

from saber_tooth.analysis import Analysis, onset_density
from saber_tooth.profiles import Profile
from saber_tooth.timing import Timing

BASE_SCORE = {"kick": 1.0, "snare": 0.9, "hh": 0.4}
BEAT_BONUS = 0.3
BAR_BONUS = 0.2
BAR_BEATS = 4.0
MAX_ENERGY = 1.5
EPS = 1e-6


@dataclass(frozen=True)
class Candidate:
    beat: float  # map beat
    rel: float  # beats since the first analysed beat
    score: float
    kick: bool


def phase_of(a: Analysis, timing: Timing) -> float:
    return timing.to_beats(a.beats[0]) if a.beats else 0.0


def bar_index(rel: float) -> int:
    return math.floor(rel / BAR_BEATS + EPS)


def build_candidates(
    a: Analysis, timing: Timing, profile: Profile, phase: float
) -> list[Candidate]:
    merged: dict[int, Candidate] = {}
    for kind, base in BASE_SCORE.items():
        for t in getattr(a, kind):
            rel = round((timing.to_beats(t) - phase) / profile.grid) * profile.grid
            if phase + rel < 0:
                continue
            score = base
            if abs(rel - round(rel)) < EPS:
                score += BEAT_BONUS
            if abs(rel / BAR_BEATS - round(rel / BAR_BEATS)) < EPS:
                score += BAR_BONUS
            key = round(rel * 1000)
            old = merged.get(key)
            kick = kind == "kick" or (old is not None and old.kick)
            best = max(score, old.score) if old else score
            merged[key] = Candidate(phase + rel, rel, best, kick)
    return sorted(merged.values(), key=lambda c: c.beat)


def bar_energies(a: Analysis, timing: Timing, phase: float, bars: range) -> dict[int, float]:
    dens = {
        b: onset_density(
            a,
            timing.to_seconds(phase + BAR_BEATS * b),
            timing.to_seconds(phase + BAR_BEATS * (b + 1)),
        )
        for b in bars
    }
    ordered = sorted(dens.values())
    p90 = ordered[int(0.9 * (len(ordered) - 1))] if ordered else 0.0
    if p90 <= 0:
        return dict.fromkeys(bars, 0.0)
    return {b: min(MAX_ENERGY, d / p90) for b, d in dens.items()}


def select(
    cands: list[Candidate], a: Analysis, timing: Timing, profile: Profile, phase: float
) -> tuple[list[Candidate], dict[int, float]]:
    """Per bar keep the best-scoring candidates up to the energy-scaled target."""
    if not cands:
        return [], {}
    by_bar: dict[int, list[Candidate]] = {}
    for c in cands:
        by_bar.setdefault(bar_index(c.rel), []).append(c)
    lo, hi = min(by_bar), max(by_bar)
    energy = bar_energies(a, timing, phase, range(lo, hi + 1))
    slots = int(BAR_BEATS / profile.grid)
    chosen: list[Candidate] = []
    for bar, items in by_bar.items():
        seconds = timing.to_seconds(phase + BAR_BEATS * (bar + 1))
        seconds -= timing.to_seconds(phase + BAR_BEATS * bar)
        target = profile.target_nps * seconds * (0.5 + energy[bar])
        n = min(int(target + 0.5), slots, len(items))
        chosen.extend(sorted(items, key=lambda c: (-c.score, c.beat))[:n])
    return sorted(chosen, key=lambda c: c.beat), energy
