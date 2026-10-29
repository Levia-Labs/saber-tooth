// BeatSaver playlist search state: URL encoding, API parameters, client-side filter and sort.
// The URL keys are the API query keys, so the address is shareable.
import type { BsPlaylist } from "../api/beatsaver";
import { wholeBound } from "./range";

export const PL_ORDERS = ["Latest", "Relevance", "Rating", "Curated"] as const;
export type PlOrder = (typeof PL_ORDERS)[number];
/** Orders applied in the browser, among the playlists loaded so far. */
export const PL_LOCAL_SORTS = ["maps", "upvotes", "length"] as const;
export type PlLocalSort = (typeof PL_LOCAL_SORTS)[number];
export const PL_LOCAL_LABELS: Record<PlLocalSort, string> = {
  maps: "Maps (loaded playlists)",
  upvotes: "Upvotes (loaded playlists)",
  length: "Length (loaded playlists)",
};
export const PL_ORDER_LABELS: Record<PlOrder, string> = {
  Latest: "Created",
  Relevance: "Relevance",
  Rating: "Rating",
  Curated: "Curated",
};

export interface PlState {
  q: string;
  /** Author text, applied to the loaded playlists. */
  owner: string;
  order: PlOrder;
  localSort: PlLocalSort | null;
  ascending: boolean;
  curated: boolean;
  verified: boolean;
  npsMin: number | null;
  npsMax: number | null;
  from: string;
  to: string;
  mapsMin: number | null;
  mapsMax: number | null;
  minRating: number | null;
  minUpvotes: number | null;
  durationMin: number | null;
  durationMax: number | null;
}

