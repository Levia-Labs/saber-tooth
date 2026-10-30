import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { BACK_PARAM, FROM_PARAM } from "./backlink";
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
    (next: BsState, replace = false) =>
      setParams(
        (prev) => {
          const out = encodeBsState(next);
          // The origin of the page (where Back to list returns) is not a filter: keep it.
          for (const name of [FROM_PARAM, BACK_PARAM]) {
            const value = prev.get(name);
            if (value !== null) out.set(name, value);
          }
          return out;
        },
        { replace },
      ),
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
