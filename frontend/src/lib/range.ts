// Parsing and display of the range filter inputs (length as m:ss, BPM and percentages as numbers).

/** Seconds for "m:ss" or plain seconds; null for empty text; undefined when not a duration. */
export function parseDuration(text: string): number | null | undefined {
  const t = text.trim();
  if (t === "") return null;
  const clock = /^(\d{1,3}):([0-5]?\d)$/.exec(t);
  if (clock) return Number(clock[1]) * 60 + Number(clock[2]);
  return /^\d{1,5}$/.test(t) ? Number(t) : undefined;
}

/** "m:ss" for the length inputs; empty for no bound. */
export function durationInput(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
    return "";
  }
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/** A finite number within bounds; null for empty text; undefined when invalid or out of range. */
export function parseBounded(text: string, min: number, max: number): number | null | undefined {
  const t = text.trim();
  if (t === "") return null;
  if (!/^\d{1,6}(\.\d{0,2})?$/.test(t)) return undefined;
  const n = Number(t);
  return n >= min && n <= max ? n : undefined;
}

/** True when a minimum and a maximum are both set and out of order. */
export function inverted(low: number | null, high: number | null): boolean {
  return low !== null && high !== null && low > high;
}

/** Length and BPM filters are whole numbers: a stale decimal link rounds out (min down, max up). */
export function wholeBound(name: string, value: number | null): number | null {
  if (value === null || !/^(duration|bpm)(Min|Max)$/.test(name)) return value;
  return name.endsWith("Max") ? Math.ceil(value) : Math.floor(value);
}
