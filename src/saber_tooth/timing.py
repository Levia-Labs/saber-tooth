from saber_tooth.model import BpmEvent


class Timing:
    """Beat <-> seconds conversion with piecewise-constant tempo."""

    def __init__(self, bpm: float, changes: list[BpmEvent]):
        # A change at beat 0 overrides the initial bpm; later duplicates win; beat < 0 is ignored.
        by_beat = {0.0: bpm}
        for change in sorted(changes):
            if change.beat >= 0:
                by_beat[change.beat] = change.bpm
        segs = [BpmEvent(beat, b) for beat, b in sorted(by_beat.items())]
        self._segs: list[tuple[float, float, float]] = []  # (start_beat, start_s, bpm)
        start_s = 0.0
        for i, seg in enumerate(segs):
            if i:
                prev_beat, prev_s, prev_bpm = self._segs[-1]
                start_s = prev_s + (seg.beat - prev_beat) * 60.0 / prev_bpm
            self._segs.append((seg.beat, start_s, seg.bpm))

    def to_seconds(self, beat: float) -> float:
        b0, s0, bpm = self._segs[0]
        for seg in self._segs[1:]:
            if seg[0] > beat:
                break
            b0, s0, bpm = seg
        return s0 + (beat - b0) * 60.0 / bpm

    def to_beats(self, seconds: float) -> float:
        b0, s0, bpm = self._segs[0]
        for seg in self._segs[1:]:
            if seg[1] > seconds:
                break
            b0, s0, bpm = seg
        return b0 + (seconds - s0) * bpm / 60.0
