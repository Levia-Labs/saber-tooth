import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { clearJobFilters, encodeJobsState, parseJobsState, type JobsState } from "./jobfilters";

export type JobsPatch = (patch: Partial<JobsState>, replace?: boolean) => void;

export interface JobsControls {
  state: JobsState;
  /** Merge a change into the URL; typing uses replace so history is not flooded. */
  update: JobsPatch;
  clearFilters: () => void;
}

/** Jobs table filter and sort state kept in the URL query string. */
export function useJobsState(): JobsControls {
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  const state = useMemo(() => parseJobsState(search), [search]);
  const update = useCallback<JobsPatch>(
    (patch, replace = false) =>
      setParams(encodeJobsState({ ...parseJobsState(search), ...patch }), { replace }),
    [search, setParams],
  );
  const clearFilters = useCallback(
    () => setParams(encodeJobsState(clearJobFilters(parseJobsState(search)))),
    [search, setParams],
  );
  return { state, update, clearFilters };
}
