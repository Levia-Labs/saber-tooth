"""Local filters BeatSaver cannot apply, and the server-side query that narrows what it returns."""

from dataclasses import dataclass
from typing import Literal

from saber_tooth.beatsaver.models import BsDiff, BsMap

ORDERS = ("Latest", "Relevance", "Rating", "Curated", "Random", "Duration")
DIFFICULTIES = ("Easy", "Normal", "Hard", "Expert", "ExpertPlus")
PAGE_SIZE = 100


@dataclass(frozen=True)
class LocalFilter:
    diffs: frozenset[str] = frozenset()
    diffs_mode: Literal["all", "any"] = "all"
    nps_min: float | None = None
    nps_max: float | None = None
    nps_scope: Literal["any", "all"] = "any"
    characteristic: str = "Standard"
    min_rating: float | None = None
    min_upvotes: int | None = None

    def _chosen(self, m: BsMap) -> list[BsDiff]:
        return [d for d in m.diffs if d.characteristic == self.characteristic]

    def _nps_ok(self, nps: float) -> bool:
        return (self.nps_min is None or nps >= self.nps_min) and (
            self.nps_max is None or nps <= self.nps_max
        )

    def matches(self, m: BsMap) -> bool:
        if self.min_rating is not None and m.score < self.min_rating:
            return False
        if self.min_upvotes is not None and m.upvotes < self.min_upvotes:
            return False
        chosen = self._chosen(m)
        if self.diffs:
            have = {d.difficulty for d in chosen}
            ok = self.diffs <= have if self.diffs_mode == "all" else bool(self.diffs & have)
            if not ok:
                return False
        if self.nps_min is None and self.nps_max is None:
            return True
        results = [self._nps_ok(d.nps) for d in chosen]
        if self.nps_scope == "all":
            return bool(results) and all(results)
        return any(results)


def _num(value: float) -> str:
    return f"{value:g}"


@dataclass(frozen=True)
class ServerQuery:
    q: str = ""
    tags: tuple[str, ...] = ()
    min_rating: float | None = None
    min_upvotes: int | None = None
    order: str = "Rating"
    ascending: bool = False
    ranked: bool = False
    date_from: str | None = None
    date_to: str | None = None
    bpm_min: float | None = None
    bpm_max: float | None = None
    duration_min: int | None = None
    duration_max: int | None = None
    full_spread: bool = False
    nps_max: float | None = None
    nps_scope: Literal["any", "all"] = "any"

    def to_params(self) -> dict[str, str]:
        """Query for BeatSaver. minNps is never sent and maxNps only for scope all, because the
        API does not say which difficulty they apply to and a wrong guess would drop matches."""
        params = {"order": self.order, "ascending": str(self.ascending).lower()}
        params["pageSize"] = str(PAGE_SIZE)
        if self.q:
            params["q"] = self.q
        if self.tags:
            params["tags"] = "|".join(self.tags)
        if self.min_rating is not None:
            params["minRating"] = _num(self.min_rating)
        if self.min_upvotes is not None:
            params["minUpVotes"] = str(self.min_upvotes)
        if self.ranked:
            params["leaderboard"] = "Ranked"
        optional = {
            "from": self.date_from,
            "to": self.date_to,
            "minBpm": self.bpm_min,
            "maxBpm": self.bpm_max,
            "minDuration": self.duration_min,
            "maxDuration": self.duration_max,
        }
        for key, value in optional.items():
            if value is not None:
                params[key] = value if isinstance(value, str) else _num(value)
        if self.full_spread:
            params["fullSpread"] = "true"
        if self.nps_scope == "all" and self.nps_max is not None:
            params["maxNps"] = _num(self.nps_max)
        return params
