"""Which lightshow set is active: the learned file in the data dir, else the bundled one."""

from datetime import UTC, datetime
from pathlib import Path

from saber_tooth.lightshow import Templates, load_cached

LEARNED = "lightshow.json"


def template_path(data: Path, bundled: Path | None) -> tuple[str, Path | None]:
    """(source, path): the learned file when present, else the bundled file when it exists."""
    learned = Path(data) / LEARNED
    if learned.is_file():
        return "learned", learned
    return "bundled", bundled if bundled and bundled.is_file() else None


def active_templates(data: Path, bundled: Path | None) -> Templates | None:
    """The active set, parsed once per file version (see `load_cached`)."""
    path = template_path(data, bundled)[1]
    return load_cached(path) if path else None


def info(data: Path, bundled: Path | None) -> dict:
    """`{source, environments, units, learned_at}` for GET /api/lightshow."""
    source, path = template_path(data, bundled)
    templates = active_templates(data, bundled)
    learned_at = None
    if source == "learned" and path:
        learned_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
    return {
        "source": source,
        "environments": len(templates.units) if templates else 0,
        "units": sum(len(u) for u in templates.units.values()) if templates else 0,
        "learned_at": learned_at,
    }
