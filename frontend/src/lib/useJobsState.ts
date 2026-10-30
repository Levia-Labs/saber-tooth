import { clearJobFilters, encodeJobsState, parseJobsState, type JobsState } from "./jobfilters";
import { useUrlState, type UrlControls } from "./useUrlState";

export type JobsPatch = (patch: Partial<JobsState>, replace?: boolean) => void;
export type JobsControls = UrlControls<JobsState>;

const CODEC = { parse: parseJobsState, encode: encodeJobsState, clear: clearJobFilters };

/** Jobs table filter and sort state kept in the URL query string. */
export function useJobsState(): JobsControls {
  return useUrlState(CODEC);
}
