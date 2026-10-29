// Restores job toasts after a refresh and takes over jobs whose page went away.
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import { useJobLists } from "../api/joblist";
import { ownedJobs } from "../api/jobs";
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
    const plan = planToasts(prev.current, lists, ownedJobs);
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
  }, [lists, announce, withdraw, navigate]);

  return null;
}
