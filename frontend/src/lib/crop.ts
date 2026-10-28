// Pure helpers for the crop panel: snapping, stepping and re-picking the window edges.
import type { CropEnd, CropPlan, CropStart, EndKind } from "../api/types";

export const EPS = 1e-6;

/** Strongest kind first: the order the server prefers an end in. */
export const KIND_RANK: Record<EndKind, number> = { section: 0, phrase: 1, bar4: 2, bar: 3 };

export const KIND_LABEL: Record<EndKind, string> = {
  section: "section boundary",
  phrase: "phrase line",
  bar4: "4-bar line",
  bar: "bar line",
};

export const CROP_TIPS = {
  create:
    "Write the chosen stretch of the song as a new folder beside this map. The original is never changed.",
  reset: "Go back to the suggested window.",
  toggle: "Show or hide the crop panel: cut a 1 or 2 minute highlight.",
} as const;

/** A chosen window, in beats. */
export interface Choice {
  start: number;
  end: number;
}

export const same = (a: number, b: number): boolean => Math.abs(a - b) < EPS;

/** "m:ss.s" for a time in seconds. */
export function clock(seconds: number): string {
  const tenths = Math.round(Math.max(0, seconds) * 10);
  const m = Math.floor(tenths / 600);
  return `${m}:${((tenths - m * 600) / 10).toFixed(1).padStart(4, "0")}`;
}

/** Song seconds under a pointer, clamped to the song. */
export function secondsAt(clientX: number, left: number, width: number, duration: number): number {
  if (width <= 0) return 0;
  return Math.min(duration, Math.max(0, ((clientX - left) / width) * duration));
}

export function nearest<T extends { seconds: number }>(points: readonly T[], seconds: number): T {
  let best = points[0] as T;
  for (const p of points) {
    if (Math.abs(p.seconds - seconds) < Math.abs(best.seconds - seconds)) best = p;
  }
  return best;
}

export const snapStart = (plan: CropPlan, seconds: number): CropStart =>
  nearest(plan.starts, seconds);

export const snapEnd = (start: CropStart, seconds: number): CropEnd => nearest(start.ends, seconds);

/** The strongest kind, then the length closest to the middle of the band, then the earlier end. */
export function pickEnd(start: CropStart, band: [number, number]): CropEnd {
  const target = (band[0] + band[1]) / 2;
  const off = (e: CropEnd) => Math.abs(e.seconds - start.seconds - target);
  return [...start.ends].sort(
    (a, b) => KIND_RANK[a.kind] - KIND_RANK[b.kind] || off(a) - off(b) || a.beat - b.beat,
  )[0] as CropEnd;
}

/** The end to show after the start changed: the old one when still allowed, else a new pick. */
export function endFor(start: CropStart, previous: number | null, band: [number, number]): CropEnd {
  const kept = start.ends.find((e) => previous !== null && same(e.beat, previous));
  return kept ?? pickEnd(start, band);
}

function stepIn<T extends { beat: number }>(
  points: readonly T[],
  current: number,
  dir: 1 | -1,
): T | undefined {
  const sorted = [...points].sort((a, b) => a.beat - b.beat);
  return dir === 1
    ? sorted.find((p) => p.beat > current + EPS)
    : sorted.reverse().find((p) => p.beat < current - EPS);
}

/** Next or previous start; every start is a section boundary, so Shift adds nothing here. */
export function stepStart(plan: CropPlan, current: number, dir: 1 | -1): CropStart {
  return (
    stepIn(plan.starts, current, dir) ??
    (plan.starts.find((s) => same(s.beat, current)) as CropStart)
  );
}

/** Next or previous allowed end; `jump` considers section ends only. */
export function stepEnd(start: CropStart, current: number, dir: 1 | -1, jump: boolean): CropEnd {
  const pool = jump ? start.ends.filter((e) => e.kind === "section") : start.ends;
  return (
    stepIn(pool, current, dir) ??
    start.ends.find((e) => same(e.beat, current)) ??
    (start.ends[0] as CropEnd)
  );
}

export function suggestion(plan: CropPlan): Choice | null {
  const best = plan.suggestions[0];
  return plan.enabled && best ? { start: best.start_beat, end: best.end_beat } : null;
}

/** Switching length: keep the start when the new plan has it and re-pick the end. */
export function keepStart(plan: CropPlan, choice: Choice | null): Choice | null {
  const start = choice ? plan.starts.find((s) => same(s.beat, choice.start)) : undefined;
  return start ? { start: start.beat, end: pickEnd(start, plan.band).beat } : null;
}
