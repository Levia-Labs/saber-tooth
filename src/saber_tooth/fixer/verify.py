"""Proposal model and the acceptance check every candidate must pass."""

import threading
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from saber_tooth.analysis import Analysis
from saber_tooth.checks import MAP_RULES, Finding, check_difficulty, run_checks
from saber_tooth.fixer.codec import note_to_dict
from saber_tooth.fixer.ops import AddDifficulty, ApplyLightshow, Op, OpConflict, apply_ops
from saber_tooth.fixer.summary import summarize
from saber_tooth.lightshow import Templates
from saber_tooth.model import Beatmap, Difficulty, Note
from saber_tooth.profiles import PROFILES, Profile
from saber_tooth.timing import Timing

EPS = 1e-6
_RANK = {"warn": 0, "error": 1}


def finding_key(f: Finding) -> tuple:
    """Identity of a finding: difficulty, rule and the hands and walls involved."""
    return (f.difficulty, f.rule, frozenset(int(n.color) for n in f.notes), f.walls)


def _same(a: Finding, b: Finding) -> bool:
    """Same identity and overlapping (or touching) beat ranges."""
    ranges = a.beat_start <= b.beat_end + EPS and b.beat_start <= a.beat_end + EPS
    return finding_key(a) == finding_key(b) and ranges


def _overlaps(a: Finding, b: Finding) -> bool:
    """Same identity and overlapping beat ranges of positive length, or exactly equal."""
    if finding_key(a) != finding_key(b):
        return False
    equal = abs(a.beat_start - b.beat_start) <= EPS and abs(a.beat_end - b.beat_end) <= EPS
    return equal or (a.beat_start < b.beat_end - EPS and b.beat_start < a.beat_end - EPS)


def find_same(findings: list[Finding], target: Finding) -> Finding | None:
    """The first finding with the target's identity and an overlapping beat range, or None."""
    return next((f for f in findings if _same(f, target)), None)


def new_findings(after: list[Finding], before: list[Finding]) -> list[Finding]:
    """Findings in `after` that match no `before` finding or are more severe than all matches."""
    buckets: dict[tuple, list[Finding]] = {}
    for b in before:
        buckets.setdefault(finding_key(b), []).append(b)
    index = {k: _Bucket(v) for k, v in buckets.items()}
    out = []
    for a in after:
        bucket = index.get(finding_key(a))
        top = bucket.top_rank(a) if bucket else None
        if top is None or _RANK[a.severity] > top:
            out.append(a)
    return out


class _Bucket:
    """Findings of one identity sorted by start beat: range lookups without a pairwise scan."""

    def __init__(self, findings: list[Finding]) -> None:
        self.items = sorted(findings, key=lambda f: f.beat_start)
        self.starts = [f.beat_start for f in self.items]
        self.longest = max((f.beat_end - f.beat_start for f in self.items), default=0.0)

    def top_rank(self, a: Finding) -> int | None:
        """The highest severity rank among findings whose range overlaps or touches `a`'s."""
        hi = bisect_right(self.starts, a.beat_end + EPS)
        lo = bisect_left(self.starts, a.beat_start - EPS - self.longest)
        ranks = [_RANK[b.severity] for b in self.items[lo:hi] if b.beat_end >= a.beat_start - EPS]
        return max(ranks) if ranks else None


@dataclass(frozen=True)
class Proposal:
    rule: str
    difficulty: str
    severity: str
    summary: str
    ops: list[Op]
    before: list[Note]
    after: list[Note]

    def to_dict(self) -> dict:
        return {
            "rule": self.rule,
            "difficulty": self.difficulty,
            "severity": self.severity,
            "summary": self.summary,
            "ops": [op.to_dict() for op in self.ops],
            "before": [note_to_dict(n) for n in self.before],
            "after": [note_to_dict(n) for n in self.after],
        }


