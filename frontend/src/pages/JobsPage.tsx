import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import { cancelJob } from "../api/client";
import { useJobLists } from "../api/joblist";
import { keys } from "../api/queries";
import type { JobKind, JobView } from "../api/types";
import { useAnnounce } from "../components/Announcer";
import { Icon } from "../components/icons";
import { SectionTabs } from "../components/SectionTabs";
import { useDocumentTitle } from "../lib/hooks";
import { duration, staleMinutes } from "../lib/jobtime";

const KIND_LABEL: Record<JobKind, string> = {
  scan: "Scan",
  fix: "Fix",
  apply: "Apply",
  crop: "Crop",
  generate: "Generate",
  learn: "Learn lightshows",
  "bs-download": "Download maps",
};

const errorText = (err: unknown) => (err instanceof Error ? err.message : String(err));

function Title({ job }: { job: JobView }) {
  return job.map_exists && job.map_id ? (
    <Link className="jobs-title" to={`/maps/${job.map_id}`}>
      {job.title}
    </Link>
  ) : (
    <span className="jobs-title">{job.title}</span>
  );
}

function Running({ job, now }: { job: JobView; now: number }) {
  const stale = staleMinutes(job, now);
  return (
    <li className="jobs-row">
      <div className="jobs-main">
        <Title job={job} />
        <span className="jobs-kind">{KIND_LABEL[job.kind]}</span>
      </div>
      <span className="jobs-detail">{job.progress}</span>
      <span className="jobs-time">
        {duration(job.started_at ?? job.created_at, now)}
        {stale !== null && <span className="jobs-stale">no progress for {stale} min</span>}
      </span>
    </li>
  );
}

function Queued({ job, now, onCancel }: { job: JobView; now: number; onCancel: () => void }) {
  return (
    <li className="jobs-row">
      <div className="jobs-main">
        <span className="jobs-pos">#{job.position}</span>
        <Title job={job} />
        <span className="jobs-kind">{KIND_LABEL[job.kind]}</span>
      </div>
      <span className="jobs-time">waiting {duration(job.created_at, now)}</span>
      <button type="button" className="btn" aria-label={`Cancel ${job.title}`} onClick={onCancel}>
        Cancel
      </button>
    </li>
  );
}

function Recent({ job }: { job: JobView }) {
  const end = Date.parse(job.updated_at);
  const icon = job.status === "done" ? "ok" : job.status === "failed" ? "error" : null;
  return (
    <li className="jobs-row">
      <div className="jobs-main">
        {icon ? (
          <Icon name={icon} className={`jobs-${job.status}`} />
        ) : (
          <span className="jobs-dot" />
        )}
        <Title job={job} />
        <span className="jobs-kind">{KIND_LABEL[job.kind]}</span>
      </div>
      <span className="jobs-detail">{job.error}</span>
      <span className="jobs-time">
        {duration(job.started_at ?? job.created_at, end)}
        {Number.isFinite(end) && ` · ${new Date(end).toLocaleTimeString()}`}
      </span>
    </li>
  );
}

export function JobsPage() {
  useDocumentTitle("Jobs");
  const lists = useJobLists();
  const client = useQueryClient();
  const announce = useAnnounce();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const cancel = async (job: JobView) => {
    try {
      await cancelJob(job.id);
    } catch (err) {
      announce({ variant: "danger", title: `Cancel ${job.title}`, message: errorText(err) });
    }
    await client.invalidateQueries({ queryKey: keys.jobs });
  };
  const idle = lists.running.length === 0 && lists.queued.length === 0;
  return (
    <section className="library jobs" aria-labelledby="jobs-heading">
      <div className="lib-bar">
        <div className="lib-title">
          <SectionTabs active="jobs" heading="Jobs" headingId="jobs-heading" />
        </div>
      </div>
      {idle && <p className="jobs-empty">Nothing running or queued.</p>}
      {lists.running.length > 0 && (
        <section aria-labelledby="jobs-running">
          <h2 id="jobs-running">Running</h2>
          <ul className="jobs-list">
            {lists.running.map((j) => (
              <Running key={j.id} job={j} now={now} />
            ))}
          </ul>
        </section>
      )}
      {lists.queued.length > 0 && (
        <section aria-labelledby="jobs-queued">
          <h2 id="jobs-queued">Queued</h2>
          <ul className="jobs-list">
            {lists.queued.map((j) => (
              <Queued key={j.id} job={j} now={now} onCancel={() => void cancel(j)} />
            ))}
          </ul>
        </section>
      )}
      {lists.recent.length > 0 && (
        <section aria-labelledby="jobs-recent">
          <h2 id="jobs-recent">Recent</h2>
          <ul className="jobs-list">
            {lists.recent.map((j) => (
              <Recent key={j.id} job={j} />
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
