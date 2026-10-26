class MapParseError(ValueError):
    """Raised when a map folder or file cannot be parsed."""


def safe_name(name: object) -> str:
    """Return name if it is a plain filename; raise MapParseError otherwise."""
    if not isinstance(name, str) or not name or name in (".", ".."):
        raise MapParseError(f"invalid filename: {name!r}")
    if "/" in name or "\\" in name or ":" in name or "\x00" in name:
        raise MapParseError(f"invalid filename: {name!r}")
    return name
