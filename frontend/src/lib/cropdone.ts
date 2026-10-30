import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router";
import { cropSuggestionsKey } from "../api/cropauto";
import { keys } from "../api/queries";
import type { CropResult, Job } from "../api/types";
import { mapHref } from "./backlink";
import { useOrigin } from "./useBacklink";

/**
 * What a finished crop does to the page. Everything keyed to the old map content is reset (so no
 * stale Auto cards or window survive), the library is refetched, and the page moves to Status:
 * a new map opens on its own page, keeping the origin; a replaced map stays and drops `?tab=`.
 */
export function useCropDone(mapId: string): (job: Job, replace: boolean) => Promise<void> {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [, setParams] = useSearchParams();
  const { origin, back } = useOrigin();
  return async (job, replace) => {
    const result = job.result as Partial<CropResult> | null | undefined;
    if (replace) {
      await Promise.all([
        client.resetQueries({ queryKey: keys.timeline(mapId) }),
        client.resetQueries({ queryKey: cropSuggestionsKey(mapId) }),
        client.invalidateQueries({ queryKey: keys.proposals(mapId) }),
        client.invalidateQueries({ queryKey: keys.map(mapId) }),
      ]);
      setParams((prev) => {
        const out = new URLSearchParams(prev);
        out.delete("tab");
        return out;
      });
    } else if (result?.cropped_id) {
      void navigate(mapHref(result.cropped_id, { from: origin, back }));
    }
    await client.invalidateQueries({ queryKey: keys.maps }); // the library lists live under it
  };
}
