// Restores job toasts after a refresh and takes over jobs whose page went away.
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { cancelJob } from "../api/client";
import { useJobLists } from "../api/joblist";
import { ownedJobs } from "../api/jobs";
import { keys } from "../api/queries";
import type { JobView } from "../api/types";
import { planToasts, SUMMARY_KEY, type ToastPlan } from "../lib/jobtoasts";
import { useAnnounce, useWithdraw } from "./Announcer";

export function JobToasts() {
  const lists = useJobLists();
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  const navigate = useNavigate();
  const prev = useRef<ToastPlan["next"]>(new Map());
  const summaryClosed = useRef(false);
  const dismissed = useRef(new Set<string>());
  const shownSummary = useRef<string | null>(null);

  const client = useQueryClient();
  const cancel = useCallback(
    (job: JobView) => {
      cancelJob(job.id)
        .catch((err: unknown) =>
          announce({
            variant: "danger",
            title: `Cancel ${job.title}`,
            message: err instanceof Error ? err.message : String(err),
          }),
        )
        .finally(() => void client.invalidateQueries({ queryKey: keys.jobs }));
    },
    [announce, client],
  );

  useEffect(() => {
    const plan = planToasts(prev.current, lists, ownedJobs, cancel, dismissed.current);
    prev.current = plan.next;
    for (const key of plan.withdraw) withdraw(key);
    for (const t of plan.show) {
      if (t.key !== SUMMARY_KEY) {
        announce(t);
        continue;
      }
      if (summaryClosed.current || shownSummary.current === t.title) continue;
      shownSummary.current = t.title;
      announce({
        ...t,
        // The summary is a progress toast without a close button; its action is the only way to
        // close it, so pressing it marks it closed until the count drops to 4 or fewer.
        actions: [
          {
            label: "Show jobs",
            icon: "playlist",
            onClick: () => {
              summaryClosed.current = true;
              navigate("/jobs");
            },
          },
        ],
      });
    }
    if (!plan.summary) {
      summaryClosed.current = false;
      if (shownSummary.current !== null) withdraw(SUMMARY_KEY);
      shownSummary.current = null;
    }
  }, [lists, announce, withdraw, navigate, cancel]);

  return null;
}
