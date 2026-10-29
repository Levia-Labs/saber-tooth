"""The Fix engine: one difficulty at a time, one time batch at a time, saving as it goes.

A pass over a difficulty checks it once, then tries the findings of each batch (a window of
about BATCH_NOTES notes) in order, folding every verified fix into the working map. Each fix
is verified against its window only (see fixer.window). Passes repeat while one changed
the map, up to the round cap. `on_save` fires after every pass and every SAVE_BATCHES
batches with the position to resume from, so a cancel or crash loses at most a few batches.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from saber_tooth.analysis import Analysis
from saber_tooth.checks import MAP_RULES, Finding, run_checks
from saber_tooth.fixer import Proposal, apply_ops, propose_with_reason
from saber_tooth.fixer.verify import _same
from saber_tooth.fixer.window import batch_edges, batch_of
from saber_tooth.jobs import JobCancelled
from saber_tooth.lightshow import Templates
from saber_tooth.model import DIFFICULTIES, Beatmap

MAX_ROUNDS = 6
SAVE_BATCHES = 10  # a save writes the whole difficulty list, so not after every batch


@dataclass
class FixRun:
    """What the engine did: the fixed map, the proposals folded in and what stayed open."""

    fixed: Beatmap
    steps: list[Proposal] = field(default_factory=list)
    unfixed: list[dict] = field(default_factory=list)  # finding dicts plus a "reason"
    rounds: int = 0
    completed: list[dict] = field(default_factory=list)  # {"difficulty", "batches", "rounds"}


def complete(bm: Beatmap) -> bool:
    return all(name in bm.difficulties for name in DIFFICULTIES)


def _order(f: Finding) -> tuple:
    return (f.rule != "missing-difficulty", f.severity != "error", f.difficulty, f.beat_start)


class Stopped(Exception):
    """A fix failed part way; `where` names the difficulty and batch."""

    def __init__(self, where: str, cause: BaseException) -> None:
        super().__init__(f"stopped at {where}: {cause}")
        self.where = where


class _Engine:
    def __init__(self, run, analysis, templates, seed, max_rounds, hooks) -> None:
        self.run, self.analysis, self.templates, self.seed = run, analysis, templates, seed
        self.max_rounds = max_rounds
        self.on_round, self.check, self.on_batch, self.on_save = hooks
        self.since_save = 0

    def _try(self, findings: list[Finding], tried: list) -> bool:
        """Fold the verified fix of each finding into the map; True when any applied."""
        run, progressed = self.run, False
        for f in sorted(findings, key=_order):
            if self.check:
                self.check()  # raises to stop the run; saved batches stay saved
            out = propose_with_reason(run.fixed, f, self.analysis, self.templates, self.seed)
            if out.proposal is None:
                tried.append((f, out.reason))
                continue
            run.fixed = apply_ops(run.fixed, out.proposal.ops)
            run.steps.append(out.proposal)
            progressed = True
        return progressed

    def _save(self, position: dict | None) -> None:
        if self.on_save:
            self.on_save(self.run, position)
        self.since_save = 0

    def map_level(self) -> None:
        self._round(1)
        found = run_checks(self.run.fixed, self.analysis, rules=set(MAP_RULES))
        self._try(found, [])
        self._save({"difficulty": "", "round": 1, "batch": 0, "progressed": False})

    def _round(self, n: int) -> None:
        if n > self.run.rounds:
            self.run.rounds = n
            if self.on_round:
                self.on_round(n, self.max_rounds)

    def difficulty(self, name: str, rnd: int = 1, first: int = 0, progressed: bool = False) -> None:
        run, tried = self.run, []
        batches = top = 1
        while rnd <= self.max_rounds:
            self._round(rnd)
            d = run.fixed.difficulties[name]
            edges = batch_edges(d)
            batches = len(edges) + 1
            top = max(top, batches)
            groups: list[list[Finding]] = [[] for _ in range(batches)]
            for f in run_checks(run.fixed, self.analysis, difficulty=name):
                groups[batch_of(edges, f.beat_start)].append(f)
            tried = []
            for i in range(first, batches):
                if self.on_batch:
                    self.on_batch(name, i + 1, batches, rnd)
                try:
                    progressed |= self._try(groups[i], tried)
                except JobCancelled:
                    raise
                except Exception as exc:
                    raise Stopped(f"{name} batch {i + 1} of {batches}", exc) from exc
                self.since_save += 1
                if self.since_save >= SAVE_BATCHES and i + 1 < batches:
                    self._save({"difficulty": name, "round": rnd, "batch": i + 1,
                                "progressed": progressed})  # fmt: skip
            first = 0
            if not progressed:
                break
            rnd += 1
            progressed = False
            self._save({"difficulty": name, "round": rnd, "batch": 0, "progressed": False})
        self._finish(name, top, min(rnd, self.max_rounds), tried)

    def _finish(self, name: str, batches: int, rounds: int, tried: list) -> None:
        run = self.run
        now = run_checks(run.fixed, self.analysis, difficulty=name)
        for f, reason in tried:  # a later fix may have cleared a finding tried earlier
            if any(_same(f, g) for g in now):
                run.unfixed.append({**f.to_dict(), "reason": reason})
        run.completed.append({"difficulty": name, "batches": batches, "rounds": rounds})


def fix_beatmap(
    original: Beatmap,
    analysis: Analysis | None,
    templates: Templates | None,
    seed: int,
    max_rounds: int = MAX_ROUNDS,
    on_round: Callable[[int, int], None] | None = None,
    check: Callable[[], None] | None = None,
    on_batch: Callable[[str, int, int, int], None] | None = None,  # difficulty, i, n, round
    on_save: Callable[[FixRun, dict | None], None] | None = None,
    resume: tuple[FixRun, dict] | None = None,
) -> FixRun:
    """Fix findings difficulty by difficulty and batch by batch, each verified in its window.

    `resume` is a FixRun holding the saved map and the position its `on_save` was given.
    """
    run, pos = resume if resume else (FixRun(original), None)
    eng = _Engine(run, analysis, templates, seed, max_rounds, (on_round, check, on_batch, on_save))
    if pos is None:
        eng.map_level()
    done = {c["difficulty"] for c in run.completed}
    for name in sorted(run.fixed.difficulties):
        if name in done:
            continue
        at = pos if pos and pos["difficulty"] == name else None
        args = (at["round"], at["batch"], at["progressed"]) if at else ()
        eng.difficulty(name, *args)
    eng._save(None)
    return run
