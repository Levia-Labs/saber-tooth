"""Generation style: the vanilla environment and colour scheme a map is written with.

A style comes from the caller (`parse_style`) or, when absent, from the song: tempo, energy and
brightness pick the closest catalogue environment and its default palette (`resolve_style`)."""

import random
import re
from dataclasses import dataclass, field

from saber_tooth.analysis import Analysis, onset_density
from saber_tooth.environments import BY_NAME, CATALOGUE, COLOR_ROLES, Environment
from saber_tooth.model import ColorScheme

_HEX = re.compile(r"#[0-9a-fA-F]{6}")
TOP_CHOICES = 3
DENSITY_FULL = 5.0  # weighted onsets per second that read as full energy
BPM_LOW, BPM_SPAN = 60.0, 120.0
HH_FULL = 0.6  # share of hi-hat onsets that reads as fully bright


@dataclass(frozen=True)
class Style:
    environment: str | None = None
    colors: dict[str, str] = field(default_factory=dict)  # role -> "#rrggbb"

    def to_dict(self) -> dict:
        return {"environment": self.environment, "colors": dict(self.colors)}


def parse_style(raw: object, known: set[str] | None = None) -> Style | None:
    """A validated style from untrusted input; None for no style, ValueError for a bad one.

    The environment must be a catalogue name (and in `known` when given); colours must be
    "#rrggbb" under a known role. Nothing else passes."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("style must be an object")
    extra = set(raw) - {"environment", "colors"}
    if extra:
        raise ValueError(f"unknown style fields: {', '.join(sorted(map(str, extra)))}")
    env = raw.get("environment")
    if env is not None and (
        not isinstance(env, str) or env not in BY_NAME or (known and env not in known)
    ):
        raise ValueError(f"unknown environment: {str(env)[:60]}")
    colors = {} if raw.get("colors") is None else raw["colors"]
    if not isinstance(colors, dict):
        raise ValueError("style colors must be an object")
    out: dict[str, str] = {}
    for role, value in colors.items():
        if role not in COLOR_ROLES:
            raise ValueError(f"unknown colour role: {str(role)[:40]}")
        if not isinstance(value, str) or not _HEX.fullmatch(value):
            raise ValueError(f"colour {role} must be #rrggbb")
        out[role] = value.lower()
    if env is None and not out:
        return None
    return Style(env, out)


def features(a: Analysis) -> tuple[float, float, float]:
    """Tempo, energy and brightness of the song, each in [0, 1]."""
    end = a.beats[-1] if a.beats else max([*a.kick, *a.snare, *a.hh, 1.0])
    energy = min(1.0, onset_density(a, 0.0, end + 1.0) / DENSITY_FULL)
    tempo = min(1.0, max(0.0, (a.bpm - BPM_LOW) / BPM_SPAN))
    total = len(a.kick) + len(a.snare) + len(a.hh)
    bright = min(1.0, (len(a.hh) / total) / HH_FULL) if total else 0.5
    return tempo, energy, bright


def pick_environment(a: Analysis, seed: int, names: set[str] | None = None) -> Environment:
    """The catalogue environment nearest the song's feel; a seeded pick among the closest few."""
    tempo, energy, bright = features(a)
    want = (0.7 * bright + 0.3 * tempo, 0.6 * energy + 0.4 * tempo, energy)
    pool = [e for e in CATALOGUE if names is None or e.name in names] or list(CATALOGUE)

    def distance(e: Environment) -> float:
        return sum(
            (x - y) ** 2 for x, y in zip((e.valence, e.energy, e.intensity), want, strict=True)
        )

    ranked = sorted(pool, key=lambda e: (distance(e), e.name))
    return random.Random(seed).choice(ranked[:TOP_CHOICES])  # noqa: S311 # nosec B311 - seeded


def to_scheme(env: Environment, style: Style | None) -> ColorScheme:
    """The info.dat colour scheme: the style's colours over the environment's palette."""
    roles = {**env.palette, **(style.colors if style else {})}
    return ColorScheme(f"st-{env.name}", {COLOR_ROLES[r]: _rgba(h) for r, h in roles.items()})


def _rgba(hex_: str) -> dict[str, float]:
    r, g, b = (int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return {"r": r, "g": g, "b": b, "a": 1.0}


def resolve_style(
    style: Style | None, a: Analysis, seed: int, names: set[str] | None = None
) -> tuple[Environment, ColorScheme]:
    """The environment and colour scheme to write: the caller's, else the song's."""
    if style and style.environment:
        env = BY_NAME[style.environment]
    else:
        env = pick_environment(a, seed, names)
    return env, to_scheme(env, style)
