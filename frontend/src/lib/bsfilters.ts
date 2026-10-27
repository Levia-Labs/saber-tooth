// BeatSaver search state: URL encoding, API parameters and preset conversion. Pure functions.
// The URL keys are the API query keys, so a preset (stored as those keys) is also a shareable URL.
import { LEVEL_KEYS, type LevelKey } from "../api/types";

export const BS_ORDERS = [
  "Latest",
  "Relevance",
  "Rating",
  "Curated",
  "Random",
  "Duration",
] as const;
export type BsOrder = (typeof BS_ORDERS)[number];
export type Scope = "any" | "all";

export interface BsState {
  q: string;
  /** Tags the map may have (any of them). */
  tags: string[];
  /** Minimum rating as a fraction, 0 to 1. */
  minRating: number | null;
  /** Minimum upvote count. */
  minUpvotes: number | null;
  npsMin: number | null;
  npsMax: number | null;
  npsScope: Scope;
  /** Standard difficulties the map must have, in `diffsMode`. */
  diffs: LevelKey[];
  diffsMode: Scope;
  ranked: boolean;
  order: BsOrder;
  ascending: boolean;
  from: string;
  to: string;
  bpmMin: number | null;
  bpmMax: number | null;
  durationMin: number | null;
  durationMax: number | null;
}

export const DEFAULT_BS_STATE: BsState = {
  q: "",
  tags: [],
  minRating: null,
  minUpvotes: null,
  npsMin: null,
  npsMax: null,
  npsScope: "any",
  diffs: [],
  diffsMode: "all",
  ranked: false,
  order: "Latest",
  ascending: false,
  from: "",
  to: "",
  bpmMin: null,
  bpmMax: null,
  durationMin: null,
  durationMax: null,
};

export const BS_PAGE_SIZE = 40;
const MAX_Q = 200;
const MAX_TAGS = 30;
const MAX_TAG = 40;
const DATE = /^\d{4}-\d{2}-\d{2}$/;

type NumKey =
  | "minRating"
  | "minUpvotes"
  | "npsMin"
  | "npsMax"
  | "bpmMin"
  | "bpmMax"
  | "durationMin"
  | "durationMax";

/** URL and API key, and the inclusive bounds, of every numeric filter. */
export const NUMBERS: Record<NumKey, { key: string; min: number; max: number }> = {
  minRating: { key: "min_rating", min: 0, max: 1 },
  minUpvotes: { key: "min_upvotes", min: 0, max: 1_000_000 },
  npsMin: { key: "nps_min", min: 0, max: 30 },
  npsMax: { key: "nps_max", min: 0, max: 30 },
  bpmMin: { key: "bpm_min", min: 0, max: 1000 },
  bpmMax: { key: "bpm_max", min: 0, max: 1000 },
  durationMin: { key: "duration_min", min: 0, max: 7200 },
  durationMax: { key: "duration_max", min: 0, max: 7200 },
};
const NUM_KEYS = Object.keys(NUMBERS) as NumKey[];

function isLevel(value: string): value is LevelKey {
  return (LEVEL_KEYS as readonly string[]).includes(value);
}

function isOrder(value: string | null): value is BsOrder {
  return value !== null && (BS_ORDERS as readonly string[]).includes(value);
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}

