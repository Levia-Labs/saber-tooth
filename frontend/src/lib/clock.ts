// The "mm:ss" text of the length filter inputs; one pure parse and one pure format.

/** Seconds for "m:ss" or "mm:ss"; null for empty text; undefined for anything else. */
export function parseClock(text: string): number | null | undefined {
  const t = text.trim();
  if (t === "") return null;
  const m = /^(\d{1,3}):([0-5]\d)$/.exec(t);
  return m ? Number(m[1]) * 60 + Number(m[2]) : undefined;
}

/** "mm:ss" for whole seconds; empty for no bound or a value that is not a duration. */
export function formatClock(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
    return "";
  }
  const total = Math.round(seconds);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(
    2,
    "0",
  )}`;
}
