"""Thin a denser difficulty down to a tier's target density, then re-flow its cuts."""

import copy
import math

from saber_tooth.checks import check_difficulty
from saber_tooth.fixer.layout_fixes import in_wall
from saber_tooth.mapio.write import BOX_KEYS, FX_KEY
from saber_tooth.model import CUT_VECTORS, OPPOSITE, Bomb, Cut, Difficulty, Note
from saber_tooth.profiles import Profile
from saber_tooth.swings import build_swings
from saber_tooth.timing import Timing

BAR = 4.0
MAX_ROUNDS = 300
EPS = 1e-6


def _on(value: float, step: float) -> bool:
    return abs(value / step - round(value / step)) < EPS


def position_score(beat: float) -> float:
    score = 0.3 if _on(beat, 1.0) else (0.1 if _on(beat, 0.5) else 0.0)
    return score + (0.2 if _on(beat, BAR) else 0.0)


def _one_per_hand_and_beat(notes: list[Note], profile: Profile) -> list[Note]:
    kept: dict[tuple, Note] = {}
    for n in sorted(notes):
        key = (
            (round(n.beat * 1000),)
            if not profile.allow_doubles
            else (round(n.beat * 1000), n.color)
        )
        kept.setdefault(key, n)
    return sorted(kept.values())


def _budget_per_bar(notes: list[Note], profile: Profile, timing: Timing) -> list[Note]:
    bars: dict[int, list[Note]] = {}
    for n in notes:
        bars.setdefault(math.floor(n.beat / BAR + EPS), []).append(n)
    out: list[Note] = []
    carry = 0.0
    for bar in range(min(bars, default=0), max(bars, default=-1) + 1):
        seconds = timing.to_seconds((bar + 1) * BAR) - timing.to_seconds(bar * BAR)
        want = profile.target_nps * seconds + carry
        budget = int(want)
        carry = min(want - budget, 1.0)
        ranked = sorted(bars.get(bar, []), key=lambda n: (-position_score(n.beat), n.beat))
        out.extend(ranked[:budget])
    return sorted(out)


def reflow(notes: list[Note], timing: Timing) -> list[Note]:
    """Give every swing a cut that alternates against the hand's previous swing."""
    swap: dict[Note, Note] = {}
    swings = build_swings(notes, timing)
    for hand_swings in swings.values():
        prev = Cut.UP
        for s in hand_swings:
            want = OPPOSITE[prev]
            first = next((n.cut for n in s.notes if n.cut != Cut.ANY), Cut.ANY)
            cut = want
            if first != Cut.ANY:
                wv, fv = CUT_VECTORS[want], CUT_VECTORS[first]
                if wv[0] * fv[0] + wv[1] * fv[1] > 0.5:
                    cut = first
            for n in s.notes:
                swap[n] = Note(n.beat, n.x, n.y, n.color, cut, n.angle)
            prev = cut
    return sorted(swap.get(n, n) for n in notes)


def _victims(findings) -> set[Note]:
    gone: set[Note] = set()
    for f in findings:
        if gone & set(f.notes):
            continue
        late = [n for n in f.notes if abs(n.beat - f.beat_end) < EPS]
        pick = late if late and f.beat_start != f.beat_end else f.notes[1:] or f.notes
        gone.update(pick)
    return gone


def _free_bombs(bombs: list[Bomb], notes: list[Note]) -> list[Bomb]:
    """Source bombs minus those that would sit in a kept note's cell at its beat."""
    taken = {(round(n.beat / EPS), n.x, n.y) for n in notes}
    return [copy.copy(b) for b in bombs if (round(b.beat / EPS), b.x, b.y) not in taken]


def thin(source: Difficulty, profile: Profile, timing: Timing) -> Difficulty | None:
    grid = [n for n in source.notes if _on(n.beat, profile.grid)] or list(source.notes)
    notes = _budget_per_bar(_one_per_hand_and_beat(grid, profile), profile, timing)
    out = Difficulty(
        profile.name,
        profile.njs,
        profile.offset,
        events=copy.deepcopy(source.events),
        boosts=copy.deepcopy(source.boosts),
        bombs=[],
        walls=copy.deepcopy(source.walls),
        bpm_events=copy.deepcopy(source.bpm_events),
        raw={k: copy.deepcopy(source.raw[k]) for k in (*BOX_KEYS, FX_KEY) if k in source.raw},
    )
    for _ in range(MAX_ROUNDS):
        out.notes = reflow(notes, timing)
        out.bombs = _free_bombs(source.bombs, out.notes)
        findings = check_difficulty(out, timing, profile)
        if not findings:
            return out
        for f in (f for f in findings if f.rule == "note-in-wall"):
            n = f.notes[0]
            out.walls = [w for w in out.walls if not in_wall(n.x, n.y, n.beat, w)]
        gone = _victims([f for f in findings if f.rule != "note-in-wall"])
        notes = [n for n in out.notes if n not in gone]
    return None
