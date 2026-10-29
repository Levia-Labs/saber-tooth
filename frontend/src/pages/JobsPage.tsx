import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { cancelJob } from "../api/client";
import { useJobLists } from "../api/joblist";
import { keys } from "../api/queries";
import type { JobView } from "../api/types";
import { useAnnounce } from "../components/Announcer";
import { ActionButton } from "../components/Buttons";
import { JobsTable } from "../components/JobsTable";
import { SectionTabs } from "../components/SectionTabs";
import { useDocumentTitle } from "../lib/hooks";
import { allJobs, filterJobs, jobsFilterCount, sortJobs } from "../lib/jobfilters";
import { useJobsState } from "../lib/useJobsState";

const errorText = (err: unknown) => (err instanceof Error ? err.message : String(err));

export function JobsPage() {
  useDocumentTitle("Jobs");
  const lists = useJobLists();
  const client = useQueryClient();
  const announce = useAnnounce();
  const { state, update, clearFilters } = useJobsState();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const all = useMemo(() => allJobs(lists), [lists]);
  const rows = useMemo(() => sortJobs(filterJobs(all, state), state, now), [all, state, now]);
  const cancel = async (job: JobView) => {
    try {
      await cancelJob(job.id);
    } catch (err) {
      announce({ variant: "danger", title: `Cancel ${job.title}`, message: errorText(err) });
    }
    await client.invalidateQueries({ queryKey: keys.jobs });
  };
  const filtered = Object.values(jobsFilterCount(state)).some((n) => n > 0);
  const empty =
    all.length > 0 && filtered ? (
      <p className="jobs-empty">
        No jobs match the filters.{" "}
        <ActionButton
          icon="filter-x"
          label="Clear filters"
          tip="Show every job again"
          text
          onClick={clearFilters}
        />
      </p>
    ) : (
      <p className="jobs-empty">Nothing running or queued.</p>
    );
  return (
    <section className="library jobs" aria-labelledby="jobs-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <SectionTabs active="jobs" heading="Jobs" headingId="jobs-heading" />
        </div>
      </div>
      <JobsTable
        rows={rows}
        all={all}
        state={state}
        update={update}
        now={now}
        onCancel={(j) => void cancel(j)}
        empty={empty}
      />
    </section>
  );
}
