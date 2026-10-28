// Pure tick maths for the chart axes.
const TIME_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600];
const MAX_TIME_TICKS = 8;
const MAX_NPS_STEPS = 5;

const pad = (n: number): string => String(n).padStart(2, "0");

/** "mm:ss" for a whole-second tick. */
export function tickLabel(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
}

/** Seconds of the time ticks: 0 and every round step up to the duration, at most 9 of them. */
export function timeTicks(duration: number): number[] {
  if (!(duration > 0)) return [];
  const step =
    TIME_STEPS.find((s) => duration / s <= MAX_TIME_TICKS) ?? (TIME_STEPS.at(-1) as number);
  const out: number[] = [];
  for (let t = 0; t <= duration; t += step) out.push(t);
  return out;
}

/** Round notes-per-second ticks from 0; `top` is the last tick and covers the peak. */
export function npsTicks(peak: number): { ticks: number[]; top: number } {
  const p = Math.max(0, peak);
  let step = 1;
  for (let mag = 1; Math.ceil(p / step) > MAX_NPS_STEPS;) {
    for (const m of [2, 5, 10]) {
      step = mag * m;
      if (Math.ceil(p / step) <= MAX_NPS_STEPS) break;
    }
    mag *= 10;
  }
  const count = Math.max(1, Math.ceil(p / step));
  return { ticks: Array.from({ length: count + 1 }, (_, i) => i * step), top: count * step };
}

/** Vertical padding of the plot, as a fraction of its height, shared by the lines and the y axis. */
export const PAD_FRAC = 0.05;

/** Height of `value` above the plot bottom, 0 to 1, for a plot whose top tick is `top`. */
export const yFrac = (value: number, top: number): number =>
  PAD_FRAC + (top > 0 ? Math.min(1, Math.max(0, value / top)) : 0) * (1 - 2 * PAD_FRAC);
