import type { CropEnd, CropPlan, CropWindow, EndKind, Timeline } from "../src/api/types";

const series = (scale: number): number[] =>
  Array.from({ length: 140 }, (_, i) => Math.round(((i % 20) / 20) * scale * 10) / 10);

/** An end at `beat` on a 120 bpm map: seconds are half the beats. */
const end = (beat: number, kind: EndKind): CropEnd => ({ beat, seconds: beat / 2, kind });

const win = (start: number, stop: number, kind: EndKind): CropWindow => ({
  start_beat: start,
  end_beat: stop,
  start_s: start / 2,
  end_s: stop / 2,
  length_s: (stop - start) / 2,
  end_kind: kind,
  score: 0.5,
});

const PLAN_60: CropPlan = {
  enabled: true,
  reason: null,
  band: [54, 66],
  suggestions: [win(0, 128, "section"), win(128, 256, "phrase")],
  starts: [
    {
      beat: 0,
      seconds: 0,
      ends: [end(112, "bar4"), end(116, "bar"), end(128, "section"), end(132, "bar")],
    },
    { beat: 128, seconds: 64, ends: [end(240, "bar4"), end(256, "phrase")] },
  ],
};

const PLAN_120: CropPlan = {
  enabled: true,
  reason: null,
  band: [108, 132],
  suggestions: [win(0, 224, "section")],
  starts: [{ beat: 0, seconds: 0, ends: [end(224, "section"), end(240, "phrase")] }],
};

/** A 140 s song at 120 bpm with three sections and both lengths enabled. */
export const TIMELINE: Timeline = {
  map_id: "id0000000001",
  duration_s: 140,
  bpm: 120,
  hardest: "ExpertPlus",
  map_only: false,
  grid_drift_s: 0,
  nps: { Expert: series(4), ExpertPlus: series(6) },
  sections: [
    { start_beat: 0, end_beat: 128, start_s: 0, end_s: 64, nps: 3, intensity: 0.4 },
    { start_beat: 128, end_beat: 224, start_s: 64, end_s: 112, nps: 6, intensity: 1 },
    { start_beat: 224, end_beat: 280, start_s: 112, end_s: 140, nps: 2, intensity: 0.3 },
  ],
  lengths: { "60": PLAN_60, "120": PLAN_120 },
};
