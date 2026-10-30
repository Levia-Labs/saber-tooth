// Small display formatters.
export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** "m:ss" for a duration in seconds, or an en dash when unknown. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
    return "–";
  }
  const total = Math.round(seconds);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Compact count: 950, 1.2k, 15k, 1.1M. */
export function formatCount(n: number): string {
  if (!Number.isFinite(n) || n < 0) return "0";
  if (n < 1000) return String(Math.round(n));
  const [value, unit] = n < 1_000_000 ? [n / 1000, "k"] : [n / 1_000_000, "M"];
  const text = value < 10 ? value.toFixed(1).replace(/\.0$/, "") : String(Math.round(value));
  return text + unit;
}

/** "N BPM" for a tempo, or an en dash when unknown. */
export function formatBpm(bpm: number | null | undefined): string {
  if (bpm === null || bpm === undefined || !Number.isFinite(bpm) || bpm <= 0) return "–";
  return `${Math.round(bpm)} BPM`;
}

/** The tempo number alone for the BPM column, whose header carries the unit; an en dash when unknown. */
export function formatBpmValue(bpm: number | null | undefined): string {
  return formatBpm(bpm).replace(/ BPM$/, "");
}

/** The BPM cell's accessible name: "128 BPM", or undefined when the tempo is unknown. */
export function bpmLabel(bpm: number | null | undefined): string | undefined {
  const text = formatBpm(bpm);
  return text === "–" ? undefined : text;
}
