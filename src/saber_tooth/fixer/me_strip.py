"""Fix pre-step: drop Mapping Extensions precision walls so the copy is vanilla playable."""

from dataclasses import replace

from saber_tooth.model import Beatmap


def strip_precision_walls(bm: Beatmap) -> Beatmap:
    """The map without precision walls; the same object when it has none."""
    if not any(w.me for d in bm.difficulties.values() for w in d.walls):
        return bm
    diffs = {
        name: replace(d, walls=[w for w in d.walls if not w.me])
        for name, d in bm.difficulties.items()
    }
    return replace(bm, difficulties=diffs)
