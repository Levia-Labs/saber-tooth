// Library query state: URL encoding, API parameters and sort transitions. Pure functions.
import { STATUS_KEYS, type SortKey, type SortOrder, type StatusKey } from "../api/types";

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
];

export interface LibraryState {
  q: string;
  status: StatusKey[];
  env: string[];
  sort: SortKey;
  order: SortOrder;
}

export const DEFAULT_STATE: LibraryState = {
  q: "",
  status: [],
  env: [],
  sort: "title",
  order: "asc",
};

const DESC_FIRST = new Set<SortKey>(["errors", "warnings", "scanned_at", "duration", "bpm"]);
const MAX_Q = 200;
const MAX_ENV = 50;

function isStatus(value: string): value is StatusKey {
  return (STATUS_KEYS as readonly string[]).includes(value);
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
  return {
    q: (params.get("q") ?? "").slice(0, MAX_Q),
    status: unique(statuses.filter(isStatus)),
    env: unique(envs).slice(0, MAX_ENV),
    sort: isSort(sort) ? sort : DEFAULT_STATE.sort,
    order: order === "asc" || order === "desc" ? order : DEFAULT_STATE.order,
  };
}

/** URL search params for the address bar: only values that differ from the defaults. */
export function encodeState(state: LibraryState): URLSearchParams {
  const params = new URLSearchParams();
  const q = state.q.trim();
  if (q) params.set("q", q);
  if (state.status.length) params.set("status", state.status.join(","));
  for (const name of state.env) params.append("env", name);
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
    params.set("q_fields", "title,mapper");
  }
  if (state.status.length) params.set("status", state.status.join(","));
  for (const name of state.env) params.append("env", name);
  return params;
}

/** Sort after a header click: same key flips order, a new key starts at its natural order. */
export function nextSort(state: LibraryState, key: SortKey): Pick<LibraryState, "sort" | "order"> {
  if (state.sort === key) return { sort: key, order: state.order === "asc" ? "desc" : "asc" };
  return { sort: key, order: DESC_FIRST.has(key) ? "desc" : "asc" };
}

/** Number of active filters per header filter, for the badge. */
export function filterCounts(state: LibraryState): { title: number; status: number; env: number } {
  return {
    title: state.q.trim() ? 1 : 0,
    status: state.status.length,
    env: state.env.length,
  };
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}
