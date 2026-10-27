// Library query state (search, status filter, sort) and its URL / API encodings. Pure.
export const SORTS = [
  ["title", "Title"],
  ["mapper", "Mapper"],
  ["environment", "Environment"],
  ["status", "Status"],
  ["errors", "Errors"],
  ["warnings", "Warnings"],
  ["scanned_at", "Last scanned"],
];
export const STATUSES = [
  ["all", "All"],
  ["error", "Errors"],
  ["warn", "Warnings"],
  ["ok", "Good"],
  ["unscanned", "Not scanned"],
  ["unreadable", "Unreadable"],
];
export const DEFAULTS = Object.freeze({ q: "", status: "all", sort: "title", order: "asc" });
const DESC_FIRST = new Set(["errors", "warnings", "scanned_at"]);

/** Parse a location.search string; unknown or invalid values fall back to the defaults. */
export function parseState(search) {
  const params = new URLSearchParams(search || "");
  const sort = params.get("sort");
  const status = params.get("status");
  const order = params.get("order");
  return {
    q: (params.get("q") || "").slice(0, 200),
    status: STATUSES.some(([k]) => k === status) ? status : DEFAULTS.status,
    sort: SORTS.some(([k]) => k === sort) ? sort : DEFAULTS.sort,
    order: order === "desc" || order === "asc" ? order : DEFAULTS.order,
  };
}

/** Query string for the address bar: only non-default values, "" when none. */
export function encodeState(state) {
  const params = new URLSearchParams();
  for (const key of Object.keys(DEFAULTS)) {
    const value = key === "q" ? state.q.trim() : state[key];
    if (value !== DEFAULTS[key]) params.set(key, value);
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

/** Query string (no leading "?") for GET /api/maps. */
export function apiQuery(state, offset, limit) {
  const params = new URLSearchParams({
    offset: String(offset),
    limit: String(limit),
    sort: state.sort,
    order: state.order,
  });
  const q = state.q.trim();
  if (q) params.set("q", q);
  if (state.status !== "all") params.set("status", state.status);
  return params.toString();
}

/** Sort state after a column header click: same key flips order, a new key starts at its natural order. */
export function nextSort(state, key) {
  if (state.sort === key) return { sort: key, order: state.order === "asc" ? "desc" : "asc" };
  return { sort: key, order: DESC_FIRST.has(key) ? "desc" : "asc" };
}
