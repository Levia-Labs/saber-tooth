/**
 * The single column definition for the library list. The header, the rows and the skeleton rows
 * all take their grid tracks from `gridTemplate`, so they cannot drift apart.
 */

export type Breakpoint = "wide" | "mid" | "compact";
export type ColumnKey =
  | "cover"
  | "title"
  | "author"
  | "levels"
  | "length"
  | "bpm"
  | "env"
  | "status"
  | "actions"
  | "select"
  | "rating"
  | "upvotes"
  | "tags";
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
  env: "Env",
  status: "Status",
  actions: "Actions",
  select: "Select",
  rating: "Rating",
  upvotes: "Upvotes",
  tags: "Tags",
};

export const LIMITS: Partial<Record<ColumnKey, { min: number; max: number }>> = {
  title: { min: 100, max: 800 },
  author: { min: 100, max: 400 },
  levels: { min: 72, max: 400 },
  length: { min: 64, max: 200 },
  bpm: { min: 64, max: 200 },
  env: { min: 72, max: 400 },
  status: { min: 84, max: 300 },
  rating: { min: 72, max: 200 },
  upvotes: { min: 72, max: 200 },
  tags: { min: 96, max: 500 },
};

/**
 * Default widths, sized for the compact cells (Levels: the 23-character text "Ea | No | Ha | Ex | Ex+"; Status:
 * icon-only chip) so that Title, the flexible track, gets the rest at every viewport width.
 */
export const DEFAULTS: Record<Breakpoint, Record<string, number>> = {
  wide: {
    cover: 56,
    title: 200,
    author: 120,
    levels: 140,
    length: 88,
    bpm: 80,
    env: 120,
    status: 96,
    actions: 140,
  },
  mid: {
    cover: 56,
    title: 200,
    author: 120,
    levels: 140,
    length: 88,
    bpm: 80,
    status: 96,
    actions: 140,
  },
  compact: { cover: 64, title: 100, length: 88, bpm: 80, status: 100, actions: 140 },
};

/** Bumped when the default widths change, so widths saved against older defaults are dropped. */
const STORE_PREFIX = "saber-tooth.columns.v3.";
const LEGACY_PREFIXES = ["saber-tooth.columns.v1.", "saber-tooth.columns.v2."];

/** Tracks, default widths and storage key of one list; the library is the default. */
export interface ColumnSet {
  tracks: Record<Breakpoint, readonly ColumnKey[]>;
  defaults: Record<Breakpoint, Record<string, number>>;
  storePrefix: string;
  legacyPrefixes: readonly string[];
}

export const LIBRARY_COLUMNS: ColumnSet = {
  tracks: TRACKS,
  defaults: DEFAULTS,
  storePrefix: STORE_PREFIX,
  legacyPrefixes: LEGACY_PREFIXES,
};

const GAP = 12;
const PAD = 24;
const MAIN_PAD = 40;
const MAIN_MAX = 1480;
const SCROLL_BORDER = 2;
const SCROLLBAR = 17;
export const STEP = 16;
export const BIG_STEP = 64;

/** Width of the list's scroll content at a viewport width: page padding, border and scrollbar off. */
export function availableWidth(viewport: number): number {
  return Math.min(viewport, MAIN_MAX) - MAIN_PAD - SCROLL_BORDER - SCROLLBAR;
}

/** Rendered Title width at a viewport width: whatever the fixed tracks leave over. */
export function titleWidthAt(
  bp: Breakpoint,
  widths: Widths,
  viewport: number,
  set: ColumnSet = LIBRARY_COLUMNS,
): number {
  const rest = tableMinWidth(bp, widths, set) - width(bp, widths, "title", set);
  return Math.max(width(bp, widths, "title", set), availableWidth(viewport) - rest);
}

export function isResizable(key: ColumnKey): boolean {
  return LIMITS[key] !== undefined;
}

export function clampWidth(key: ColumnKey, px: number): number {
  const limit = LIMITS[key];
  if (!limit) return Number.isFinite(px) ? px : 0;
  const v = Number.isFinite(px) ? Math.round(px) : limit.min;
  return Math.min(limit.max, Math.max(limit.min, v));
}

export function defaultWidths(bp: Breakpoint, set: ColumnSet = LIBRARY_COLUMNS): Widths {
  return { ...set.defaults[bp] };
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

function width(bp: Breakpoint, widths: Widths, key: ColumnKey, set: ColumnSet): number {
  return widths[key] ?? set.defaults[bp][key] ?? 0;
}

/** CSS grid-template-columns for a breakpoint; Title is the flexible track. */
export function gridTemplate(
  bp: Breakpoint,
  widths: Widths,
  set: ColumnSet = LIBRARY_COLUMNS,
): string {
  return set.tracks[bp]
    .map((key) => {
      const w = width(bp, widths, key, set);
      return key === "title" ? `minmax(${w}px, 1fr)` : `${w}px`;
    })
    .join(" ");
}

/** Minimum table width in px; below it the scroll region scrolls horizontally. */
export function tableMinWidth(
  bp: Breakpoint,
  widths: Widths,
  set: ColumnSet = LIBRARY_COLUMNS,
): number {
  const cols = set.tracks[bp];
  const sum = cols.reduce((acc, key) => acc + width(bp, widths, key, set), 0);
  return sum + GAP * (cols.length - 1) + PAD;
}

/** Custom properties for the list container, one grid template and one min width per breakpoint. */
export function columnVars(
  all: Record<Breakpoint, Widths>,
  set: ColumnSet = LIBRARY_COLUMNS,
): Record<string, string> {
  const vars: Record<string, string> = {};
  for (const bp of BREAKPOINTS) {
    vars[`--cols-${bp}`] = gridTemplate(bp, all[bp], set);
    vars[`--min-${bp}`] = `${tableMinWidth(bp, all[bp], set)}px`;
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
export function loadWidths(
  bp: Breakpoint,
  storage: Storage | null = getStorage(),
  set: ColumnSet = LIBRARY_COLUMNS,
): Widths {
  const widths = defaultWidths(bp, set);
  try {
    for (const old of set.legacyPrefixes) storage?.removeItem(old + bp);
    const raw = storage?.getItem(set.storePrefix + bp);
    if (!raw) return widths;
    const saved: unknown = JSON.parse(raw);
    if (typeof saved !== "object" || saved === null) return widths;
    for (const key of set.tracks[bp]) {
      const v = (saved as Record<string, unknown>)[key];
      if (isResizable(key) && typeof v === "number" && Number.isFinite(v)) {
        widths[key] = clampWidth(key, v);
      }
    }
  } catch {
    return defaultWidths(bp, set);
  }
  return widths;
}

/** Persist widths, or clear them when they equal the defaults. Never throws. */
export function saveWidths(
  bp: Breakpoint,
  widths: Widths,
  storage: Storage | null = getStorage(),
  set: ColumnSet = LIBRARY_COLUMNS,
): void {
  try {
    if (!storage) return;
    const same = set.tracks[bp].every((k) => widths[k] === set.defaults[bp][k]);
    if (same) storage.removeItem(set.storePrefix + bp);
    else storage.setItem(set.storePrefix + bp, JSON.stringify(widths));
  } catch {
    /* storage unavailable or full: widths last for this session only */
  }
}
