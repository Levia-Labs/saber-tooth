"""Pacing pass: thins vanilla light events so a lightshow never strobes.

Limits are stated in seconds and measured with the map timing, so tempo regions are honoured.
Thinning keeps events on strong beats (final lights-off, section starts and energy peaks,
downbeats, then weaker beats) and drops the weaker ones. A flash stays paired with the fade or
off that follows it in the input; a flash is never the last event of its group.
"""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from itertools import pairwise

from saber_tooth.model import BasicEvent
from saber_tooth.timing import Timing

LIGHT_GAP_S = 0.5  # per light group: minimum time between state changes
MAX_CHANGES_PER_S = 4.0  # all light groups together, averaged over WINDOW_S
WINDOW_S = 2.0
MAX_IN_WINDOW = int(MAX_CHANGES_PER_S * WINDOW_S)
MOTION_GAP_S = 1.0  # per group: minimum time between rotation / laser-speed events

LIGHT_TYPES = (0, 1, 2, 3, 4)
MOTION_TYPES = (8, 9, 12, 13)  # ring spin, ring zoom, left and right laser speed
COLOR_GROUPS = "lightColorEventBoxGroups"
MOTION_GROUPS = ("lightRotationEventBoxGroups", "lightTranslationEventBoxGroups")
EPS = 1e-6

Groups = dict[str, list[dict]]


@dataclass(frozen=True)
class Entry:
    ref: tuple  # ("e", index) or (group key, index)
    t: float
    beat: float
    lane: tuple
    light: bool
    state: str  # "off" | "flash" | "fade" | "other"


@dataclass
class Atom:
    entries: tuple[Entry, ...]
    strength: int
    alive: bool = True

    @property
    def start(self) -> float:
        return self.entries[0].t

    @property
    def end(self) -> float:
        return self.entries[-1].t


def _state(value: int) -> str:
    if value == 0:
        return "off"
    if value % 4 == 2:
        return "flash"
    if value % 4 == 3:
        return "fade"
    return "other"


def _entries(events: list[BasicEvent], groups: Groups, timing: Timing) -> list[Entry]:
    out = [
        Entry(
            ("e", i),
            timing.to_seconds(e.beat),
            e.beat,
            ("e", e.type),
            e.type in LIGHT_TYPES,
            _state(e.value),
        )
        for i, e in enumerate(events)
        if e.type in LIGHT_TYPES or e.type in MOTION_TYPES
    ]
    for key in (COLOR_GROUPS, *MOTION_GROUPS):
        for i, g in enumerate(groups.get(key, [])):
            beat = float(g.get("b", 0.0))
            out.append(
                Entry(
                    (key, i),
                    timing.to_seconds(beat),
                    beat,
                    (key, g.get("g", 0)),
                    key == COLOR_GROUPS,
                    "other",
                )
            )
    return out


def _near(x: float) -> bool:
    return abs(x - round(x)) < EPS


def _tier(beat: float, strong: set[int], final: int | None, off: bool = False) -> int:
    key = round(beat * 1000)
    if final is not None and key == final and off:
        return 5
    if final is not None and key == final:
        return 4
    if key in strong:
        return 4
    if _near(beat / 4):
        return 3
    return 2 if _near(beat / 2) else 1 if _near(beat) else 0


def _lane_atoms(lane: list[Entry], gap: float, tier) -> list[Atom]:
    """A flash with the fade or off right after it is one atom; a flash too close to it goes."""
    atoms: list[Atom] = []
    i = 0
    while i < len(lane):
        e = lane[i]
        nxt = lane[i + 1] if i + 1 < len(lane) else None
        if e.state == "flash" and nxt is not None and nxt.state in ("off", "fade"):
            if nxt.t - e.t >= gap - EPS:
                atoms.append(Atom((e, nxt), max(tier(e), tier(nxt))))
                i += 2
                continue
            i += 1  # flash dropped, the fade or off stays
            continue
        atoms.append(Atom((e,), tier(e)))
        i += 1
    return atoms


def _thin_lane(atoms: list[Atom], gap: float) -> None:
    stack: list[Atom] = []
    for a in atoms:
        while stack and a.start - stack[-1].end < gap - EPS:
            if a.strength > stack[-1].strength:
                stack.pop().alive = False
            else:
                a.alive = False
                break
        if a.alive:
            stack.append(a)


