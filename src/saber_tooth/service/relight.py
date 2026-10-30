"""Relight: a copy of a map in another vanilla environment, lit from the learned templates."""

import logging
from dataclasses import replace

from saber_tooth.crop.replace import replace_folder
from saber_tooth.fixer import ApplyLightshow, apply_ops
from saber_tooth.fixer.verify import map_timing
from saber_tooth.lightshow import Templates, build_lightshow
from saber_tooth.service.copyscan import store_copy_scan
from saber_tooth.service.util import checkpoint, map_id_for
from saber_tooth.service.verify import stored_analysis
from saber_tooth.service.writeout import write_fixed

SUFFIX = " [saber-tooth]"
log = logging.getLogger(__name__)


class UnknownEnvironment(ValueError):
    """The environment has no lightshow templates, so no lighting can be built for it."""


def environment_names(templates: Templates | None) -> list[str]:
    """The vanilla environments the lightshow templates can light, sorted."""
    if templates is None:
        return []
    return sorted(env for env, units in templates.units.items() if units)


def relight_map(svc, map_id: str, environment: str, progress=None) -> dict:
    """Light a saber-tooth copy of the map in `environment`; the original is never written.

    A copy (or the existing copy of an original) is rewritten in place, so its fixes stay;
    an original without a copy gets a new `<folder> [saber-tooth]`. Checkpoints run before
    anything is written, so a cancelled job leaves the library as it was.
    """
    templates = svc._templates()
    if environment not in environment_names(templates):
        raise UnknownEnvironment(f"no lightshow templates for environment: {environment}")
    folder = svc._folder(map_id)
    existing = folder if folder.name.endswith(SUFFIX) else svc.levels / (folder.name + SUFFIX)
    rewrite = existing.is_dir()
    if rewrite:
        folder, map_id = existing, map_id_for(existing.name)
    original = svc._load(folder)
    checkpoint(progress, "building the lightshow")
    analysis = stored_analysis(svc.uploads, svc.store.scan_info(map_id))
    payload = build_lightshow(
        original, map_timing(original), templates, analysis, int(map_id[:8], 16), environment
    )
    lit = apply_ops(original, [ApplyLightshow.from_payload(payload)])
    if not rewrite:
        lit.info = replace(lit.info, song_name=original.info.song_name + SUFFIX)
    checkpoint(progress)  # a cancel during the build must not save the result
    checkpoint(progress, "writing the copy")
    if rewrite:
        staged = write_fixed(svc.levels, folder, lit, folder.name + " relight-tmp")
        target = replace_folder(svc.levels, folder, staged)
    else:
        target = write_fixed(svc.levels, folder, lit, folder.name + SUFFIX)
    if not rewrite or svc.store.scan_info(map_id_for(target.name)) is None:
        store_copy_scan(svc, target.name, lit, analysis)
    try:
        svc.refresh_library()
    except Exception:
        log.exception("library refresh failed after relighting %s", map_id)
    return {
        "map_id": map_id,
        "created": not rewrite,
        "environment": environment,
        "folder": target.name,
        "fixed_id": map_id_for(target.name),
        "difficulties": sorted(lit.difficulties),
    }