export const DEFAULT_PL_STATE: PlState = {
  q: "",
  owner: "",
  order: "Latest",
  localSort: null,
  ascending: false,
  curated: false,
  verified: false,
  npsMin: null,
  npsMax: null,
  from: "",
  to: "",
  mapsMin: null,
  mapsMax: null,
  minRating: null,
  minUpvotes: null,
  durationMin: null,
  durationMax: null,
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;

type NumKey =
  | "npsMin"
  | "npsMax"
  | "mapsMin"
  | "mapsMax"
  | "minRating"
  | "minUpvotes"
  | "durationMin"
  | "durationMax";

export const PL_NUMBERS: Record<NumKey, { key: string; min: number; max: number }> = {
  npsMin: { key: "min_nps", min: 0, max: 30 },
  npsMax: { key: "max_nps", min: 0, max: 30 },
  mapsMin: { key: "maps_min", min: 0, max: 1_000_000 },
  mapsMax: { key: "maps_max", min: 0, max: 1_000_000 },
  minRating: { key: "min_rating", min: 0, max: 1 },
  minUpvotes: { key: "min_upvotes", min: 0, max: 1_000_000 },
  durationMin: { key: "duration_min", min: 0, max: 360_000 },
  durationMax: { key: "duration_max", min: 0, max: 360_000 },
};
const NUM_KEYS = Object.keys(PL_NUMBERS) as NumKey[];

const isOrder = (v: string | null): v is PlOrder =>
  v !== null && (PL_ORDERS as readonly string[]).includes(v);
const isLocal = (v: string | null): v is PlLocalSort =>
  v !== null && (PL_LOCAL_SORTS as readonly string[]).includes(v);

function number(raw: string | null, min: number, max: number): number | null {
  if (raw === null || raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) && n >= min && n <= max ? n : null;
}

export function parsePlState(search: string): PlState {
  const p = new URLSearchParams(search);
  const order = p.get("order");
  const local = p.get("lsort");
  const state: PlState = {
    ...DEFAULT_PL_STATE,
    q: (p.get("q") ?? "").slice(0, 200),
    owner: (p.get("owner") ?? "").slice(0, 200),
    order: isOrder(order) ? order : DEFAULT_PL_STATE.order,
    localSort: isLocal(local) ? local : null,
    ascending: p.get("ascending") === "true",
    curated: p.get("curated") === "true",
    verified: p.get("verified") === "true",
    from: DATE.test(p.get("from") ?? "") ? (p.get("from") as string) : "",
    to: DATE.test(p.get("to") ?? "") ? (p.get("to") as string) : "",
  };
  for (const name of NUM_KEYS) {
    const { key, min, max } = PL_NUMBERS[name];
    state[name] = wholeBound(name, number(p.get(key), min, max));
  }
  return state;
}

export function encodePlState(state: PlState): URLSearchParams {
  const p = new URLSearchParams();
  if (state.q.trim()) p.set("q", state.q.trim());
  if (state.owner.trim()) p.set("owner", state.owner.trim());
  for (const name of NUM_KEYS) {
    const value = state[name];
    if (value !== null) p.set(PL_NUMBERS[name].key, String(value));
  }
  if (state.curated) p.set("curated", "true");
  if (state.verified) p.set("verified", "true");
  if (state.order !== DEFAULT_PL_STATE.order) p.set("order", state.order);
  if (state.localSort) p.set("lsort", state.localSort);
  if (state.ascending) p.set("ascending", "true");
  if (state.from) p.set("from", state.from);
  if (state.to) p.set("to", state.to);
  return p;
}

/** Query for the API: no browser-only keys; an inverted range is ignored until fixed. */
export function plApiParams(state: PlState, cursor: string | null): URLSearchParams {
  const p = encodePlState(state);
  p.delete("lsort");
  p.delete("owner");
  for (const [low, high] of [
    ["maps_min", "maps_max"],
    ["duration_min", "duration_max"],
    ["min_nps", "max_nps"],
  ] as const) {
    if (Number(p.get(low) ?? "-1") > Number(p.get(high) ?? "Infinity")) {
      p.delete(low);
      p.delete(high);
    }
  }
  if (cursor) p.set("cursor", cursor);
  return p;
}

/** The part of the state that decides what the server returns; the browser-only parts are left out. */
export function plFetched(state: PlState): PlState {
  return { ...state, owner: "", localSort: null };
}

export function isPlDefault(state: PlState): boolean {
  return encodePlState({ ...state, order: "Latest", localSort: null, ascending: false }).size === 0;
}

export function clearPlFilters(state: PlState): PlState {
  return {
    ...DEFAULT_PL_STATE,
    order: state.order,
    localSort: state.localSort,
    ascending: state.ascending,
  };
}

export interface PlCounts {
  title: number;
  author: number;
  maps: number;
  rating: number;
  upvotes: number;
  length: number;
  nps: number;
  created: number;
  more: number;
}

const count = (...v: unknown[]) => v.filter((x) => x !== null && x !== "" && x !== false).length;

export function plCounts(s: PlState): PlCounts {
  return {
    title: count(s.q.trim()),
    author: count(s.owner.trim()),
    maps: count(s.mapsMin, s.mapsMax),
    rating: count(s.minRating),
    upvotes: count(s.minUpvotes),
    length: count(s.durationMin, s.durationMax),
    nps: count(s.npsMin, s.npsMax),
    created: count(s.from, s.to),
    more: count(s.curated, s.verified),
  };
}

export const plTotal = (c: PlCounts): number => Object.values(c).reduce((a, b) => a + b, 0);

/** State patch for an order select value: a server order or `local:<sort>`. */
export function plOrderPatch(value: string): Partial<PlState> {
  if (value.startsWith("local:") && isLocal(value.slice(6))) {
    return { localSort: value.slice(6) as PlLocalSort };
  }
  return isOrder(value) ? { order: value, localSort: null } : { localSort: null };
}

/** Author filter and local sort over the loaded playlists. */
export function viewPlaylists(items: BsPlaylist[], state: PlState): BsPlaylist[] {
  const owner = state.owner.trim().toLowerCase();
  const shown = owner ? items.filter((p) => p.owner.toLowerCase().includes(owner)) : items;
  if (!state.localSort) return shown;
  const key = {
    maps: (p: BsPlaylist) => p.map_count,
    upvotes: (p: BsPlaylist) => p.upvotes,
    length: (p: BsPlaylist) => p.duration,
  }[state.localSort];
  const dir = state.ascending ? 1 : -1;
  return [...shown].sort((a, b) => dir * (key(a) - key(b)));
}

/** "m:ss" under an hour, "h:mm" from an hour. */
export function formatTotalLength(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "–";
  const total = Math.round(seconds);
  const two = (n: number) => String(n).padStart(2, "0");
  if (total < 3600) return `${Math.floor(total / 60)}:${two(total % 60)}`;
  return `${Math.floor(total / 3600)}:${two(Math.floor((total % 3600) / 60))}`;
}

export function formatNpsRange(min: number, max: number): string {
  if (!(max > 0)) return "–";
  return `${min.toFixed(1)}–${max.toFixed(1)}`;
}
