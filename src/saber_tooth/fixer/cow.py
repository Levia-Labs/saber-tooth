"""Copy-on-write working copy of a Beatmap for apply_ops: only what an op mutates is copied."""

import copy
from itertools import pairwise

from saber_tooth.model import Beatmap, Difficulty

_SORTED: list[tuple[list, int]] = []  # (notes list, length) known to be in order, newest last


def notes_sorted(notes: list) -> bool:
    """Whether `notes` is in order; remembered per list object, because every candidate of a
    batch starts from the same unchanged map and the answer would be recomputed each time."""
    for known, n in _SORTED:
        if known is notes and n == len(notes):
            return True
    ok = all(a <= b for a, b in pairwise(notes))
    if ok:
        _SORTED.append((notes, len(notes)))
        del _SORTED[:-16]
    return ok


class Draft:
    """Shallow copy of a map. `own` hands out a private Difficulty (fresh sorted notes, walls and
    raw dict, so ops can bisect and insert in place; raw lists and element objects are never
    mutated in place, only replaced), `info` a private MapInfo.
    Everything else stays shared with the source."""

    def __init__(self, src: Beatmap):
        self.map = copy.copy(src)
        self.map.difficulties = dict(src.difficulties)
        self._owned: set[str] = set()
        self._adopted: set[str] = set()
        self._info = False

    def own(self, name: str) -> Difficulty:
        d = self.map.difficulties[name]
        if name not in self._owned:
            d = copy.copy(d)
            d.notes, d.walls, d.raw = list(d.notes), list(d.walls), dict(d.raw)
            if not notes_sorted(self.map.difficulties[name].notes):
                d.notes.sort()
            self.map.difficulties[name] = d
            self._owned.add(name)
        return d

    def adopt(self, name: str) -> None:
        """Mark a difficulty the draft itself created as private."""
        self._owned.add(name)
        self._adopted.add(name)

    def info(self):
        if not self._info:
            self.map.info = copy.copy(self.map.info)
            self._info = True
        return self.map.info

    def finish(self) -> Beatmap:
        """Notes of every difficulty in order: owned ones are kept in order by the ops, a
        difficulty the draft only adopted or shares is sorted (copied) when it is not."""
        for name, d in list(self.map.difficulties.items()):
            if name in self._adopted or (name not in self._owned and not notes_sorted(d.notes)):
                self.own(name).notes.sort()
        return self.map
