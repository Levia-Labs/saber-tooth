/** Pure calendar helpers on ISO `YYYY-MM-DD` strings; local dates, no time zone shifts. */

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

export function parseIso(value: string): Date | null {
  const m = ISO.exec(value);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const ok = d.getMonth() === Number(m[2]) - 1 && d.getDate() === Number(m[3]);
  return ok ? d : null;
}

export function toIso(d: Date): string {
  const p = (n: number, w = 2) => String(n).padStart(w, "0");
  return `${p(d.getFullYear(), 4)}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function addDays(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
}

/** Move by whole months, clamping the day to the target month's length. */
export function addMonths(d: Date, n: number): Date {
  const first = new Date(d.getFullYear(), d.getMonth() + n, 1);
  const last = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
  return new Date(first.getFullYear(), first.getMonth(), Math.min(d.getDate(), last));
}

/** Clamp to an optional inclusive ISO range. */
export function clampDate(d: Date, min?: string, max?: string): Date {
  const lo = min ? parseIso(min) : null;
  const hi = max ? parseIso(max) : null;
  if (lo && d < lo) return lo;
  if (hi && d > hi) return hi;
  return d;
}

export function inRange(d: Date, min?: string, max?: string): boolean {
  return clampDate(d, min, max).getTime() === d.getTime();
}

/** Index 0..6 of the weekday relative to the locale's first day of the week. */
export function firstWeekday(locale?: string): number {
  const info = new Intl.Locale(locale ?? navigator.language) as unknown as {
    weekInfo?: { firstDay: number };
    getWeekInfo?: () => { firstDay: number };
  };
  const first = info.getWeekInfo?.().firstDay ?? info.weekInfo?.firstDay ?? 7;
  return first % 7;
}

/** The weeks (arrays of 7 dates) that cover the month of `view`. */
export function monthWeeks(view: Date, weekStart: number): Date[][] {
  const first = new Date(view.getFullYear(), view.getMonth(), 1);
  const lead = (first.getDay() - weekStart + 7) % 7;
  const start = addDays(first, -lead);
  const days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
  const rows = Math.ceil((lead + days) / 7);
  return Array.from({ length: rows }, (_, r) =>
    Array.from({ length: 7 }, (_, c) => addDays(start, r * 7 + c)),
  );
}

export function sameDay(a: Date, b: Date): boolean {
  return toIso(a) === toIso(b);
}
