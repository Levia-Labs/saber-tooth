import math
from pathlib import Path

from saber_tooth.lightshow.units import BAR, Templates, Unit
from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.mapio.write import BOX_KEYS, strip_custom
from saber_tooth.model import BasicEvent, Beatmap, Difficulty

DEFAULT_ENV = "DefaultEnvironment"
MIN_EVENTS = 16


def _p90(counts: list[int]) -> float:
    if not counts:
        return 0.0
    s = sorted(counts)
    return float(s[min(len(s) - 1, math.ceil(0.9 * len(s)) - 1)])


def _box_count(d: Difficulty) -> int:
    return sum(len(d.raw.get(k, [])) for k in BOX_KEYS)


def _rebase_group(g: dict, start: float) -> dict:
    out = strip_custom(g)
    out["b"] = out["b"] - start
    return out


def _units(env: str, source: str, d: Difficulty) -> list[Unit]:
    bars = {}
    for n in d.notes:
        bars[int(n.beat // BAR)] = bars.get(int(n.beat // BAR), 0) + 1
    n_bars = max(
        [int(x.beat // BAR) for x in (*d.notes, *d.events)]
        + [int(b // BAR) for b, _ in d.boosts]
        + [int(g["b"] // BAR) for k in BOX_KEYS for g in d.raw.get(k, [])]
        + [0]
    )
    p90 = _p90([bars.get(i, 0) for i in range(n_bars + 1)])
    out = []
    for i in range(n_bars + 1):
        lo, hi = i * BAR, (i + 1) * BAR
        events = [
            BasicEvent(e.beat - lo, e.type, e.value, e.float_value)
            for e in d.events
            if lo <= e.beat < hi
        ]
        boosts = [(b - lo, o) for b, o in d.boosts if lo <= b < hi]
        groups = {
            k: [_rebase_group(g, lo) for g in d.raw.get(k, []) if lo <= g["b"] < hi]
            for k in BOX_KEYS
        }
        if not (events or boosts or groups):
            continue
        energy = min(1.0, max(0.0, bars.get(i, 0) / p90)) if p90 else 0.0
        out.append(Unit(env, source, energy, events, boosts, groups))
    return out


def _densest(m: Beatmap) -> Difficulty | None:
    return max(m.difficulties.values(), key=lambda d: len(d.notes), default=None)


def learn(levels: Path) -> Templates:
    """Learn one-bar vanilla lighting units from map folders (read-only)."""
    t = Templates()
    for folder in sorted(p for p in Path(levels).iterdir() if p.is_dir()):
        try:
            m = load_map(folder)
        except (MapParseError, OSError):
            continue
        env = m.info.environment
        d = _densest(m)
        if env == DEFAULT_ENV or d is None:
            continue
        if len(d.events) < MIN_EVENTS and not _box_count(d):
            continue
        t.units.setdefault(env, []).extend(_units(env, folder.name, d))
        if m.info.color_scheme and m.info.color_scheme not in t.schemes.get(env, []):
            t.schemes.setdefault(env, []).append(m.info.color_scheme)
    return t
