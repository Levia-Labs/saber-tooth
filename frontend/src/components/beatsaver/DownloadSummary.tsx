import { useEffect } from "react";
import { batchSummary } from "../../lib/announcements";
import { useAnnounce } from "../Announcer";
import { tally, type Downloads } from "./downloads";

/** Announces the finished batch as the keyed "Download maps" toast, replacing its progress toast. */
export function DownloadSummary({ downloads }: { downloads: Downloads }) {
  const announce = useAnnounce();
  const { runner, results } = downloads;
  const busy = runner.busy;
  useEffect(() => {
    if (busy || Object.keys(results).length === 0) return;
    const reasons = Object.values(results)
      .filter((o) => o.status === "failed")
      .map((o) => `${o.id}: ${o.reason ?? "failed"}`);
    announce(batchSummary("Download maps", tally(results), reasons));
  }, [busy, results, announce]);
  return null;
}
