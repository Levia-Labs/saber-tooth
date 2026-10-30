import { useQuery } from "@tanstack/react-query";
import type { CropSuggestions } from "../lib/cropauto";
import { request } from "./client";

export const cropSuggestionsKey = (id: string) => ["crop-suggestions", id] as const;

/** The server's ranked Auto crop windows; fast, so it only waits for the Auto choice to be shown. */
export function useCropSuggestions(id: string, enabled: boolean) {
  return useQuery({
    queryKey: cropSuggestionsKey(id),
    queryFn: ({ signal }) =>
      request<CropSuggestions>(
        "GET",
        `/api/maps/${encodeURIComponent(id)}/crop/suggestions`,
        undefined,
        signal,
      ),
    enabled,
    staleTime: 60_000,
  });
}
