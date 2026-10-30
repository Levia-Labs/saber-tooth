from collections.abc import Callable

from saber_tooth.checks.finding import Finding
from saber_tooth.checks.flow import parity_break, swing_speed, wide_jump
from saber_tooth.checks.gaps import empty_gap
from saber_tooth.checks.layout import crossover, note_in_wall, stack_conflict, vision_block
from saber_tooth.checks.slicing import slice_difficulty
from saber_tooth.checks.structure import default_environment, missing_difficulty
from saber_tooth.checks.walls import wall_short, wall_trap
from saber_tooth.model import Beatmap, Difficulty
from saber_tooth.profiles import PROFILES, Profile
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

# Per-difficulty rules: rule(d, swings, timing, profile, analysis) -> list[Finding].
# Extend by adding entries (Task 6 registers "empty-gap"); rules needing analysis skip on None.
RULES: dict[str, Callable] = {
    "parity-break": parity_break,
    "wide-jump": wide_jump,
    "swing-speed": swing_speed,
    "stack-conflict": stack_conflict,
    "crossover": crossover,
    "vision-block": vision_block,
    "note-in-wall": note_in_wall,
    "empty-gap": empty_gap,
    "wall-trap": wall_trap,
    "wall-short": wall_short,
}
# Reach of each per-difficulty rule in seconds: it never looks further from a note than this
# (the profile limits top out at 1.5 s). None marks a global rule that is computed on the whole
# difficulty (or, with a window, on the gaps around it) instead of on a slice.
LOCAL_REACH_S = 2.0
REACH_S: dict[str, float | None] = {r: LOCAL_REACH_S for r in RULES} | {"empty-gap": None}
# Map-level rules: rule(beatmap) -> list[Finding].
MAP_RULES: dict[str, Callable] = {
    "missing-difficulty": missing_difficulty,
    "default-environment": default_environment,
}


def check_difficulty(
    d: Difficulty,
    timing: Timing,
    profile: Profile,
    analysis=None,
    rules: set[str] | None = None,
    window: tuple[float, float] | None = None,
) -> list[Finding]:
    """Findings of one difficulty; with a (lo, hi) beat window only those overlapping it, at a
    cost that follows the window: local rules run on a slice reaching their reach past it."""
    wanted = [(i, r) for i, r in RULES.items() if rules is None or i in rules]
    out: list[Finding] = []
    if window is None:
        swings = build_swings(d.notes, timing)
        for _, rule in wanted:
            out.extend(rule(d, swings, timing, profile, analysis))
        return sorted(out, key=Finding.sort_key)
    lo, hi = window
    local = [r for i, r in wanted if REACH_S[i] is not None]
    if local:
        m = timing.to_beats(LOCAL_REACH_S) - timing.to_beats(0.0)
        part = slice_difficulty(d, lo - m, hi + m)
        swings = build_swings(part.notes, timing)
        for rule in local:
            out.extend(rule(part, swings, timing, profile, analysis))
    out += (
        empty_gap(d, None, timing, profile, analysis, window)
        if any(REACH_S[i] is None for i, _ in wanted)
        else []
    )
    return sorted((f for f in out if f.beat_start <= hi and f.beat_end >= lo), key=Finding.sort_key)


def run_checks(
    beatmap: Beatmap,
    analysis=None,
    rules: set[str] | None = None,
    difficulty: str | None = None,
    window: tuple[float, float] | None = None,
) -> list[Finding]:
    out: list[Finding] = []
    for rule_id, rule in MAP_RULES.items():
        wanted = rule_id in rules if rules is not None else difficulty is None
        if wanted:
            out.extend(rule(beatmap))
    for name, d in beatmap.difficulties.items():
        profile = PROFILES.get(name)
        if profile is None or (difficulty is not None and name != difficulty):
            continue
        timing = Timing(beatmap.info.bpm, d.bpm_events)
        out.extend(check_difficulty(d, timing, profile, analysis, rules, window))
    return sorted(out, key=Finding.sort_key)


__all__ = ["MAP_RULES", "REACH_S", "RULES", "Finding", "check_difficulty", "run_checks"]
