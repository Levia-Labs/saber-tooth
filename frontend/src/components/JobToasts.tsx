// Restores job toasts after a refresh and takes over jobs whose page went away.
import { useEffect, useRef } from "react";
import { useJobLists } from "../api/joblist";
import { ownedJobs } from "../api/jobs";
import { planToasts, SUMMARY_KEY, type ToastPlan } from "../lib/jobtoasts";
import { dismissedJobs } from "../lib/jobdismiss";
import { useOpenJobs } from "../lib/jobopen";
import { useAnnounce, useWithdraw } from "./Announcer";

export function JobToasts() {
  const lists = useJobLists();
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  const prev = useRef<ToastPlan["next"]>(new Map());
  const summaryClosed = useRef(false);
  const shownSummary = useRef<string | null>(null);

  const open = useOpenJobs();

  useEffect(() => {
    const plan = planToasts(prev.current, lists, ownedJobs, open, dismissedJobs);
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
        // Opening the summary closes it until the count drops to 4 or fewer; so does its close button.
        onOpen: () => {
          summaryClosed.current = true;
          withdraw(SUMMARY_KEY);
          open();
        },
        onDismiss: () => {
          summaryClosed.current = true;
        },
      });
    }
    if (!plan.summary) {
      summaryClosed.current = false;
      if (shownSummary.current !== null) withdraw(SUMMARY_KEY);
      shownSummary.current = null;
    }
  }, [lists, announce, withdraw, open]);

  return null;
}
