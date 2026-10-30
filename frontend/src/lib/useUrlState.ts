import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router";
import { BACK_PARAM, FROM_PARAM } from "./backlink";

export interface UrlStateCodec<S> {
  parse: (search: string) => S;
  encode: (state: S) => URLSearchParams;
  /** The state with every filter reset (sort and paging are the codec's concern). */
  clear: (state: S) => S;
}

export interface UrlControls<S> {
  state: S;
  /** Merge a change into the URL; typing uses replace so history is not flooded. */
  update: (patch: Partial<S>, replace?: boolean) => void;
  /** Replace the whole state, e.g. when a preset is applied. */
  set: (next: S, replace?: boolean) => void;
  clearFilters: () => void;
}

/** Filter state kept in the URL query string, shared by every list page. */
export function useUrlState<S>({ parse, encode, clear }: UrlStateCodec<S>): UrlControls<S> {
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  const state = useMemo(() => parse(search), [parse, search]);
  const set = useCallback(
    (next: S, replace = false) =>
      setParams(
        (prev) => {
          const out = encode(next);
          // The origin of the page (where Back to list returns) is not a filter: keep it.
          for (const name of [FROM_PARAM, BACK_PARAM]) {
            const value = prev.get(name);
            if (value !== null) out.set(name, value);
          }
          return out;
        },
        { replace },
      ),
    [encode, setParams],
  );
  const update = useCallback(
    (patch: Partial<S>, replace = false) => set({ ...parse(search), ...patch }, replace),
    [parse, search, set],
  );
  const clearFilters = useCallback(() => set(clear(parse(search))), [clear, parse, search, set]);
  return { state, update, set, clearFilters };
}
