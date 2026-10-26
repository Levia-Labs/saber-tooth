import math
from dataclasses import dataclass

from saber_tooth.analysis import Analysis
from saber_tooth.checks import check_difficulty
from saber_tooth.generator.candidates import Candidate, build_candidates, phase_of
from saber_tooth.generator.motifs import Step, motif_steps, phrase_picks
from saber_tooth.generator.placer import GenerationError, Placer
from saber_tooth.generator.plan import BAR_BEATS, Event, plan_events
from saber_tooth.model import BpmEvent, Color, Difficulty
from saber_tooth.profiles import Profile
from saber_tooth.swings import Swing
from saber_tooth.timing import Timing

PHRASE_BEATS = 4 * BAR_BEATS
MAX_REPAIRS = 40


@dataclass
class GenerationStats:
    selected: int = 0  # notes the planner asked for
    placed: int = 0  # notes the placer could verify and keep
    filled: int = 0  # notes added to close empty gaps
    repaired: int = 0  # notes dropped after the final check
    final: int = 0

    @property
    def dropped(self) -> int:
        return self.selected - self.placed + self.repaired


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


def place_events(events: list[Event], placer: Placer, seed: int) -> int:
    state = MotifState(seed)
    placed = 0
    for i, ev in enumerate(events):
        next_s = events[i + 1].secs if i + 1 < len(events) else None
        for hand in ev.hands:
            # a single that does not fit its hand may still fit the other one
            order = [hand] if len(ev.hands) > 1 else [hand, Color(1 - hand)]
            for h in order:
                ordered = state.ordered(h, ev.rel)
                step = placer.try_add(h, ev.beat, ordered, next_s)
                if step is not None:
                    state.advance(h, ordered, step)
                    placed += 1
                    break
    return placed


def _insert(placer: Placer, c: Candidate, seed: int) -> bool:
    state = MotifState(seed)
    at = placer.timing.to_seconds(c.beat)
    for h in sorted(Color, key=lambda h: placer.last_secs(h, at)):
        if placer.try_add(h, c.beat, state.ordered(h, c.rel)) is not None:
            return True
    return False


def _fill_gaps(placer, cands, a, timing, profile, scope, seed) -> int:
    filled = 0
    for _ in range(MAX_REPAIRS):
        notes = placer.all_notes(with_context=True)
        diff = Difficulty(profile.name, profile.njs, profile.offset, notes=notes)
        gaps = [f for f in check_difficulty(diff, timing, profile, a, {"empty-gap"}) if scope(f)]
        progress = False
        for f in gaps:
            mid = (f.beat_start + f.beat_end) / 2
            inside = [c for c in cands if f.beat_start <= c.beat <= f.beat_end]
            for c in sorted(inside, key=lambda c: (abs(c.beat - mid), -c.score)):
                if _insert(placer, c, seed):
                    progress, filled = True, filled + 1
                    break
        if not progress:
            break
    return filled


def timing_events(timing: Timing) -> list[BpmEvent]:
    return [BpmEvent(beat, bpm) for beat, _, bpm in timing._segs[1:]]


def generate_with_stats(
    a: Analysis,
    timing: Timing,
    profile: Profile,
    seed: int,
    window: tuple[float, float] | None = None,
    entry: dict[Color, Swing] | None = None,
    exit: dict[Color, Swing] | None = None,
) -> tuple[Difficulty, GenerationStats]:
    phase = phase_of(a, timing)
    cands, bars = build_candidates(a, timing, profile, phase)
    if window is not None:
        cands = [c for c in cands if window[0] <= timing.to_seconds(c.beat) < window[1]]
        lo, hi = timing.to_beats(window[0]), timing.to_beats(window[1])
    else:
        lo, hi = -math.inf, math.inf
    context = [n for sw in [*(entry or {}).values(), *(exit or {}).values()] for n in sw.notes]
    last = {h: entry[h].seconds if entry and h in entry else -math.inf for h in Color}
    plan = plan_events(cands, bars, timing, profile, last)
    placer = Placer(timing, profile, context)
    stats = GenerationStats(selected=plan.selected)
    stats.placed = place_events(plan.events, placer, seed)

    def scope(f) -> bool:
        return f.beat_end > lo and f.beat_start < hi

    stats.filled = _fill_gaps(placer, cands, a, timing, profile, scope, seed)
    findings: list = []
    for _ in range(MAX_REPAIRS):
        diff = Difficulty(
            profile.name, profile.njs, profile.offset, notes=placer.all_notes(with_context=True)
        )
        findings = [f for f in check_difficulty(diff, timing, profile, a) if scope(f)]
        own = [f for f in findings if f.rule != "empty-gap" and set(f.notes) - placer.context]
        if not own:
            break
        drops = {max(set(f.notes) - placer.context) for f in own}
        stats.repaired += len(drops)
        kept = [n for n in placer.all_notes() if n not in drops]
        placer = Placer.from_notes(timing, profile, kept, context)
        stats.filled += _fill_gaps(placer, cands, a, timing, profile, scope, seed)
    else:
        raise GenerationError(f"{profile.name}: findings remain after repair: {findings[:3]}")
    if window is None and findings:
        raise GenerationError(f"{profile.name}: findings remain: {findings[:3]}")
    d = Difficulty(
        profile.name,
        profile.njs,
        profile.offset,
        notes=placer.all_notes(),
        bpm_events=timing_events(timing),
    )
    stats.final = len(d.notes)
    return d, stats


def generate_difficulty(*args, **kwargs) -> Difficulty:
    """Generate one difficulty. `window` is (start_s, end_s); `entry` and `exit` are the swings
    just before and after the window, modelled so the seams stay finding-free."""
    return generate_with_stats(*args, **kwargs)[0]
