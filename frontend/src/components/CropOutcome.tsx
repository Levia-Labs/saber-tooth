import { useEffect } from "react";
import type { CropResult, Job } from "../api/types";
import { toAlert } from "../lib/alerts";
import { specToInput } from "../lib/announcements";
import { useAnnounce } from "./Announcer";

/** Reports a finished or failed crop as a toast; renders nothing. */
export function CropOutcome({
  mapId,
  job,
  error,
}: {
  mapId: string;
  job: Job | null;
  error: string | null;
}) {
  const announce = useAnnounce();
  useEffect(() => {
    if (error !== null) {
      const spec = toAlert(job, error);
      if (spec) announce(specToInput(`Crop:${mapId}`, spec));
      return;
    }
    const result = job?.result as Partial<CropResult> | null | undefined;
    if (!result?.cropped_id || result.replaced) return;
    announce({
      key: `Crop:${mapId}`,
      variant: "success",
      title: "Cropped map written",
      message: `Written to ${result.folder ?? "a new folder"}.`,
      link: { to: `/maps/${encodeURIComponent(result.cropped_id)}`, label: "Open cropped map" },
    });
  }, [announce, mapId, job, error]);
  return null;
}
