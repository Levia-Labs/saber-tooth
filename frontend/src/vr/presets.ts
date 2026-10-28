// The VR library presets and sorts, and how they map onto the library query. Pure functions.
import type { LevelKey, MapItem, StatusKey } from "../api/types";
import { STATUS_ORDER } from "../lib/status";
import { DEFAULT_STATE, type LibraryState } from "../lib/urlstate";

export const VR_PRESETS = [
  { key: "needs-fix", label: "Needs fix", help: "Maps with errors or warnings." },
  {
    key: "missing-levels",
    label: "Missing levels",
    help: "Maps never scanned that lack one of the five levels.",
  },
  { key: "unscanned", label: "Not scanned", help: "Maps that have not been scanned yet." },
  { key: "fixed", label: "Fixed copies", help: "The [saber-tooth] copies that Fix wrote." },
  { key: "expert-plus", label: "Expert+", help: "Maps that have an Expert+ level." },
] as const;
export type VrPreset = (typeof VR_PRESETS)[number]["key"];

export const VR_SORTS = [
  { key: "title", label: "Title", sort: "title", order: "asc" },
  { key: "errors", label: "Most errors", sort: "errors", order: "desc" },
  { key: "recent", label: "Recently scanned", sort: "scanned_at", order: "desc" },
  { key: "length", label: "Longest", sort: "duration", order: "desc" },
] as const;
export type VrSort = (typeof VR_SORTS)[number]["key"];

export interface VrView {
  presets: VrPreset[];
  sort: VrSort;
}

/** Known presets in the fixed order, once each, and a known sort; anything else is ignored. */
export function parseVrView(search: string): VrView {
  const params = new URLSearchParams(search);
  const wanted = (params.get("p") ?? "").split(",");
  const sort = VR_SORTS.find((s) => s.key === params.get("sort"))?.key ?? "title";
  return { presets: VR_PRESETS.map((p) => p.key).filter((k) => wanted.includes(k)), sort };
}

export function encodeVrView(view: VrView): URLSearchParams {
  const params = new URLSearchParams();
  if (view.presets.length) params.set("p", view.presets.join(","));
  if (view.sort !== "title") params.set("sort", view.sort);
  return params;
}

export function togglePreset(view: VrView, key: VrPreset): VrView {
  const on = view.presets.includes(key);
  const presets = VR_PRESETS.map((p) => p.key).filter((k) =>
    k === key ? !on : view.presets.includes(k),
  );
  return { ...view, presets };
}

/** The library query for a view. Status presets combine as OR; Expert+ narrows them. */
export function vrState(view: VrView): LibraryState {
  const status = new Set<StatusKey>();
  if (view.presets.includes("needs-fix")) status.add("error").add("warn");
  if (view.presets.includes("missing-levels")) status.add("incomplete");
  if (view.presets.includes("unscanned")) status.add("unscanned");
  const by = VR_SORTS.find((s) => s.key === view.sort) ?? VR_SORTS[0];
  const level: LevelKey[] = view.presets.includes("expert-plus") ? ["ExpertPlus"] : [];
  return {
    ...DEFAULT_STATE,
    status: STATUS_ORDER.filter((s) => status.has(s)),
    level,
    sort: by.sort,
    order: by.order,
  };
}

/** The API has no filter for fixed copies; a fixed copy is a map that records its original. */
export const isFixedCopy = (item: Partial<Pick<MapItem, "original_id">>): boolean =>
  Boolean(item.original_id);
