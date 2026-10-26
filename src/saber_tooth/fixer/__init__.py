from itertools import islice
from typing import NamedTuple

from saber_tooth.analysis import Analysis
from saber_tooth.checks import Finding
from saber_tooth.fixer.ops import (
    AddDifficulty,
    ApplyLightshow,
    Delete,
    Fill,
    Flip,
    Move,
    Op,
    OpConflict,
    Recolor,
    apply_ops,
    op_from_dict,
)
from saber_tooth.fixer.strategies import STRATEGIES
from saber_tooth.fixer.verify import Context, Proposal, accepts, build_proposal
from saber_tooth.lightshow import Templates
from saber_tooth.model import Beatmap

MAX_CANDIDATES = 40


class Outcome(NamedTuple):
    proposal: Proposal | None
    reason: str


def propose_with_reason(
    beatmap: Beatmap,
    finding: Finding,
    analysis: Analysis | None,
    templates: Templates | None,
    seed: int,
) -> Outcome:
    strategy = STRATEGIES.get(finding.rule)
    if strategy is None:
        return Outcome(None, f"no fix for {finding.rule}")
    ctx = Context(beatmap, finding, analysis, templates, seed)
    if finding.rule not in ("missing-difficulty", "default-environment") and (
        ctx.d is None or ctx.profile is None
    ):
        return Outcome(None, f"difficulty {finding.difficulty} not found")
    for ops in islice(strategy(ctx), MAX_CANDIDATES):
        fixed = accepts(ctx, ops) if ops else None
        if fixed is not None:
            return Outcome(build_proposal(ctx, ops, fixed), "")
    return Outcome(None, ctx.reason or "no verified fix")


def propose(
    beatmap: Beatmap,
    finding: Finding,
    analysis: Analysis | None,
    templates: Templates | None,
    seed: int,
) -> Proposal | None:
    """First candidate fix that removes the finding and adds none, or None."""
    return propose_with_reason(beatmap, finding, analysis, templates, seed).proposal


__all__ = [
    "AddDifficulty",
    "ApplyLightshow",
    "Context",
    "Delete",
    "Fill",
    "Flip",
    "Move",
    "Op",
    "OpConflict",
    "Outcome",
    "Proposal",
    "Recolor",
    "apply_ops",
    "op_from_dict",
    "propose",
    "propose_with_reason",
]
