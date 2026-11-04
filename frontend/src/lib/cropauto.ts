// Types and helpers for Auto crop: the three ranked windows the server proposes.
import type { Span } from "./crop";

/** One proposal from GET /api/maps/{id}/crop/suggestions. */
export interface CropProposal {
  rank: number;
  start_beat: number;
  end_beat: number;
  start_s: number;
  end_s: number;
  length_s: number;
  /** "1 min" or "2 min": the length it was cut for. */
  target: string;
  /** Points from 0 to 100: the sum of the breakdown. */
  score: number;
  /** Points per scoring component; they sum to `score`. */
  breakdown: ScorePart[];
  reason: string;
}

export interface ScorePart {
  key: string;
  label: string;
  points: number;
  max_points: number;
}

export interface CropSuggestions {
  map_id: string;
  duration_s: number;
  /** Why there is no proposal, when the list is empty. */
  reason: string | null;
  suggestions: CropProposal[];
}

export const spanOf = (p: CropProposal): Span => ({ start_s: p.start_s, end_s: p.end_s });

/** Score in whole points from 0 to 100 for the bar and its label. */
export const percent = (score: number): number => Math.round(Math.max(0, Math.min(100, score)));

/** Points as shown in the breakdown: one decimal, none when whole. */
export const points = (value: number): string => String(Math.round(value * 10) / 10);

/** "m:ss" for whole seconds, rounded to the nearest second. */
export function mmss(seconds: number): string {
  const total = Math.round(Math.max(0, Number.isFinite(seconds) ? seconds : 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/** Seconds in "m:ss" or "mm:ss" (seconds 00 to 59); null when it is not that shape. */
export function parseMmss(text: string): number | null {
  const m = /^(\d{1,3}):([0-5]\d)$/.exec(text.trim());
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

/** A selection narrower than this share of the song cannot hold three time labels. */
export const NARROW_SHARE = 0.3;

export interface TimeLabels {
  /** Too narrow for three labels: only the crop length is shown, centred on the selection. */
  narrow: boolean;
  /** Left and right edge of the selection, as a percentage of the chart width. */
  left: number;
  right: number;
  start: string;
  end: string;
  length: string;
}

/** The mm:ss labels above the crop: the start, the end and the length between them. */
export function timeLabels(start_s: number, end_s: number, duration: number): TimeLabels {
  const share = (s: number) =>
    duration > 0 ? Math.min(100, Math.max(0, (s / duration) * 100)) : 0;
  const left = share(start_s);
  const right = share(end_s);
  return {
    narrow: right - left < NARROW_SHARE * 100,
    left,
    right,
    start: mmss(start_s),
    end: mmss(end_s),
    length: mmss(end_s - start_s),
  };
}
