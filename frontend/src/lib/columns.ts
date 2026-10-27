/**
 * The single column definition for the library list. The header, the rows and the skeleton rows
 * all take their grid tracks from `gridTemplate`, so they cannot drift apart.
 */

export type Breakpoint = "wide" | "mid" | "compact";
export type ColumnKey =
  "cover" | "title" | "author" | "levels" | "length" | "bpm" | "env" | "status" | "actions";
export type Widths = Partial<Record<ColumnKey, number>>;

export const BREAKPOINTS: readonly Breakpoint[] = ["wide", "mid", "compact"];

/** Visible columns, in grid order, per breakpoint. Below 720px rows become cards with no header. */
export const TRACKS: Record<Breakpoint, readonly ColumnKey[]> = {
  wide: ["cover", "title", "author", "levels", "length", "bpm", "env", "status", "actions"],
  mid: ["cover", "title", "author", "levels", "length", "bpm", "status", "actions"],
  compact: ["cover", "title", "length", "bpm", "status", "actions"],
};

/** Column keys the grid must render in every row cell, in order; `sub` is the compact subtitle. */
export const ROW_CELLS: readonly (ColumnKey | "sub")[] = [
  "cover",
  "title",
  "sub",
  "author",
  "levels",
  "length",
  "bpm",
  "env",
  "status",
  "actions",
];

export const LABELS: Record<ColumnKey, string> = {
  cover: "Image",
  title: "Title",
  author: "Author",
  levels: "Levels",
  length: "Length",
  bpm: "BPM",
  env: "Environment",
  status: "Status",
  actions: "Actions",
};

export const LIMITS: Partial<Record<ColumnKey, { min: number; max: number }>> = {
  title: { min: 100, max: 800 },
  author: { min: 100, max: 400 },
  levels: { min: 120, max: 400 },
  length: { min: 56, max: 200 },
  bpm: { min: 56, max: 200 },
  env: { min: 100, max: 400 },
  status: { min: 120, max: 300 },
};

export const DEFAULTS: Record<Breakpoint, Record<string, number>> = {
  wide: {
    cover: 56,
    title: 160,
    author: 120,
    levels: 150,
    length: 60,
    bpm: 84,
    env: 130,
    status: 130,
    actions: 140,
  },
  mid: {
    cover: 56,
    title: 160,
    author: 120,
    levels: 150,
    length: 60,
    bpm: 84,
    status: 130,
    actions: 140,
  },
  compact: { cover: 64, title: 100, length: 76, bpm: 88, status: 150, actions: 156 },
};

const GAP = 12;
const PAD = 24;
const STORE_PREFIX = "saber-tooth.columns.v1.";
export const STEP = 16;
export const BIG_STEP = 64;

export function isResizable(key: ColumnKey): boolean {
  return LIMITS[key] !== undefined;
}

export function clampWidth(key: ColumnKey, px: number): number {
  const limit = LIMITS[key];
  if (!limit) return Number.isFinite(px) ? px : 0;
  const v = Number.isFinite(px) ? Math.round(px) : limit.min;
  return Math.min(limit.max, Math.max(limit.min, v));
}

export function defaultWidths(bp: Breakpoint): Widths {
  return { ...DEFAULTS[bp] };
}

/** Width after an arrow key, or null when the key is not a resize key. */
export function stepWidth(
  key: ColumnKey,
  current: number,
  arrow: string,
  big: boolean,
): number | null {
  const step = big ? BIG_STEP : STEP;
  if (arrow === "ArrowLeft") return clampWidth(key, current - step);
  if (arrow === "ArrowRight") return clampWidth(key, current + step);
  return null;
}

function width(bp: Breakpoint, widths: Widths, key: ColumnKey): number {
  return widths[key] ?? DEFAULTS[bp][key] ?? 0;
}

/** CSS grid-template-columns for a breakpoint; Title is the flexible track. */
export function gridTemplate(bp: Breakpoint, widths: Widths): string {
  return TRACKS[bp]
    .map((key) => {
      const w = width(bp, widths, key);
      return key === "title" ? `minmax(${w}px, 1fr)` : `${w}px`;
    })
    .join(" ");
}

/** Minimum table width in px; below it the scroll region scrolls horizontally. */
export function tableMinWidth(bp: Breakpoint, widths: Widths): number {
  const cols = TRACKS[bp];
  const sum = cols.reduce((acc, key) => acc + width(bp, widths, key), 0);
  return sum + GAP * (cols.length - 1) + PAD;
}

/** Custom properties for the list container, one grid template and one min width per breakpoint. */
export function columnVars(all: Record<Breakpoint, Widths>): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const bp of BREAKPOINTS) {
    vars[`--cols-${bp}`] = gridTemplate(bp, all[bp]);
    vars[`--min-${bp}`] = `${tableMinWidth(bp, all[bp])}px`;
  }
  return vars;
}

export function getStorage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Saved widths merged over the defaults; any storage or parse failure yields the defaults. */
export function loadWidths(bp: Breakpoint, storage: Storage | null = getStorage()): Widths {
  const widths = defaultWidths(bp);
  try {
    const raw = storage?.getItem(STORE_PREFIX + bp);
    if (!raw) return widths;
    const saved: unknown = JSON.parse(raw);
    if (typeof saved !== "object" || saved === null) return widths;
    for (const key of TRACKS[bp]) {
      const v = (saved as Record<string, unknown>)[key];
      if (isResizable(key) && typeof v === "number" && Number.isFinite(v)) {
        widths[key] = clampWidth(key, v);
      }
    }
  } catch {
    return defaultWidths(bp);
  }
  return widths;
}

/** Persist widths, or clear them when they equal the defaults. Never throws. */
export function saveWidths(
  bp: Breakpoint,
  widths: Widths,
  storage: Storage | null = getStorage(),
): void {
  try {
    if (!storage) return;
    const same = TRACKS[bp].every((k) => widths[k] === DEFAULTS[bp][k]);
    if (same) storage.removeItem(STORE_PREFIX + bp);
    else storage.setItem(STORE_PREFIX + bp, JSON.stringify(widths));
  } catch {
    /* storage unavailable or full: widths last for this session only */
  }
}