def _thin_window(atoms: list[Atom]) -> None:
    """At most MAX_IN_WINDOW light changes in any WINDOW_S; the weakest atom goes first."""
    events = sorted(
        ((e.t, k, a) for k, a in enumerate(atoms) for e in a.entries), key=lambda x: x[:2]
    )
    active: list[tuple[float, Atom]] = []
    for t, _, a in events:
        if not a.alive:
            continue
        active.append((t, a))
        while True:
            active = [(tt, x) for tt, x in active if x.alive and t - tt < WINDOW_S - EPS]
            if len(active) <= MAX_IN_WINDOW:
                break
            min(
                {id(x): x for _, x in active}.values(), key=lambda x: (x.strength, -x.start)
            ).alive = False


def _drop_trailing_flash(atoms: list[Atom]) -> None:
    by_lane: dict[tuple, list[Atom]] = defaultdict(list)
    for a in atoms:
        if a.alive:
            by_lane[a.entries[0].lane].append(a)
    for lane in by_lane.values():
        for last in sorted(lane, key=lambda a: a.end, reverse=True):
            if last.entries[-1].state != "flash":
                break
            last.alive = False


def pace_show(
    events: list[BasicEvent],
    groups: Groups,
    timing: Timing,
    strong_beats: Collection[float] = (),
    final_beat: float | None = None,
) -> tuple[list[BasicEvent], Groups]:
    """The events and box groups that survive the pacing limits; a subset of the input."""
    strong = {round(b * 1000) for b in strong_beats}
    final = None if final_beat is None else round(final_beat * 1000)

    def tier(e: Entry) -> int:
        return _tier(e.beat, strong, final, e.state == "off")

    lanes: dict[tuple, list[Entry]] = defaultdict(list)
    for e in sorted(_entries(events, groups, timing), key=lambda e: (e.t, e.ref[1])):
        lanes[e.lane].append(e)
    light: list[Atom] = []
    dropped: set[tuple] = set()
    for lane in lanes.values():
        gap = LIGHT_GAP_S if lane[0].light else MOTION_GAP_S
        atoms = _lane_atoms(lane, gap, tier)
        dropped |= {e.ref for e in lane} - {e.ref for a in atoms for e in a.entries}
        _thin_lane(atoms, gap)
        if lane[0].light:
            light.extend(atoms)
        else:
            dropped |= {e.ref for a in atoms if not a.alive for e in a.entries}
    _thin_window(light)
    _drop_trailing_flash(light)
    dropped |= {e.ref for a in light if not a.alive for e in a.entries}
    kept_events = [e for i, e in enumerate(events) if ("e", i) not in dropped]
    kept_groups = {
        k: [g for i, g in enumerate(v) if (k, i) not in dropped] for k, v in groups.items()
    }
    return kept_events, kept_groups


def _bad_windows(
    events: list[BasicEvent], groups: Groups, timing: Timing
) -> list[tuple[float, float, str]]:
    found: list[tuple[float, float, str]] = []
    lanes: dict[tuple, list[Entry]] = defaultdict(list)
    for e in sorted(_entries(events, groups, timing), key=lambda e: (e.t, e.ref[1])):
        lanes[e.lane].append(e)
    for lane in lanes.values():
        light = lane[0].light
        gap = LIGHT_GAP_S if light else MOTION_GAP_S
        what = (
            f"light group changes within {gap:g} s"
            if light
            else f"rotation or laser speed within {gap:g} s"
        )
        found += [(a.t, b.t, what) for a, b in pairwise(lane) if b.t - a.t < gap - EPS]
    every = sorted((e for lane in lanes.values() for e in lane if e.light), key=lambda e: e.t)
    lo = 0
    for hi, e in enumerate(every):
        while e.t - every[lo].t >= WINDOW_S - EPS:
            lo += 1
        if hi - lo + 1 > MAX_IN_WINDOW:
            found.append(
                (every[lo].t, e.t, f"more than {MAX_CHANGES_PER_S:g} light changes per second")
            )
    return found


def strobe_windows(
    events: list[BasicEvent], groups: Groups, timing: Timing
) -> list[tuple[float, float, str]]:
    """Merged (start beat, end beat, message) windows that break the pacing limits."""
    spans = sorted(
        (timing.to_beats(a), timing.to_beats(b), m)
        for a, b, m in _bad_windows(events, groups, timing)
    )
    merged: list[list] = []
    for a, b, m in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
            if m not in merged[-1][2]:
                merged[-1][2].append(m)
        else:
            merged.append([a, b, [m]])
    return [(a, b, "; ".join(ms)) for a, b, ms in merged]
