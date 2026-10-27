// Small hooks: URL-backed library state, debounce, media query and document title.
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { encodeState, parseState, type LibraryState } from "./urlstate";

let lastLibrarySearch = "";

/** The library query string last shown, so the map page can link back to it. */
export function libraryHref(): string {
  return lastLibrarySearch ? `/?${lastLibrarySearch}` : "/";
}

export interface LibraryControls {
  state: LibraryState;
  /** Merge a change into the URL; typing uses replace so history is not flooded. */
  update: (patch: Partial<LibraryState>, replace?: boolean) => void;
  clearFilters: () => void;
}

export function useLibraryState(): LibraryControls {
  const [params, setParams] = useSearchParams();
  const search = params.toString();
  const state = useMemo(() => parseState(search), [search]);
  useEffect(() => {
    lastLibrarySearch = search;
  }, [search]);
  const update = useCallback(
    (patch: Partial<LibraryState>, replace = false) => {
      setParams(encodeState({ ...parseState(search), ...patch }), { replace });
    },
    [search, setParams],
  );
  const clearFilters = useCallback(() => update({ q: "", status: [], env: [] }), [update]);
  return { state, update, clearFilters };
}

/** A value that follows `value` after it has been stable for `ms`. */
export function useDebounced<T>(value: T, ms: number): T {
  const [out, setOut] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setOut(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return out;
}

export function useMediaQuery(query: string): boolean {
  const get = () => typeof window.matchMedia === "function" && window.matchMedia(query).matches;
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia(query);
    const on = () => setMatches(mq.matches);
    on();
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [query]);
  return matches;
}

export function useDocumentTitle(title: string): void {
  useEffect(() => {
    document.title = title ? `${title} - saber-tooth` : "saber-tooth";
  }, [title]);
}
