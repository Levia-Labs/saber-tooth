// Restores job toasts after a refresh and takes over jobs whose page went away.
import { useEffect, useRef } from "react";
import { useJobLists } from "../api/joblist";
import { ownedJobs } from "../api/jobs";
import {
  dismissedJobs,
  planToasts,
  useOpenJobs,
  type SummaryState,
  type Tracked,
} from "../lib/jobtoasts";
import { useAnnounce, useWithdraw } from "./Announcer";

export function JobToasts() {
  const lists = useJobLists();
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  const open = useOpenJobs();
  const prev = useRef<Tracked>(new Map());
  const summary = useRef<SummaryState>({ closed: false, shown: null });

  useEffect(() => {
    summary.current.withdraw = withdraw;
    const plan = planToasts(prev.current, lists, ownedJobs, open, dismissedJobs, summary.current);
    prev.current = plan.next;
    for (const key of plan.withdraw) withdraw(key);
    for (const toast of plan.show) announce(toast);
  }, [lists, announce, withdraw, open]);

  return null;
}
