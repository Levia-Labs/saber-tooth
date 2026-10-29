// Arrow-button and ArrowUp/ArrowDown stepping of a range bound.

/** The value after one step: `current` (or `start` when unset) plus `delta`, kept within lo..hi. */
export function stepBound(
  current: number | null,
  delta: number,
  lo: number,
  hi: number,
  start: number,
): number {
  const top = Math.max(lo, hi);
  return Math.min(top, Math.max(lo, (current ?? start) + delta));
}
