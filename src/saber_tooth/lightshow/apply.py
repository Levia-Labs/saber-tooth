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
    return random.Random(seed).choice([e for _, e in ranked[:3]])  # noqa: S311


def _sections(energy: list[float]) -> list[tuple[int, int]]:
    """Half-open bar ranges; a 4-bar mean jump of >= 0.25 starts a new section."""
    means = [
        sum(energy[i : i + SECTION_BLOCK]) / len(energy[i : i + SECTION_BLOCK])
        for i in range(0, len(energy), SECTION_BLOCK)
    ]
    starts = [0]
    for k in range(1, len(means)):
        if abs(means[k] - means[k - 1]) >= SECTION_JUMP - 1e-9:
            starts.append(k * SECTION_BLOCK)
    return list(zip(starts, [*starts[1:], len(energy)], strict=True))


def _closest(units: list[Unit], target: float) -> Unit:
    return min(units, key=lambda u: abs(u.energy - target))


def _pick_donor(by_source: dict[str, list[Unit]], target: float, rng: random.Random) -> str:
    ranked = sorted(by_source, key=lambda s: abs(_closest(by_source[s], target).energy - target))
    return rng.choice(ranked[:DONOR_CHOICES])


def _limited(units: list[Unit], cap: float | None, fallback: list[Unit]) -> list[Unit]:
    if cap is None:
        return units
    ok = [u for u in units if u.energy < cap]
    if ok:
        return ok
    ok = [u for u in fallback if u.energy < cap]
    return ok or [min(fallback, key=lambda u: u.energy)]


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


def _section_units(
    pool: list[Unit], env_units: list[Unit], energy: list[float], lo: int, hi: int
) -> list[Unit]:
    """Per bar of [lo, hi): motif slot k takes the closest unit to its mean target energy."""
    mean = sum(energy[lo:hi]) / (hi - lo)
    low = mean < LOW
    allowed = _limited(pool, LOW_UNIT_MAX if low else None, env_units)
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
    return sorted(events), sorted(boosts), groups


def build_lightshow(
    beatmap: Beatmap,
    timing: Timing,
    t: Templates,
    analysis: Analysis | None,
    seed: int,
    environment: str | None = None,
) -> LightshowPayload:
    _require(t)
    rng = random.Random(seed)  # noqa: S311 - not cryptographic
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
    for lo, hi in _sections(energy):
        mean = sum(energy[lo:hi]) / (hi - lo)
        donor = by_source[_pick_donor(by_source, mean, rng)]
        chosen = _section_units(donor, units, energy, lo, hi)
        start_boost = mean > HIGH or mean < LOW
        if start_boost:
            out[1].append((lo * BAR, mean > HIGH))
        for i, unit in zip(range(lo, hi), chosen, strict=True):
            if i >= fade_from:
                unit = _closest(_limited(donor, FADE_UNIT_MAX, units), energy[i])
            _place(unit, i * BAR, out, boosts=not start_boost and i < fade_from)
    last = last_note_beat(beatmap)
    final = _finish(out, last + OFF_AFTER)
    shows = {
        name: (list(final[0]), list(final[1]), copy.deepcopy(final[2]))
        for name in beatmap.difficulties
    }
    return LightshowPayload(env, scheme, shows)
