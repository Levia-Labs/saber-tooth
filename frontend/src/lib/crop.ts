// Pure helpers for the crop panel: free window edges kept inside the song and above a minimum length.
import type { CropEnd, CropPlan, CropStart, EndKind } from "../api/types";

/** Strongest kind first: the order the server prefers an end in. */
export const KIND_RANK: Record<EndKind, number> = { section: 0, phrase: 1, bar4: 2, bar: 3 };

export const CROP_TIPS = {
  create:
    "Save the chosen stretch of the song as a new map in a folder beside this one. The original is never changed.",
  reset: "Go back to the suggested window.",
} as const;

/** A chosen window, in song seconds. */
export interface Span {
  start_s: number;
  end_s: number;
}

/** The shortest crop the server accepts, in seconds, when the timeline does not say. */
export const MIN_LENGTH_S = 1;
/** Arrow-key nudge of a handle, and the larger one with Shift. */
export const NUDGE_S = 0.1;
export const NUDGE_BIG_S = 1;

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

/** The strongest kind, then the length closest to the middle of the band, then the earlier end. */
export function pickEnd(start: CropStart, band: [number, number]): CropEnd {
  const target = (band[0] + band[1]) / 2;
  const off = (e: CropEnd) => Math.abs(e.seconds - start.seconds - target);
  return [...start.ends].sort(
    (a, b) => KIND_RANK[a.kind] - KIND_RANK[b.kind] || off(a) - off(b) || a.beat - b.beat,
  )[0] as CropEnd;
}

/** The plan's best window, or null when the length is off. */
export function suggestion(plan: CropPlan): Span | null {
  const best = plan.suggestions[0];
  return plan.enabled && best ? { start_s: best.start_s, end_s: best.end_s } : null;
}

/** Switching length: keep the start when the new plan has it and re-pick the end. */
export function keepStart(plan: CropPlan, span: Span | null): Span | null {
  const at = span?.start_s ?? -1;
  const start = plan.starts.find((s) => Math.abs(s.seconds - at) < 1e-3);
  return start ? { start_s: start.seconds, end_s: pickEnd(start, plan.band).seconds } : null;
}

const clamp = (v: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, v));
/** Milliseconds, so repeated 0.1 s nudges never drift. */
const tidy = (v: number): number => Math.round(v * 1000) / 1000;

/** A window start kept inside the song: from 0 to the last start that still fits `length`. */
export const clampStart = (start: number, length: number, duration: number): number =>
  Math.max(0, Math.min(duration - length, start));

/** Move one edge to `seconds`: inside the song, never closer to the other edge than `min`. */
export function moveEdge(
  span: Span,
  edge: "start" | "end",
  seconds: number,
  min: number,
  duration: number,
): Span {
  // Bounds round inward, so tidying the value can never cut the window below `min`.
  if (edge === "start") {
    return {
      ...span,
      start_s: clamp(tidy(seconds), 0, Math.floor((span.end_s - min) * 1000) / 1000),
    };
  }
  const lo = Math.ceil((span.start_s + min) * 1000) / 1000;
  return { ...span, end_s: clamp(tidy(seconds), lo, Math.floor(duration * 1000) / 1000) };
}

/** Nudge an edge by 0.1 s, or by 1 s with `big`. */
export function nudgeEdge(
  span: Span,
  edge: "start" | "end",
  dir: 1 | -1,
  big: boolean,
  min: number,
  duration: number,
): Span {
  const at = edge === "start" ? span.start_s : span.end_s;
  return moveEdge(span, edge, at + dir * (big ? NUDGE_BIG_S : NUDGE_S), min, duration);
}

/** Move the whole window so it starts at `start`, keeping its length, inside the song. */
export function shiftWindow(span: Span, start: number, duration: number): Span {
  const length = span.end_s - span.start_s;
  const at = tidy(clampStart(start, length, duration));
  return { start_s: at, end_s: tidy(at + length) };
}

/** Whether two windows are the same to the millisecond. */
export const sameSpan = (a: Span, b: Span): boolean =>
  Math.abs(a.start_s - b.start_s) < 1e-3 && Math.abs(a.end_s - b.end_s) < 1e-3;

/** The section holding `seconds`, if any. */
export function sectionAt<T extends { start_s: number; end_s: number }>(
  sections: readonly T[],
  seconds: number,
): T | undefined {
  return sections.find((s) => s.start_s <= seconds && seconds < s.end_s);
}
