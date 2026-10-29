// Restores job toasts after a refresh and takes over jobs whose page went away.
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { useJobLists } from "../api/joblist";
import { watchedJobs } from "../api/jobs";
import { planToasts, SUMMARY_KEY, type ToastPlan } from "../lib/jobtoasts";
import { useAnnounce, useWithdraw } from "./Announcer";

export function JobToasts() {
  const lists = useJobLists();
  const announce = useAnnounce();
  const withdraw = useWithdraw();
  const navigate = useNavigate();
  const prev = useRef<ToastPlan["next"]>(new Map());
  const summaryClosed = useRef(false);
  const shownSummary = useRef<string | null>(null);

  useEffect(() => {
    const plan = planToasts(prev.current, lists, watchedJobs);
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
        actions: [{ label: "Show jobs", onClick: () => navigate("/jobs") }],
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
  }, [lists, announce, withdraw, navigate]);

  return null;
}