function number(raw: string | null, min: number, max: number): number | null {
  if (raw === null || raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

export function cleanTag(tag: string): string {
  return tag.trim().toLowerCase().replaceAll(/[,|!]/g, "").slice(0, MAX_TAG);
}

/** Parse a location.search string; unknown or out of range values fall back to the defaults. */
export function parseBsState(search: string): BsState {
  const p = new URLSearchParams(search);
  const order = p.get("order");
  const state: BsState = {
    ...DEFAULT_BS_STATE,
    q: (p.get("q") ?? "").slice(0, MAX_Q),
    tags: unique(
      p
        .getAll("tags")
        .flatMap((v) => v.split(","))
        .map(cleanTag)
        .filter(Boolean),
    ).slice(0, MAX_TAGS),
    npsScope: p.get("nps_scope") === "all" ? "all" : "any",
    diffs: unique(
      p
        .getAll("diffs")
        .flatMap((v) => v.split(","))
        .filter(isLevel),
    ),
    diffsMode: p.get("diffs_mode") === "any" ? "any" : "all",
    ranked: p.get("ranked") === "true",
    order: isOrder(order) ? order : DEFAULT_BS_STATE.order,
    ascending: p.get("ascending") === "true",
    from: DATE.test(p.get("from") ?? "") ? (p.get("from") as string) : "",
    to: DATE.test(p.get("to") ?? "") ? (p.get("to") as string) : "",
  };
  for (const name of NUM_KEYS) {
    const { key, min, max } = NUMBERS[name];
    state[name] = number(p.get(key), min, max);
  }
  return state;
}

/** URL search params for the address bar: only values that differ from the defaults. */
export function encodeBsState(state: BsState): URLSearchParams {
  const p = new URLSearchParams();
  const q = state.q.trim();
  if (q) p.set("q", q);
  if (state.tags.length) p.set("tags", state.tags.join(","));
  for (const name of NUM_KEYS) {
    const value = state[name];
    if (value !== null) p.set(NUMBERS[name].key, String(value));
  }
  if (state.npsScope === "all") p.set("nps_scope", "all");
  if (state.diffs.length) p.set("diffs", state.diffs.join(","));
  if (state.diffs.length && state.diffsMode === "any") p.set("diffs_mode", "any");
  if (state.ranked) p.set("ranked", "true");
  if (state.order !== DEFAULT_BS_STATE.order) p.set("order", state.order);
  if (state.ascending) p.set("ascending", "true");
  if (state.from) p.set("from", state.from);
  if (state.to) p.set("to", state.to);
  return p;
}

/** beatsaver.com search address for the filters that map cleanly: text, tags and order. */
export function bsSiteUrl(state: BsState): string {
  const p = new URLSearchParams();
  const q = state.q.trim();
  if (q) p.set("q", q);
  if (state.tags.length) p.set("tags", state.tags.join(","));
  if (state.order !== DEFAULT_BS_STATE.order) p.set("order", state.order);
  const qs = p.toString();
  return qs ? `https://beatsaver.com/search?${qs}` : "https://beatsaver.com";
}

/** Query parameters for GET /api/beatsaver/search and the playlist routes. */
export function bsApiParams(state: BsState, cursor: string | null, limit: number): URLSearchParams {
  const p = encodeBsState(state);
  p.set("limit", String(limit));
  if (cursor) p.set("cursor", cursor);
  return p;
}

/** The filters as the string map a preset stores. */
export function presetFilters(state: BsState): Record<string, string> {
  return Object.fromEntries(encodeBsState(state));
}

/** State for a stored preset; invalid entries fall back to the defaults. */
export function stateFromPreset(filters: Record<string, string>): BsState {
  return parseBsState(new URLSearchParams(filters).toString());
}

export interface BsCounts {
  title: number;
  levels: number;
  rating: number;
  tags: number;
  tempo: number;
  more: number;
}

/** Number of active filters per header filter, for the badge. */
export function bsCounts(s: BsState): BsCounts {
  const n = (...v: unknown[]) => v.filter((x) => x !== null && x !== "" && x !== false).length;
  return {
    title: n(s.q.trim()),
    levels: s.diffs.length + n(s.npsMin, s.npsMax),
    rating: n(s.minRating, s.minUpvotes),
    tags: s.tags.length,
    tempo: n(s.bpmMin, s.bpmMax, s.durationMin, s.durationMax),
    more: n(s.ranked, s.from, s.to),
  };
}

export function bsTotal(c: BsCounts): number {
  return c.title + c.levels + c.rating + c.tags + c.tempo + c.more;
}

/** True when the state has no filter set (order and direction do not count). */
export function isBsDefault(state: BsState): boolean {
  return bsTotal(bsCounts(state)) === 0;
}

/** Keep the sort, drop every filter. */
export function clearBsFilters(state: BsState): BsState {
  return { ...DEFAULT_BS_STATE, order: state.order, ascending: state.ascending };
}
