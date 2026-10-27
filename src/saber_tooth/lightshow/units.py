import gzip
import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

from saber_tooth.model import BasicEvent, ColorScheme

BAR = 4.0
BUNDLED = Path(__file__).parent / "data" / "templates.json.gz"


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
        raw = json.dumps(data).encode("utf-8")
        path = Path(path)
        if path.suffix == ".gz":
            with (
                path.open("wb") as fh,
                gzip.GzipFile(filename="", fileobj=fh, mode="wb", mtime=0) as gz,
            ):
                gz.write(raw)  # mtime 0 keeps the bytes reproducible
        else:
            path.write_bytes(raw)

    @classmethod
    def load(cls, path: Path) -> "Templates":
        path = Path(path)
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
        units = {env: [_unit(u) for u in us] for env, us in data.get("units", {}).items()}
        schemes = {
            env: [ColorScheme(s["id"], s["colors"]) for s in ss]
            for env, ss in data.get("schemes", {}).items()
        }
        return cls(units, schemes)


_cache: dict[Path, tuple[tuple[int, int], Templates]] = {}
_cache_lock = threading.Lock()


def load_cached(path: Path) -> Templates:
    """Parse `path` once per process; parse again only when its mtime or size changes."""
    path = Path(path).resolve()
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    with _cache_lock:
        hit = _cache.get(path)
        if hit and hit[0] == key:
            return hit[1]
        templates = Templates.load(path)
        _cache[path] = (key, templates)
        return templates


def _unit(u: dict) -> Unit:
    return Unit(
        environment=u["environment"],
        source=u["source"],
        energy=u["energy"],
        events=[BasicEvent(**e) for e in u["events"]],
        boosts=[(float(b), bool(o)) for b, o in u["boosts"]],
        groups=u["groups"],
    )
