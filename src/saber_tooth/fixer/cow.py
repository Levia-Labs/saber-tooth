"""Copy-on-write working copy of a Beatmap for apply_ops: only what an op mutates is copied."""

import copy

from saber_tooth.model import Beatmap, Difficulty


class Draft:
    """Shallow copy of a map. `own` hands out a private Difficulty (fresh notes, walls and raw
    dict; raw lists and element objects are never mutated in place, only replaced), `info`
    a private MapInfo. Everything else stays shared with the source."""

    def __init__(self, src: Beatmap):
        self.map = copy.copy(src)
        self.map.difficulties = dict(src.difficulties)
        self._owned: set[str] = set()
        self._info = False

    def own(self, name: str) -> Difficulty:
        d = self.map.difficulties[name]
        if name not in self._owned:
            d = copy.copy(d)
            d.notes, d.walls, d.raw = list(d.notes), list(d.walls), dict(d.raw)
            self.map.difficulties[name] = d
            self._owned.add(name)
        return d

    def adopt(self, name: str) -> None:
        """Mark a difficulty the draft itself created as private."""
        self._owned.add(name)

    def info(self):
        if not self._info:
            self.map.info = copy.copy(self.map.info)
            self._info = True
        return self.map.info

    def finish(self) -> Beatmap:
        """Sort every difficulty's notes, copying only those not already in order."""
        for name, d in list(self.map.difficulties.items()):
            if name in self._owned or any(
                a > b for a, b in zip(d.notes, d.notes[1:], strict=False)
            ):
                self.own(name).notes.sort()
        return self.map
