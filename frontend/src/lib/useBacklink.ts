import { useCallback } from "react";
import { useSearchParams } from "react-router";
import {
  BACK_PARAM,
  FROM_PARAM,
  formatOrigin,
  mapHref,
  parseOrigin,
  type Origin,
} from "./backlink";

/** The origin and `back` query of the current page URL. */
export function useOrigin(): { origin: Origin; back: string | undefined; params: URLSearchParams } {
  const [params] = useSearchParams();
  return {
    origin: parseOrigin(params.get(FROM_PARAM)),
    back: params.get(BACK_PARAM) ?? undefined,
    params,
  };
}

/**
 * Map-page links for a list page: `from` is the page's origin and, for the URL-backed jobs list,
 * `back` is its current query so filters and sort return intact.
 */
export function useMapLinks(from: Origin): (id: string, tab?: string) => string {
  const [params] = useSearchParams();
  const search = from.kind === "jobs" || from.kind === "bs-playlist" ? params.toString() : "";
  const key = formatOrigin(from);
  return useCallback(
    (id, tab) => mapHref(id, { from: key, tab, back: search || undefined }),
    [key, search],
  );
}
