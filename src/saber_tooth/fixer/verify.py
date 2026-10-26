"""Proposal model and the acceptance check every candidate must pass."""

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


def finding_key(f: Finding) -> tuple:
    """Identity of a finding: difficulty, rule and the hands involved."""
    return (f.difficulty, f.rule, frozenset(int(n.color) for n in f.notes))


def _same(a: Finding, b: Finding) -> bool:
    """Same identity and overlapping (or touching) beat ranges."""
    ranges = a.beat_start <= b.beat_end + EPS and b.beat_start <= a.beat_end + EPS
    return finding_key(a) == finding_key(b) and ranges


def new_findings(after: list[Finding], before: list[Finding]) -> list[Finding]:
    """Findings in `after` that match no `before` finding."""
    return [a for a in after if not any(_same(a, b) for b in before)]


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
    return any(_same(a, target) and not any(_same(a, o) for o in others) for a in after)


def accepts(ctx: Context, ops: list[Op]) -> list[Op] | None:
    """The fixed map must lose the target finding and gain no new one."""
    try:
        fixed = apply_ops(ctx.beatmap, ops)
    except OpConflict:
        return None
    names = _touched(ops) | {ctx.finding.difficulty}
    before = findings_for(ctx.beatmap, names, ctx.analysis)
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
