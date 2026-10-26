from saber_tooth.analysis import Analysis
from saber_tooth.generator.build import generate_difficulty
from saber_tooth.generator.placer import GenerationError
from saber_tooth.generator.tempo import tempo_map
from saber_tooth.model import DIFFICULTIES, Difficulty
from saber_tooth.profiles import PROFILES
from saber_tooth.timing import Timing


def generate_all(a: Analysis, seed: int) -> tuple[Timing, dict[str, Difficulty]]:
    base, events = tempo_map(a)
    timing = Timing(base, events)
    out: dict[str, Difficulty] = {}
    for name in DIFFICULTIES:
        d = generate_difficulty(a, timing, PROFILES[name], seed)
        d.bpm_events = list(events)
        out[name] = d
    return timing, out


__all__ = ["GenerationError", "generate_all", "generate_difficulty", "tempo_map"]
