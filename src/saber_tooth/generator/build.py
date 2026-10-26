import math
from dataclasses import dataclass

from saber_tooth.analysis import Analysis
from saber_tooth.checks import check_difficulty
from saber_tooth.generator.candidates import (
    BAR_BEATS,
    Candidate,
    bar_index,
    build_candidates,
    phase_of,
    select,
)
from saber_tooth.generator.motifs import Step, motif_steps, phrase_picks
from saber_tooth.generator.placer import GAP_MARGIN_S, GenerationError, Placer
from saber_tooth.model import Color, Difficulty
from saber_tooth.profiles import Profile
from saber_tooth.swings import Swing
from saber_tooth.timing import Timing

PHRASE_BEATS = 4 * BAR_BEATS
DOUBLE_ENERGY = 0.7
MAX_REPAIRS = 40


@dataclass(frozen=True)
class Event:
    beat: float
    rel: float
    secs: float
    hands: tuple[Color, ...]


class MotifState:
    """Per-hand position inside the phrase motif; seeded per phrase, mirrored in the 2nd half."""

    def __init__(self, seed: int):
        self.seed = seed
        self.phrase: dict[Color, int | None] = {Color.RED: None, Color.BLUE: None}
        self.k = {Color.RED: 0, Color.BLUE: 0}
        self._picks: dict[int, dict[Color, int]] = {}

    def steps(self, hand: Color, rel: float) -> tuple[Step, ...]:
        phrase = math.floor(rel / PHRASE_BEATS)
        if phrase not in self._picks:
            self._picks[phrase] = phrase_picks(self.seed, phrase)
        if self.phrase[hand] != phrase:
            self.phrase[hand], self.k[hand] = phrase, 0
        second_half = rel - phrase * PHRASE_BEATS >= PHRASE_BEATS / 2
        return motif_steps(hand, self._picks[phrase][hand], second_half)

    def ordered(self, hand: Color, rel: float) -> list[Step]:
        steps = self.steps(hand, rel)
        return [steps[(self.k[hand] + i) % len(steps)] for i in range(len(steps))]

    def advance(self, hand: Color, ordered: list[Step], chosen: Step) -> None:
        if chosen in ordered:
            self.k[hand] = (self.k[hand] + ordered.index(chosen) + 1) % len(ordered)


def make_events(
    chosen: list[Candidate],
    energy: dict[int, float],
    timing: Timing,
    profile: Profile,
    last: dict[Color, float],
) -> list[Event]:
    """Alternate hands (older hand first); doubles on loud kick bar starts."""
    gap = profile.warn.min_hand_gap_s + GAP_MARGIN_S
    last = dict(last)
    events: list[Event] = []
    for c in chosen:
        s = timing.to_seconds(c.beat)
        ready = {h: s - last[h] >= gap for h in Color}
        bar_start = abs(c.rel / BAR_BEATS - round(c.rel / BAR_BEATS)) < 1e-6
        loud = energy.get(bar_index(c.rel), 0.0) > DOUBLE_ENERGY
        if profile.allow_doubles and c.kick and bar_start and loud and all(ready.values()):
            hands: tuple[Color, ...] = (Color.RED, Color.BLUE)
        else:
            hand = min(Color, key=lambda h: (last[h], h))
            if not ready[hand]:
                continue
            hands = (hand,)
        for h in hands:
            last[h] = s
        events.append(Event(c.beat, c.rel, s, hands))
    return events


def place_events(events: list[Event], placer: Placer, seed: int) -> None:
    state = MotifState(seed)
    for i, ev in enumerate(events):
        next_s = events[i + 1].secs if i + 1 < len(events) else None
        for hand in ev.hands:
            order = [hand] if len(ev.hands) > 1 else sorted(Color, key=placer.last_secs)
            for h in order:
                ordered = state.ordered(h, ev.rel)
                step = placer.try_add(h, ev.beat, ordered, next_s)
                if step is not None:
                    state.advance(h, ordered, step)
                    break


def _in_window(f, lo_beat: float, hi_beat: float) -> bool:
    return f.beat_start >= lo_beat - 1e-9 and f.beat_end <= hi_beat + 1e-9


def _fill_gaps(placer, make, cands, a, timing, profile, scope) -> None:
    for _ in range(MAX_REPAIRS):
        gaps = [f for f in check_difficulty(make(), timing, profile, a, {"empty-gap"}) if scope(f)]
        progress = False
        for f in gaps:
            mid = (f.beat_start + f.beat_end) / 2
            inside = [c for c in cands if f.beat_start <= c.beat <= f.beat_end]
            for c in sorted(inside, key=lambda c: (abs(c.beat - mid), -c.score)):
                if _insert(placer, c):
                    progress = True
                    break
        if not progress:
            return


def _insert(placer: Placer, c: Candidate) -> bool:
    state = MotifState(0)
    for h in sorted(Color, key=placer.last_secs):
        if placer.try_add(h, c.beat, state.ordered(h, c.rel)) is not None:
            return True
    return False


def generate_difficulty(
    a: Analysis,
    timing: Timing,
    profile: Profile,
    seed: int,
    window: tuple[float, float] | None = None,
    entry: dict[Color, Swing] | None = None,
) -> Difficulty:
    """Generate one difficulty. `window` is (start_s, end_s) in seconds; `entry` seeds the hands."""
    phase = phase_of(a, timing)
    cands = build_candidates(a, timing, profile, phase)
    chosen, energy = select(cands, a, timing, profile, phase)
    if window is not None:
        inwin = [c for c in cands if window[0] <= timing.to_seconds(c.beat) < window[1]]
        chosen = [c for c in chosen if c in inwin]
        cands = inwin
        lo, hi = timing.to_beats(window[0]), timing.to_beats(window[1])
    else:
        lo, hi = -math.inf, math.inf

    def scope(f) -> bool:
        return _in_window(f, lo, hi)

    placer = Placer(timing, profile, entry)
    last = {h: placer.last_secs(h) for h in Color}
    place_events(make_events(chosen, energy, timing, profile, last), placer, seed)

    def make() -> Difficulty:
        return Difficulty(profile.name, profile.njs, profile.offset, notes=placer.all_notes())

    _fill_gaps(placer, make, cands, a, timing, profile, scope)
    for _ in range(MAX_REPAIRS):
        findings = [f for f in check_difficulty(make(), timing, profile, a) if scope(f)]
        if not findings:
            return make()
        drops = {max(f.notes) for f in findings if f.rule != "empty-gap" and f.notes}
        if drops:
            kept = [n for n in placer.all_notes() if n not in drops]
            placer = Placer.from_notes(timing, profile, kept, entry)
        _fill_gaps(placer, make, cands, a, timing, profile, scope)
    raise GenerationError(f"{profile.name}: findings remain after repair: {findings[:3]}")
