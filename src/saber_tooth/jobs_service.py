"""What a job worker process needs to rebuild the service from paths and URLs.

A child cannot receive the parent's `Service`: it holds a SQLite connection, locks and an HTTP
client. It gets a `ChildSpec` (plain strings) and builds its own service, store connection and
analyser client. Only the CPU-bound kinds run in children; the rest keep running in the API
process.
"""

from dataclasses import dataclass
from pathlib import Path

from saber_tooth.jobs_child import share_store

PROCESS_KINDS = frozenset({"scan", "fix", "relight"})


@dataclass(frozen=True)
class ChildSpec:
    levels: str
    data: str
    db: str
    analyser_url: str
    analyser_uploads: str


def build_child_handlers(spec: ChildSpec) -> dict:
    """The job handlers over a service of the child's own (runs inside the worker process)."""
    from saber_tooth.analyser_client import AnalyserClient
    from saber_tooth.api.jobs_api import core_handlers
    from saber_tooth.audio import encode_egg
    from saber_tooth.service import Service
    from saber_tooth.store import Store

    store = Store(Path(spec.db))
    share_store(store)
    client = AnalyserClient(spec.analyser_url, Path(spec.analyser_uploads))
    service = Service(Path(spec.levels), Path(spec.data), store, client, encode_egg)
    return core_handlers(service)
