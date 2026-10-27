import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { clearBsFilters, encodeBsState, parseBsState, type BsState } from "./bsfilters";

export interface BsControls {
  state: BsState;
  /** Merge a change into the URL; typing uses replace so history is not flooded. */
  update: (patch: Partial<BsState>, replace?: boolean) => void;
  /** Replace the whole state, e.g. when a preset is applied. */
  set: (next: BsState) => void;
  clearFilters: () => void;
}

/** BeatSaver filter state kept in the URL query string. */
export function useBsState(): BsControls {
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  const state = useMemo(() => parseBsState(search), [search]);
  const set = useCallback(
    (next: BsState, replace = false) => setParams(encodeBsState(next), { replace }),
    [setParams],
  );
  const update = useCallback(
    (patch: Partial<BsState>, replace = false) =>
      set({ ...parseBsState(search), ...patch }, replace),
    [search, set],
  );
  const clearFilters = useCallback(() => set(clearBsFilters(parseBsState(search))), [search, set]);
  return { state, update, set, clearFilters };
}
