import copy
import random
from dataclasses import dataclass

from saber_tooth.analysis import Analysis
from saber_tooth.lightshow.energy import bar_energy, last_note_beat
from saber_tooth.lightshow.units import BAR, Templates, Unit
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import BasicEvent, Beatmap, ColorScheme
from saber_tooth.timing import Timing

SECTION_BLOCK = 4
SECTION_JUMP = 0.25
HIGH, LOW = 0.7, 0.4
LOW_UNIT_MAX, FADE_UNIT_MAX = 0.5, 0.3
FADE_BARS = 2
OFF_AFTER = 2.0
LIGHT_TYPES = (0, 1, 2, 3, 4)
DONOR_CHOICES = 3

Events = tuple[list[BasicEvent], list[tuple[float, bool]], dict[str, list]]


@dataclass(frozen=True)
class LightshowPayload:
    environment: str
    color_scheme: ColorScheme | None
    events: dict[str, Events]


def _require(t: Templates) -> None:
    if not any(t.units.values()):
        raise ValueError("no lightshow templates; run learn first")


def choose_environment(t: Templates, seed: int) -> str:
    _require(t)
    ranked = sorted(((len(u), e) for e, u in t.units.items() if u), key=lambda x: (-x[0], x[1]))
    return random.Random(seed).choice([e for _, e in ranked[:3]])  # noqa: S311 # nosec B311 - seeded layout choice, not security


def _sections(energy: list[float]) -> list[tuple[int, int]]:
    """Half-open bar ranges; a full 4-bar mean jump of >= 0.25 starts a new section.

    A trailing block shorter than 4 bars never starts a section; it joins the previous one.
    """
    blocks = [energy[i : i + SECTION_BLOCK] for i in range(0, len(energy), SECTION_BLOCK)]
    means = [sum(b) / len(b) for b in blocks if len(b) == SECTION_BLOCK]
    starts = [0]
    for k in range(1, len(means)):
        if abs(means[k] - means[k - 1]) >= SECTION_JUMP - 1e-9:
            starts.append(k * SECTION_BLOCK)
    return list(zip(starts, [*starts[1:], len(energy)], strict=True))


def _closest(units: list[Unit], target: float) -> Unit:
    return min(units, key=lambda u: abs(u.energy - target))


def _pick_donor(
    by_source: dict[str, list[Unit]], target: float, rng: random.Random, cap: float | None
) -> str:
    """Donors nearest the target; with a cap, only those holding a unit below it."""
    names = [s for s, us in by_source.items() if cap is None or any(u.energy < cap for u in us)]
    names = names or list(by_source)
    ranked = sorted(names, key=lambda s: abs(_closest(by_source[s], target).energy - target))
    return rng.choice(ranked[:DONOR_CHOICES])


def _limited(units: list[Unit], cap: float | None, fallback: list[Unit]) -> list[Unit]:
    """Units below the cap, else fallback units below it, else the lowest-energy unit."""
    if cap is None:
        return units
    ok = [u for u in units if u.energy < cap] or [u for u in fallback if u.energy < cap]
    return ok or [min(units, key=lambda u: u.energy)]


def _place(unit: Unit, start: float, out: Events, boosts: bool) -> None:
    events, bst, groups = out
    events.extend(BasicEvent(start + e.beat, e.type, e.value, e.float_value) for e in unit.events)
    if boosts:
        bst.extend((start + b, on) for b, on in unit.boosts)
    for key in BOX_KEYS:
        for g in unit.groups.get(key, []):
            c = copy.deepcopy(g)
            c["b"] = start + c["b"]
            groups.setdefault(key, []).append(c)


def _section_units(pool: list[Unit], energy: list[float], lo: int, hi: int) -> list[Unit]:
    """Per bar of [lo, hi): motif slot k takes the closest unit to its mean target energy."""
    mean = sum(energy[lo:hi]) / (hi - lo)
    low = mean < LOW
    allowed = _limited(pool, LOW_UNIT_MAX if low else None, [])
    motif: list[Unit] = []
    for k in range(SECTION_BLOCK):
        targets = energy[lo + k : hi : SECTION_BLOCK]
        motif.append(_closest(allowed, sum(targets) / len(targets) if targets else mean))
    return [motif[(i - lo) % SECTION_BLOCK] for i in range(lo, hi)]


def _finish(out: Events, off: float) -> Events:
    events, boosts, groups = out
    events = [e for e in events if e.beat <= off]
    events += [BasicEvent(off, t, 0) for t in LIGHT_TYPES]
    boosts = [(b, o) for b, o in boosts if b <= off]
    groups = {
        k: sorted((g for g in v if g["b"] <= off), key=lambda g: g["b"]) for k, v in groups.items()
    }
    # Stable by beat: unit events first, lights-off last.
    return sorted(events, key=lambda e: e.beat), sorted(boosts, key=lambda b: b[0]), groups


def build_lightshow(
    beatmap: Beatmap,
    timing: Timing,
    t: Templates,
    analysis: Analysis | None,
    seed: int,
    environment: str | None = None,
) -> LightshowPayload:
    _require(t)
    rng = random.Random(seed)  # noqa: S311 # nosec B311 - not cryptographic
    # An environment without learned units falls back to a seeded learned one.
    env = environment if environment and t.units.get(environment) else None
    env = env or choose_environment(t, seed)
    schemes = t.schemes.get(env, [])
    scheme = rng.choice(schemes) if schemes else None
    energy = bar_energy(beatmap, timing, analysis)
    units = t.units[env]
    by_source: dict[str, list[Unit]] = {}
    for u in units:
        by_source.setdefault(u.source, []).append(u)
    fade_from = max(0, len(energy) - FADE_BARS)
    out: Events = ([], [], {})
    boost_on = False
    for lo, hi in _sections(energy):
        mean = sum(energy[lo:hi]) / (hi - lo)
        low, high = mean < LOW, mean > HIGH
        donor = by_source[_pick_donor(by_source, mean, rng, LOW_UNIT_MAX if low else None)]
        chosen = _section_units(donor, energy, lo, hi)
        if high or low or boost_on:
            out[1].append((lo * BAR, high))
            boost_on = high
        for i, unit in zip(range(lo, hi), chosen, strict=True):
            if i == fade_from and boost_on:
                out[1].append((i * BAR, False))
                boost_on = False
            if i >= fade_from:
                unit = _closest(_limited(donor, FADE_UNIT_MAX, units), energy[i])
            _place(unit, i * BAR, out, boosts=not (high or low) and i < fade_from)
    last = last_note_beat(beatmap)
    final = _finish(out, last + OFF_AFTER)
    shows = {
        name: (list(final[0]), list(final[1]), copy.deepcopy(final[2]))
        for name in beatmap.difficulties
    }
    return LightshowPayload(env, scheme, shows)
