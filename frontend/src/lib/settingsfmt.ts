// Display helpers for the Settings page.
const MB = 1024 ** 2;
const GB = 1024 ** 3;

/** "512 MB", "1.5 GB", "12 GB"; an en dash when the size is unknown. */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes) || bytes < 0) return "–";
  if (bytes < GB) return `${Math.round(bytes / MB)} MB`;
  const gb = bytes / GB;
  return `${gb < 10 ? gb.toFixed(1) : Math.round(gb)} GB`;
}

/** A whole percentage of `total`, clamped to 0..100; 0 when either number is unknown. */
export function percent(part: number | null | undefined, total: number | null | undefined): number {
  if (part === null || part === undefined || !total || total <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((part / total) * 100)));
}

/** The concurrency value limited to 1..max (a maximum below one counts as one). */
export function clampJobs(value: number, max: number): number {
  if (!Number.isFinite(value)) return 1;
  return Math.min(Math.max(1, max), Math.max(1, Math.round(value)));
}
