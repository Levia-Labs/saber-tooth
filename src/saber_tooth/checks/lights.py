from saber_tooth.checks.finding import Finding
from saber_tooth.lightshow.pacing import strobe_windows
from saber_tooth.mapio.write import BOX_KEYS
from saber_tooth.model import Beatmap
from saber_tooth.timing import Timing


def light_strobe(beatmap: Beatmap) -> list[Finding]:
    """Windows where lights change faster than the pacing limits, per difficulty."""
    out: list[Finding] = []
    for name, d in beatmap.difficulties.items():
        groups = {k: d.raw.get(k, []) for k in BOX_KEYS}
        timing = Timing(beatmap.info.bpm, d.bpm_events)
        out += [
            Finding("light-strobe", name, a, b, "warn", f"lights strobe: {msg}")
            for a, b, msg in strobe_windows(d.events, groups, timing)
        ]
    return out
