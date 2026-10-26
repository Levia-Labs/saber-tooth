from collections.abc import Callable

from saber_tooth.checks.finding import Finding
from saber_tooth.checks.flow import parity_break, swing_speed, wide_jump
from saber_tooth.checks.layout import crossover, note_in_wall, stack_conflict, vision_block
from saber_tooth.checks.structure import default_environment, missing_difficulty
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
}
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
) -> list[Finding]:
    swings = build_swings(d.notes, timing)
    out: list[Finding] = []
    for rule_id, rule in RULES.items():
        if rules is None or rule_id in rules:
            out.extend(rule(d, swings, timing, profile, analysis))
    return sorted(out, key=Finding.sort_key)


def run_checks(
    beatmap: Beatmap,
    analysis=None,
    rules: set[str] | None = None,
    difficulty: str | None = None,
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
        out.extend(check_difficulty(d, timing, profile, analysis, rules))
    return sorted(out, key=Finding.sort_key)


__all__ = ["MAP_RULES", "RULES", "Finding", "check_difficulty", "run_checks"]