@dataclass
class Context:
    beatmap: Beatmap
    finding: Finding
    analysis: Analysis | None
    templates: Templates | None
    seed: int
    reason: str = ""
    d: Difficulty | None = field(init=False, default=None)
    profile: Profile | None = field(init=False, default=None)
    timing: Timing = field(init=False)

    def __post_init__(self) -> None:
        self.d = self.beatmap.difficulties.get(self.finding.difficulty)
        self.profile = PROFILES.get(self.finding.difficulty)
        self.timing = map_timing(self.beatmap, self.d)


Strategy = Callable[[Context], Iterator[list[Op]]]


def map_timing(beatmap: Beatmap, d: Difficulty | None = None) -> Timing:
    """Timing of one difficulty, or of the first one that has tempo changes."""
    if d is None:
        d = next((x for x in beatmap.difficulties.values() if x.bpm_events), None)
    return Timing(beatmap.info.bpm, d.bpm_events if d else [])


def _touched(ops: list[Op]) -> set[str]:
    names: set[str] = set()
    for op in ops:
        if isinstance(op, AddDifficulty):
            names.add(op.difficulty.name)
        elif isinstance(op, ApplyLightshow):
            continue
        else:
            names.add(op.difficulty)
    return names


def findings_for(beatmap: Beatmap, names: set[str], analysis: Analysis | None) -> list[Finding]:
    out: list[Finding] = []
    for name in sorted(names):
        d, profile = beatmap.difficulties.get(name), PROFILES.get(name)
        if d is not None and profile is not None:
            out.extend(check_difficulty(d, map_timing(beatmap, d), profile, analysis))
    return out + run_checks(beatmap, analysis, rules=set(MAP_RULES))


def _target_remains(target: Finding, before: list[Finding], after: list[Finding]) -> bool:
    others = [b for b in before if b is not target]
    return any(_overlaps(a, target) and not any(_overlaps(a, o) for o in others) for a in after)


_BEFORE: list[tuple] = []  # (beatmap, analysis, names, findings), newest last
_BEFORE_KEPT = 6
_BEFORE_LOCK = threading.Lock()


def _before(beatmap: Beatmap, names: set[str], analysis: Analysis | None) -> list[Finding]:
    """Findings of the unchanged map: every candidate for every finding starts from the same
    map, so they are computed once per map and difficulty set instead of once per candidate."""
    with _BEFORE_LOCK:
        for bm, an, nm, found in _BEFORE:
            if bm is beatmap and an is analysis and nm == names:
                return found
    found = findings_for(beatmap, names, analysis)
    with _BEFORE_LOCK:
        _BEFORE.append((beatmap, analysis, frozenset(names), found))
        del _BEFORE[:-_BEFORE_KEPT]
    return found


def accepts(ctx: Context, ops: list[Op]) -> list[Op] | None:
    """The fixed map must lose the target finding and gain no new one."""
    try:
        fixed = apply_ops(ctx.beatmap, ops)
    except OpConflict:
        return None
    names = _touched(ops) | {ctx.finding.difficulty}
    before = _before(ctx.beatmap, names, ctx.analysis)
    after = findings_for(fixed, names, ctx.analysis)
    target = next((b for b in before if _same(b, ctx.finding)), None)
    if target is None or _target_remains(target, before, after):
        return None
    return None if new_findings(after, before) else fixed


def _changed(beatmap: Beatmap, fixed: Beatmap, names: set[str]) -> tuple[list[Note], list[Note]]:
    gone: Counter = Counter()
    new: Counter = Counter()
    for name in names:
        old = (
            Counter(beatmap.difficulties[name].notes) if name in beatmap.difficulties else Counter()
        )
        cur = Counter(fixed.difficulties[name].notes) if name in fixed.difficulties else Counter()
        gone += old - cur
        new += cur - old
    return sorted(gone.elements()), sorted(new.elements())


def build_proposal(ctx: Context, ops: list[Op], fixed: Beatmap) -> Proposal:
    before, after = _changed(ctx.beatmap, fixed, _touched(ops))
    f = ctx.finding
    return Proposal(f.rule, f.difficulty, f.severity, summarize(ops), ops, before, after)
