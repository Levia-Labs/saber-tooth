"""Which library maps the generator made: a recorded source, or its author name and a kept song."""

from pathlib import Path

GENERATOR_AUTHOR = "saber-tooth"  # info.dat author written by assemble.py
FIXED_SUFFIX = " [saber-tooth]"  # a fixed copy of a human original
SONG_FILE = "song.egg"


def _row_generated(row, levels: Path) -> bool:
    if row["source"]:
        return True
    folder = row["folder"] or ""
    if row["mapper"] != GENERATOR_AUTHOR or folder.endswith(FIXED_SUFFIX):
        return False
    return (levels / folder / SONG_FILE).is_file()


def generated_ids(store, levels: Path) -> list[str]:
    """Ids of the readable library maps the generator made."""
    rows = store._query(
        "SELECT id, folder, mapper, source FROM maps"
        " WHERE (parse_error IS NULL OR parse_error = '') ORDER BY id"
    )
    return [r["id"] for r in rows if _row_generated(r, levels)]


def is_generated(store, levels: Path, map_id: str) -> bool:
    return map_id in generated_ids(store, levels)
