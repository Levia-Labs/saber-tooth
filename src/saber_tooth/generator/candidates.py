import math
from dataclasses import dataclass, field

from saber_tooth.analysis import Analysis, onset_density
from saber_tooth.checks.constants import MIN_GAP_DENSITY
from saber_tooth.profiles import Profile
from saber_tooth.timing import Timing

BASE_SCORE = {"kick": 1.0, "snare": 0.9, "hh": 0.4}
BEAT_BONUS = 0.3
BAR_BONUS = 0.2
EIGHTH_BONUS = 0.1
FILLER_SCORE = 0.05
BAR_BEATS = 4.0
MAX_ENERGY = 1.5
EPS = 1e-6


@dataclass(frozen=True)
class Candidate:
    beat: float  # map beat
    rel: float  # beats since the first analysed beat
    score: float
    kick: bool
    filler: bool = False


@dataclass
class BarStats:
    energy: dict[int, float] = field(default_factory=dict)
    active: set[int] = field(default_factory=set)  # bars busy enough to need notes
    seconds: dict[int, float] = field(default_factory=dict)

    def active_seconds(self) -> float:
        return sum(self.seconds[b] for b in self.active)


def phase_of(a: Analysis, timing: Timing) -> float:
    return timing.to_beats(a.beats[0]) if a.beats else 0.0


def bar_index(rel: float) -> int:
    return math.floor(rel / BAR_BEATS + EPS)


def _on(value: float, step: float) -> bool:
    return abs(value / step - round(value / step)) < EPS


def _bonus(rel: float) -> float:
    bonus = BEAT_BONUS if _on(rel, 1.0) else (EIGHTH_BONUS if _on(rel, 0.5) else 0.0)
    if _on(rel, BAR_BEATS):
        bonus += BAR_BONUS
    # deterministic tie-break so equal-scored 16ths spread over the bar instead of bunching
    return bonus + (round(rel * 4) * 2654435761 % 997) / 997 * 0.02


def bar_stats(a: Analysis, timing: Timing, phase: float, bars: range) -> BarStats:
    stats = BarStats()
    dens = {}
    for b in bars:
        start = timing.to_seconds(phase + BAR_BEATS * b)
        end = timing.to_seconds(phase + BAR_BEATS * (b + 1))
        dens[b] = onset_density(a, start, end)
        stats.seconds[b] = end - start
        if dens[b] >= MIN_GAP_DENSITY:
            stats.active.add(b)
    ordered = sorted(dens.values())
    p90 = ordered[int(0.9 * (len(ordered) - 1))] if ordered else 0.0
    stats.energy = {b: min(MAX_ENERGY, d / p90) if p90 > 0 else 0.0 for b, d in dens.items()}
    return stats


def build_candidates(
    a: Analysis, timing: Timing, profile: Profile, phase: float
) -> tuple[list[Candidate], BarStats]:
    merged: dict[int, Candidate] = {}
    for kind, base in BASE_SCORE.items():
        for t in getattr(a, kind):
            rel = round((timing.to_beats(t) - phase) / profile.grid) * profile.grid
            if phase + rel < 0:
                continue
            key = round(rel * 1000)
            old = merged.get(key)
            score = base + _bonus(rel)
            kick = kind == "kick" or (old is not None and old.kick)
            merged[key] = Candidate(phase + rel, rel, max(score, old.score) if old else score, kick)
    if not merged:
        return [], BarStats()
    bars = [bar_index(c.rel) for c in merged.values()]
    stats = bar_stats(a, timing, phase, range(min(bars), max(bars) + 1))
    # Upper tiers: add low-score grid slots in busy bars so the target density is reachable.
    slots = round(BAR_BEATS / profile.grid)
    for b in stats.active:
        for i in range(slots):
            rel = BAR_BEATS * b + i * profile.grid
            key = round(rel * 1000)
            if key not in merged and phase + rel >= 0:
                score = FILLER_SCORE + _bonus(rel)
                merged[key] = Candidate(phase + rel, rel, score, False, True)
    return sorted(merged.values(), key=lambda c: c.beat), stats
