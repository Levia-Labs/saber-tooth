import { Link } from "react-router";
import type { JobState, JobView } from "../api/types";
import { jobLengthMs } from "../lib/jobfilters";
import { KIND_ICON, KIND_LABEL } from "../lib/jobkinds";
import { duration, staleMinutes } from "../lib/jobtime";
import { ActionButton } from "./Buttons";
import { Cover } from "./Chips";
import { Icon } from "./icons";

const STATE_WORD: Record<JobState, string> = {
  running: "Running",
  queued: "Queued",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

interface Props {
  job: JobView;
  index: number;
  now: number;
  onCancel: (job: JobView) => void;
}

function StatusCell({ job }: { job: JobView }) {
  const word =
    job.status === "queued" && job.position
      ? `Queued #${job.position}`
      : job.status === "running" && job.cancel_requested
        ? "Cancelling"
        : STATE_WORD[job.status];
  return (
    <div className="jc-status" role="cell">
      <span className="jobs-kind">{KIND_LABEL[job.kind]}</span>
      <span className={`jobs-badge jobs-badge-${job.status}`}>{word}</span>
    </div>
  );
}

function ActionsCell({ job, onCancel }: Pick<Props, "job" | "onCancel">) {
  const active = job.status === "queued" || job.status === "running";
  const requested = job.status === "running" && job.cancel_requested;
  return (
    <div className="jc-actions" role="cell">
      {active && (
        <ActionButton
          icon={requested ? "spinner" : "stop"}
          label={requested ? "Cancelling" : "Cancel"}
          tip={requested ? "Waiting for the job to stop" : "Cancel this job"}
          text
          aria-label={`${requested ? "Cancelling" : "Cancel"} ${job.title}`}
          disabled={requested}
          onClick={() => onCancel(job)}
        />
      )}
    </div>
  );
}

function LengthCell({ job, now }: Pick<Props, "job" | "now">) {
  const ms = jobLengthMs(job, now);
  const stale = staleMinutes(job, now);
  return (
    <div className="jc-length" role="cell">
      {ms !== null && (
        <>
          {duration(
            job.started_at ?? job.created_at,
            job.status === "running" ? now : Date.parse(job.updated_at),
          )}
          {stale !== null && <span className="jobs-stale">no progress for {stale} min</span>}
        </>
      )}
    </div>
  );
}

export function JobsRow({ job, index, now, onCancel }: Props) {
  const linked = job.map_exists && job.map_id;
  const detail = job.status === "failed" && job.error ? job.error : job.progress;
  return (
    <div className="jobs-row jobs-grid" role="row" aria-rowindex={index + 2} data-job={job.id}>
      <StatusCell job={job} />
      <ActionsCell job={job} onCancel={onCancel} />
      <div className="jc-title" role="cell">
        {linked ? (
          <Link className="jobs-title" to={`/maps/${job.map_id}`} title={job.title}>
            {job.title}
          </Link>
        ) : (
          <span className="jobs-title" title={job.title}>
            {job.title}
          </span>
        )}
        {detail && <span className="jobs-detail">{detail}</span>}
      </div>
      <div className="jc-cover" role="cell">
        {linked ? (
          <Cover url={`/api/maps/${encodeURIComponent(job.map_id ?? "")}/cover`} />
        ) : (
          <span className="cover cover-empty jobs-kind-icon">
            <Icon name={KIND_ICON[job.kind]} />
          </span>
        )}
      </div>
      <LengthCell job={job} now={now} />
    </div>
  );
}
