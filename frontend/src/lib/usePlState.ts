import { clearPlFilters, encodePlState, parsePlState, type PlState } from "./plfilters";
import { useUrlState, type UrlControls } from "./useUrlState";

export type PlControls = UrlControls<PlState>;

const CODEC = { parse: parsePlState, encode: encodePlState, clear: clearPlFilters };

/** Playlist filter state kept in the URL query string. */
export function usePlState(): PlControls {
  return useUrlState(CODEC);
}
