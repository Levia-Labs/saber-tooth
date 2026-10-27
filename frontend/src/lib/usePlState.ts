import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { clearPlFilters, encodePlState, parsePlState, type PlState } from "./plfilters";

export interface PlControls {
  state: PlState;
  /** Merge a change into the URL; typing uses replace so history is not flooded. */
  update: (patch: Partial<PlState>, replace?: boolean) => void;
  clearFilters: () => void;
}

/** Playlist filter state kept in the URL query string. */
export function usePlState(): PlControls {
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  const state = useMemo(() => parsePlState(search), [search]);
  const update = useCallback(
    (patch: Partial<PlState>, replace = false) =>
      setParams(encodePlState({ ...parsePlState(search), ...patch }), { replace }),
    [search, setParams],
  );
  const clearFilters = useCallback(
    () => setParams(encodePlState(clearPlFilters(parsePlState(search)))),
    [search, setParams],
  );
  return { state, update, clearFilters };
}
