"""Service errors; the API maps MapNotFound to 404 and MapUnreadable/ApplyConflict to 409."""


class ApplyConflict(Exception):
    """Approved proposals cannot be applied; nothing was written."""

    def __init__(self, message: str, ids: list[int]) -> None:
        super().__init__(f"{message} (proposals: {ids})" if ids else message)
        self.ids = ids
        self.result = {"conflict": ids}


class MapNotFound(KeyError):
    """The map id is unknown or its folder no longer exists."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else "map not found"


class MapUnreadable(ValueError):
    """The map folder cannot be parsed."""
