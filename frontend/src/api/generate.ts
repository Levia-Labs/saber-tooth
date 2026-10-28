// One-step generation: start the job, follow it with a keyed toast, open the finished map.
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useAnnounce } from "../components/Announcer";
import { capitalize } from "../lib/announcements";
import { resultMapId } from "../lib/generate";
import type { Started } from "./client";
import { pollJob } from "./jobs";
import { keys } from "./queries";

export interface Generator {
  busy: boolean;
  /** Start a job for `label` (a link or file name); resolves once the job ended. */
  run: (label: string, start: () => Promise<Started>) => Promise<void>;
}

/** Announces progress, success with an "Open map" link, or the failure reason; one job at a time. */
export function useGenerate(): Generator {
  const announce = useAnnounce();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const running = useRef(false);
  const counter = useRef(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const run = useCallback(
    async (label: string, start: () => Promise<Started>) => {
      if (running.current) return;
      running.current = true;
      setBusy(true);
      counter.current += 1;
      const key = `generate-${counter.current}`;
      const title = `Generating ${label}`;
      announce({ key, variant: "progress", title, message: "Queued" });
      try {
        const started = await start();
        const job = await pollJob(started.job, new AbortController().signal, (status) =>
          announce({ key, variant: "progress", title, message: capitalize(status) }),
        );
        const id = resultMapId(job.result);
        if (id === null) throw new Error("the job finished without a map");
        const folder = job.result?.["folder"];
        announce({
          key,
          variant: "success",
          title: "Map ready",
          message: typeof folder === "string" ? folder : label,
          link: { to: `/maps/${id}`, label: "Open map" },
        });
        await client.invalidateQueries({ queryKey: keys.maps });
        if (mounted.current) void navigate(`/maps/${id}`);
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        announce({ key, variant: "danger", title: `Generation failed: ${label}`, message });
      } finally {
        running.current = false;
        if (mounted.current) setBusy(false);
      }
    },
    [announce, client, navigate],
  );

  return { busy, run };
}
