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

/** "N BPM" for a tempo, or an en dash when unknown. */
export function formatBpm(bpm: number | null | undefined): string {
  if (bpm === null || bpm === undefined || !Number.isFinite(bpm) || bpm <= 0) return "–";
  return `${Math.round(bpm)} BPM`;
}
