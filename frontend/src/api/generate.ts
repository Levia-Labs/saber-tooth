// One-step generation: start the job, follow it with a keyed toast and a live view, open the finished map.
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import { useAnnounce } from "../components/Announcer";
import { capitalize } from "../lib/announcements";
import type { StageJob } from "../lib/genstages";
import { resultMapId } from "../lib/generate";
import { errorText, useOpenJobs } from "../lib/jobtoasts";
import { ApiError, type Started } from "./client";
import { pollJob } from "./jobs";
import { keys } from "./queries";

export interface Generator {
  busy: boolean;
  /** What the page shows: the job's latest state, from the moment Generate is pressed; null before. */
  view:
    | (StageJob & {
        source: "url" | "file";
        label: string;
        error: string | null;
        /** The song's title once the server knows it. */
        title?: string | undefined;
        /** Set when the song is already imported or being imported: where to look at it. */
        existing?: { to: string; label: string };
      })
    | null;
  /** Start a job for `label` (a link or file name); resolves once the job ended. */
  run: (label: string, source: "url" | "file", start: () => Promise<Started>) => Promise<void>;
}

/** The link a 409 "already imported / being imported" answer points at, else null. */
export function existingLink(err: unknown): { to: string; label: string } | null {
  if (!(err instanceof ApiError) || err.status !== 409) return null;
  const { job, map_id: map } = err.fields;
  if (typeof job === "string") return { to: "/jobs", label: "Open job" };
  if (typeof map === "string") return { to: `/maps/${map}`, label: "Open map" };
  return null;
}

/** Announces queue, progress, success with an "Open map" link, or the failure reason; one job at a time. */
export function useGenerate(): Generator {
  const announce = useAnnounce();
  const navigate = useNavigate();
  const client = useQueryClient();
  const openJobs = useOpenJobs();
  const [view, setView] = useState<Generator["view"]>(null);
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
    async (label: string, source: "url" | "file", start: () => Promise<Started>) => {
      if (running.current) return;
      running.current = true;
      counter.current += 1;
      const key = `generate-${counter.current}`;
      let song: string | undefined;
      const show = (job: StageJob & { title?: string }, error: string | null = null) => {
        // The server names a job "Generate from ..." until it knows the song.
        if (job.title && !job.title.startsWith("Generate from")) song = job.title;
        if (mounted.current) setView({ ...job, source, label, error, title: song });
      };
      show({ status: "queued" });
      let closed = false;
      try {
        const started = await start();
        const job = await pollJob(started.job, new AbortController().signal, (status, polled) => {
          if (polled) show(polled);
          if (closed || status === "unreachable" || status.startsWith("retrying")) return;
          // No toast while queued; the page shows the queue state and the toast starts when it runs.
          if (status.startsWith("queued")) return;
          announce({
            key,
            variant: "progress",
            title: `Generating ${song ?? label}`,
            message: capitalize(polled?.progress ?? status),
            autoClose: true,
            onDismiss: () => {
              closed = true;
            },
            onOpen: openJobs,
          });
        });
        const id = resultMapId(job.result);
        if (id === null) throw new Error("the job finished without a map");
        show(job);
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
        const message = errorText(err);
        const existing = existingLink(err);
        if (mounted.current) {
          setView((v) =>
            v ? { ...v, status: "failed", error: message, ...(existing && { existing }) } : v,
          );
        }
        if (existing) return; // the card shows it with a link; no toast
        announce({ key, variant: "danger", title: `Generation failed: ${label}`, message });
      } finally {
        running.current = false;
      }
    },
    [announce, client, navigate, openJobs],
  );

  const busy = view !== null && view.error === null && view.status !== "done";
  return { busy, view, run };
}
