// Library query state: URL encoding, API parameters and sort transitions. Pure functions.
import {
  LEVEL_KEYS,
  STATUS_KEYS,
  type LevelKey,
  type SortKey,
  type SortOrder,
  type StatusKey,
} from "../api/types";
import { inverted } from "./range";

export const SORT_KEYS: readonly SortKey[] = [
  "title",
  "mapper",
  "environment",
  "status",
  "errors",
  "warnings",
  "scanned_at",
  "duration",
  "bpm",
  "levels",
];

/** The one text search is either over titles (Title filter) or over mapper names (Author filter). */
export type SearchField = "title" | "mapper";
export type LevelMode = "any" | "all";

export interface LibraryState {
  q: string;
  qField: SearchField;
  status: StatusKey[];
  env: string[];
  mapper: string[];
  level: LevelKey[];
  levelMode: LevelMode;
  /** Length bounds in seconds. */
  durationMin: number | null;
  durationMax: number | null;
  bpmMin: number | null;
  bpmMax: number | null;
  sort: SortKey;
  order: SortOrder;
}

export const DEFAULT_STATE: LibraryState = {
  q: "",
  qField: "title",
  status: [],
  env: [],
  mapper: [],
  level: [],
  levelMode: "any",
  durationMin: null,
  durationMax: null,
  bpmMin: null,
  bpmMax: null,
  sort: "title",
  order: "asc",
};

const DESC_FIRST = new Set<SortKey>([
  "errors",
  "warnings",
  "scanned_at",
  "duration",
  "bpm",
  "levels",
]);
const MAX_Q = 200;
const MAX_ENV = 50;
const MAX_MAPPER = 50;
const MAX_NAME = 200;

/** URL and API key and the inclusive bounds of the numeric library filters. */
export const RANGES = {
  durationMin: { key: "duration_min", min: 0, max: 7200 },
  durationMax: { key: "duration_max", min: 0, max: 7200 },
  bpmMin: { key: "bpm_min", min: 0, max: 1000 },
  bpmMax: { key: "bpm_max", min: 0, max: 1000 },
} as const;
type RangeName = keyof typeof RANGES;
const RANGE_NAMES = Object.keys(RANGES) as RangeName[];

function bounded(raw: string | null, min: number, max: number): number | null {
  if (raw === null || raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

function isStatus(value: string): value is StatusKey {
  return (STATUS_KEYS as readonly string[]).includes(value);
}

function isLevel(value: string): value is LevelKey {
  return (LEVEL_KEYS as readonly string[]).includes(value);
}

function isSort(value: string | null): value is SortKey {
  return value !== null && (SORT_KEYS as readonly string[]).includes(value);
}

function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}

/** Parse a location.search string; unknown values fall back to the defaults. */
export function parseState(search: string): LibraryState {
  const params = new URLSearchParams(search);
  const sort = params.get("sort");
  const order = params.get("order");
  const statuses = params.getAll("status").flatMap((v) => v.split(","));
  const envs = params.getAll("env").filter((v) => v !== "");
  const mappers = params.getAll("mapper").filter((v) => v !== "" && v.length <= MAX_NAME);
  const levels = params.getAll("level").flatMap((v) => v.split(","));
  const q = (params.get("q") ?? "").slice(0, MAX_Q);
  const ranges = Object.fromEntries(
    RANGE_NAMES.map((name) => {
      const { key, min, max } = RANGES[name];
      return [name, bounded(params.get(key), min, max)];
    }),
  ) as Pick<LibraryState, RangeName>;
  return {
    ...ranges,
    q,
    qField: q && params.get("qf") === "mapper" ? "mapper" : "title",
    status: unique(statuses.filter(isStatus)),
    env: unique(envs).slice(0, MAX_ENV),
    mapper: unique(mappers).slice(0, MAX_MAPPER),
    level: unique(levels.filter(isLevel)),
    levelMode: params.get("lmode") === "all" ? "all" : "any",
    sort: isSort(sort) ? sort : DEFAULT_STATE.sort,
    order: order === "asc" || order === "desc" ? order : DEFAULT_STATE.order,
  };
}

/** URL search params for the address bar: only values that differ from the defaults. */
export function encodeState(state: LibraryState): URLSearchParams {
  const params = new URLSearchParams();
  const q = state.q.trim();
  if (q) params.set("q", q);
  if (q && state.qField === "mapper") params.set("qf", "mapper");
  if (state.status.length) params.set("status", state.status.join(","));
  for (const name of state.env) params.append("env", name);
  for (const name of state.mapper) params.append("mapper", name);
  for (const key of state.level) params.append("level", key);
  if (state.level.length && state.levelMode === "all") params.set("lmode", "all");
  for (const name of RANGE_NAMES) {
    if (state[name] !== null) params.set(RANGES[name].key, String(state[name]));
  }
  if (state.sort !== DEFAULT_STATE.sort) params.set("sort", state.sort);
  if (state.order !== DEFAULT_STATE.order) params.set("order", state.order);
  return params;
}

/** Query parameters for GET /api/maps. */
export function apiParams(state: LibraryState, offset: number, limit: number): URLSearchParams {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
    sort: state.sort,
    order: state.order,
  });
  const q = state.q.trim();
  if (q) {
    params.set("q", q);
    params.set("q_fields", state.qField);
  }
  if (state.status.length) params.set("status", state.status.join(","));
  for (const name of state.env) params.append("env", name);
  for (const name of state.mapper) params.append("mapper", name);
  if (state.level.length) {
    for (const key of state.level) params.append("level", key);
    if (state.levelMode === "all") params.set("level_mode", "all");
  }
  // An inverted pair would answer 400; it is ignored until the user fixes it.
  const skip = new Set<RangeName>();
  if (inverted(state.durationMin, state.durationMax)) skip.add("durationMin").add("durationMax");
  if (inverted(state.bpmMin, state.bpmMax)) skip.add("bpmMin").add("bpmMax");
  for (const name of RANGE_NAMES) {
    if (state[name] !== null && !skip.has(name)) params.set(RANGES[name].key, String(state[name]));
  }
  return params;
}

/** Sort after a header click: same key flips order, a new key starts at its natural order. */
export function nextSort(state: LibraryState, key: SortKey): Pick<LibraryState, "sort" | "order"> {
  if (state.sort === key) return { sort: key, order: state.order === "asc" ? "desc" : "asc" };
  return { sort: key, order: DESC_FIRST.has(key) ? "desc" : "asc" };
}

export interface FilterCounts {
  title: number;
  author: number;
  levels: number;
  status: number;
  env: number;
  length: number;
  bpm: number;
}

/** Number of active filters per header filter, for the badge. */
export function filterCounts(state: LibraryState): FilterCounts {
  const text = state.q.trim() ? 1 : 0;
  return {
    title: state.qField === "title" ? text : 0,
    author: state.mapper.length + (state.qField === "mapper" ? text : 0),
    levels: state.level.length,
    status: state.status.length,
    env: state.env.length,
    length: [state.durationMin, state.durationMax].filter((v) => v !== null).length,
    bpm: [state.bpmMin, state.bpmMax].filter((v) => v !== null).length,
  };
}

export function totalFilters(counts: FilterCounts): number {
  return (
    counts.title +
    counts.author +
    counts.levels +
    counts.status +
    counts.env +
    counts.length +
    counts.bpm
  );
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}
