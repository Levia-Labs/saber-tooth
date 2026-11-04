from dataclasses import dataclass, field

from saber_tooth.checks.gaps import DEFAULT_REST_SPAN_S, REST_SPAN_S
from saber_tooth.generator.candidates import BAR_BEATS, BarStats, Candidate, bar_index
from saber_tooth.generator.placer import GAP_MARGIN_S
from saber_tooth.model import Color
from saber_tooth.profiles import Profile
from saber_tooth.timing import Timing

DOUBLE_ENERGY = 0.7
REST_AFTER_BARS = 16  # dense play longer than this many bars needs a rest zone
REST_LEAD = 0.75  # ... and so does play longer than this share of the tier's no-rest span
REST_MIN_BARS = 2
REST_MAX_BARS = 4
REST_NOTES_PER_BAR = 1  # a rest bar holds at most one note and no doubles
DOUBLE_BAR_STRIDE = 2  # doubles only on every second bar so they do not read as a fixed grid


@dataclass(frozen=True)
class Event:
    beat: float
    rel: float
    secs: float
    hands: tuple[Color, ...]


@dataclass
class HandState:
    last: dict[Color, float]
    tie: Color = Color.RED

    def copy(self) -> "HandState":
        return HandState(dict(self.last), self.tie)


@dataclass
class Plan:
    events: list[Event] = field(default_factory=list)
    selected: int = 0
    rests: list[tuple[int, int]] = field(default_factory=list)  # bar ranges [lo, hi)


def make_events(
    chosen: list[Candidate],
    energy: dict[int, float],
    timing: Timing,
    profile: Profile,
    state: HandState,
    rest: bool = False,
) -> list[Event]:
    """Alternate hands (older hand first, ties flip); doubles on loud kick bar starts."""
    gap = profile.warn.min_hand_gap_s + GAP_MARGIN_S
    events: list[Event] = []
    for c in chosen:
        s = timing.to_seconds(c.beat)
        ready = {h: s - state.last[h] >= gap for h in Color}
        bar = bar_index(c.rel)
        bar_start = abs(c.rel / BAR_BEATS - round(c.rel / BAR_BEATS)) < 1e-6
        loud = energy.get(bar, 0.0) > DOUBLE_ENERGY and bar % DOUBLE_BAR_STRIDE == 0
        if (
            profile.allow_doubles
            and not rest
            and c.kick
            and bar_start
            and loud
            and all(ready.values())
        ):
            hands: tuple[Color, ...] = (Color.RED, Color.BLUE)
        else:
            a, b = state.last[Color.RED], state.last[Color.BLUE]
            hand = state.tie if a == b else (Color.RED if a < b else Color.BLUE)
            if a == b:
                state.tie = Color(1 - state.tie)
            if not ready[hand]:
                continue
            hands = (hand,)
        for h in hands:
            state.last[h] = s
        events.append(Event(c.beat, c.rel, s, hands))
    return events


def _notes(events: list[Event]) -> int:
    return sum(len(e.hands) for e in events)


def plan_rests(stats: BarStats, profile: Profile, bars: list[int]) -> list[tuple[int, int]]:
    """Bar ranges to keep quiet: whenever dense play has run too long, the quietest 2-4 bars of
    the run (lowest audio energy, so a break or section boundary) become a rest zone."""
    limit = REST_LEAD * REST_SPAN_S.get(profile.name, DEFAULT_REST_SPAN_S)
    rests: list[tuple[int, int]] = []
    run: list[int] = []
    for bar in bars:
        if run and bar != run[-1] + 1:
            run = []
        run.append(bar)
        due = len(run) >= REST_AFTER_BARS or sum(stats.seconds[b] for b in run) >= limit
        if not due or len(run) < REST_MIN_BARS * 2:
            continue
        energy = [stats.energy[b] for b in run]
        starts = range(len(run) // 2, len(run) - REST_MIN_BARS + 1)
        i = min(starts, key=lambda k: (max(energy[k : k + REST_MIN_BARS]), -k))
        top = max(energy[i : i + REST_MIN_BARS])
        end = i + REST_MIN_BARS
        while end < min(len(run), i + REST_MAX_BARS) and energy[end] <= top:
            end += 1
        rests.append((run[i], run[end - 1] + 1))
        run = run[end:]
    return rests


def plan_events(
    cands: list[Candidate],
    stats: BarStats,
    timing: Timing,
    profile: Profile,
    last: dict[Color, float],
    span: tuple[float, float] | None = None,
) -> Plan:
    """Pick, per bar, the best candidates that fit the hand gaps, honouring the target nps."""
    plan = Plan()
    if not cands:
        return plan
    by_bar: dict[int, list[Candidate]] = {}
    for c in cands:
        by_bar.setdefault(bar_index(c.rel), []).append(c)
    factors = {b: 0.5 + stats.energy[b] for b in stats.energy}
    busy = [factors[b] for b in stats.active] or [1.0]
    mean = sum(busy) / len(busy)
    slots = round(BAR_BEATS / profile.grid)
    state = HandState(dict(last))
    carry = 0.0
    # planned over the whole song, so a window refill keeps the same rests as the full map
    plan.rests = plan_rests(stats, profile, sorted(stats.energy))
    resting = {b for lo, hi in plan.rests for b in range(lo, hi)}
    for bar in sorted(stats.energy):
        share = 1.0  # fraction of the bar inside the window; bars outside it are not planned
        if span is not None:
            share = (
                min(span[1], BAR_BEATS * (bar + 1)) - max(span[0], BAR_BEATS * bar)
            ) / BAR_BEATS
            if share <= 0:
                continue
        carry += profile.target_nps * stats.seconds[bar] * factors[bar] / mean * share
        want = min(int(carry + 0.5), slots)
        rest = bar in resting
        if rest:
            want = min(want, REST_NOTES_PER_BAR)
        chosen: list[Candidate] = []
        events: list[Event] = []
        for c in sorted(by_bar.get(bar, []), key=lambda c: (-c.score, c.beat)):
            if _notes(events) >= want:
                break
            trial = sorted([*chosen, c], key=lambda c: c.beat)
            trial_events = make_events(trial, stats.energy, timing, profile, state.copy(), rest)
            if len(trial_events) == len(trial):
                chosen, events = trial, trial_events
        events = make_events(chosen, stats.energy, timing, profile, state, rest)
        plan.events.extend(events)
        plan.selected += _notes(events)
        carry = max(-slots, min(slots / 2, carry - _notes(events)))
    return plan
