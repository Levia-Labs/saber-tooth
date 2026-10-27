// Library query state: URL encoding, API parameters and sort transitions. Pure functions.
import {
  LEVEL_KEYS,
  STATUS_KEYS,
  type LevelKey,
  type SortKey,
  type SortOrder,
  type StatusKey,
} from "../api/types";

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
  return {
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
  };
}

export function totalFilters(counts: FilterCounts): number {
  return counts.title + counts.author + counts.levels + counts.status + counts.env;
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}
