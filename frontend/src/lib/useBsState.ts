import { clearBsFilters, encodeBsState, parseBsState, type BsState } from "./bsfilters";
import { useUrlState, type UrlControls } from "./useUrlState";

export type BsControls = UrlControls<BsState>;

const CODEC = { parse: parseBsState, encode: encodeBsState, clear: clearBsFilters };

/** BeatSaver filter state kept in the URL query string. */
export function useBsState(): BsControls {
  return useUrlState(CODEC);
}
