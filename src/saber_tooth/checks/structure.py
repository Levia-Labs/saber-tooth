from saber_tooth.checks.finding import Finding
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import DIFFICULTIES, Beatmap


def missing_difficulty(beatmap: Beatmap) -> list[Finding]:
    return [
        Finding("missing-difficulty", name, 0.0, 0.0, "error", f"difficulty {name} is missing")
        for name in DIFFICULTIES
        if name not in beatmap.difficulties
    ]


def default_environment(beatmap: Beatmap) -> list[Finding]:
    diffs = beatmap.difficulties.values()
    lit = any(d.events or any(d.raw.get(k) for k in BOX_KEYS) for d in diffs)
    if beatmap.info.environment == "DefaultEnvironment":
        msg = "map uses the default environment"
    elif not lit:
        msg = "no difficulty has lighting events"
    else:
        return []
    return [Finding("default-environment", "*", 0.0, 0.0, "warn", msg)]
