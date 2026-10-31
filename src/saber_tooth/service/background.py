"""Background library work: re-index and copy-scan backfill never run on a request thread."""

import logging
import threading
import time
from pathlib import Path

from saber_tooth.mapio import MapParseError, load_map
from saber_tooth.service.copyscan import copy_source, store_copy_scan
from saber_tooth.service.util import map_id_for
from saber_tooth.service.verify import stored_analysis

log = logging.getLogger(__name__)
YIELD_S = 0.05  # pause between copy scans so request threads get the GIL


def start_reindex(svc) -> None:
    """Re-index in a daemon thread unless one is already running; readers keep the stored index."""
    with svc._bg_lock:
        if svc._reindexing:
            return
        svc._reindexing = True
    threading.Thread(target=_reindex_job, args=(svc,), name="library-reindex", daemon=True).start()


def _reindex_job(svc) -> None:
    try:
        svc.refresh_library(wait=False)
    except Exception:  # a failed re-index must not kill the thread silently
        log.exception("background library refresh failed")
    finally:
        with svc._bg_lock:
            svc._reindexing = False


def start_backfill(svc, folders: list[str]) -> None:
    """Queue copies without a scan; one low-priority worker drains the queue."""
    if not folders:
        return
    with svc._bg_lock:
        svc._pending_scans.extend(f for f in folders if f not in svc._pending_scans)
        if svc._backfilling:
            return
        svc._backfilling = True
    threading.Thread(target=_backfill_job, args=(svc,), name="copy-backfill", daemon=True).start()


def _backfill_job(svc) -> None:
    try:
        while True:
            with svc._bg_lock:
                if not svc._pending_scans:
                    svc._backfilling = False
                    return
                name = svc._pending_scans.pop(0)
            try:
                scan_copy(svc, svc.levels / name)
            except Exception:  # one bad copy must not stop the rest
                log.exception("copy scan failed for %s", name)
            time.sleep(YIELD_S)
    except BaseException:
        with svc._bg_lock:
            svc._backfilling = False
        raise


def scan_copy(svc, folder: Path) -> None:
    """A saber-tooth copy with no scan: one cheap check, with its original's analysis."""
    mid = map_id_for(folder.name)
    if svc.store.scan_info(mid) is not None or not folder.is_dir():
        return
    try:
        beatmap = load_map(folder)
    except (MapParseError, OSError):
        return
    source = map_id_for(copy_source(folder.name))
    cropped = copy_source(folder.name) != folder.name.removesuffix(" [saber-tooth]")
    info = None if cropped else svc.store.scan_info(source)
    store_copy_scan(svc, folder.name, beatmap, stored_analysis(svc.uploads, info))
