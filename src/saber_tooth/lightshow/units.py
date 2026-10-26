import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from saber_tooth.model import BasicEvent, ColorScheme

BAR = 4.0


@dataclass
class Unit:
    """One bar of lighting; all beats relative to the bar start."""

    environment: str
    source: str
    energy: float
    events: list[BasicEvent] = field(default_factory=list)
    boosts: list[tuple[float, bool]] = field(default_factory=list)
    groups: dict[str, list[dict]] = field(default_factory=dict)


@dataclass
class Templates:
    units: dict[str, list[Unit]] = field(default_factory=dict)
    schemes: dict[str, list[ColorScheme]] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        data = {
            "units": {env: [asdict(u) for u in us] for env, us in self.units.items()},
            "schemes": {env: [asdict(s) for s in ss] for env, ss in self.schemes.items()},
        }
        Path(path).write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Templates":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        units = {env: [_unit(u) for u in us] for env, us in data.get("units", {}).items()}
        schemes = {
            env: [ColorScheme(s["id"], s["colors"]) for s in ss]
            for env, ss in data.get("schemes", {}).items()
        }
        return cls(units, schemes)


def _unit(u: dict) -> Unit:
    return Unit(
        environment=u["environment"],
        source=u["source"],
        energy=u["energy"],
        events=[BasicEvent(**e) for e in u["events"]],
        boosts=[(float(b), bool(o)) for b, o in u["boosts"]],
        groups=u["groups"],
    )
