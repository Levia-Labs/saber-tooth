"""Exceptions and error text shared by the job worker and its child processes."""

from typing import Any


class JobCancelled(Exception):
    """Raised at a checkpoint when the running job was asked to stop."""


class JobFailed(Exception):
    """A job failed in a worker process; `result` is the partial result the handler attached."""

    def __init__(self, message: str, result: Any = None) -> None:
        super().__init__(message)
        self.result = result


def error_text(exc: Exception) -> str:
    """The text a failed job shows: a KeyError becomes `internal error: missing entry for
    Cut.ANY` instead of the bare repr `<Cut.ANY: 8>`."""
    if isinstance(exc, KeyError) and exc.args:
        key = exc.args[0]
        name = getattr(key, "name", None)
        label = f"{type(key).__name__}.{name}" if name else repr(key)
        return f"internal error: missing entry for {label}"
    return str(exc) or type(exc).__name__
