from saber_tooth.analysis import Analysis
from saber_tooth.generator.build import GenerationStats, generate_difficulty, generate_with_stats
from saber_tooth.generator.placer import GenerationError
from saber_tooth.generator.tempo import tempo_map
from saber_tooth.model import DIFFICULTIES, Difficulty
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing


def generate_all_with_stats(
    a: Analysis, seed: int
) -> tuple[Timing, dict[str, Difficulty], dict[str, GenerationStats]]:
    base, events = tempo_map(a)
    timing = Timing(base, events)
    diffs: dict[str, Difficulty] = {}
    stats: dict[str, GenerationStats] = {}
    for name in DIFFICULTIES:
        diffs[name], stats[name] = generate_with_stats(a, timing, PROFILES[name], seed)
    return timing, diffs, stats


def generate_all(a: Analysis, seed: int) -> tuple[Timing, dict[str, Difficulty]]:
    timing, diffs, _ = generate_all_with_stats(a, seed)
    return timing, diffs


__all__ = [
    "GenerationError",
    "GenerationStats",
    "generate_all",
    "generate_all_with_stats",
    "generate_difficulty",
    "generate_with_stats",
    "tempo_map",
]
