import { Link } from "react-router";
import type { JobView } from "../api/types";
import { JOB_COL } from "../lib/jobcolumns";
import { jobLengthMs } from "../lib/jobfilters";
import { roundsText } from "../lib/jobrounds";
import { KIND_ICON, KIND_LABEL } from "../lib/jobkinds";
import { duration, staleMinutes } from "../lib/jobtime";
import { ActionButton } from "./Buttons";
import { Cover } from "./Chips";
import { Icon } from "./icons";
import { JobStatusChip } from "./JobStatusChip";

interface Props {
  job: JobView;
  index: number;
  now: number;
  onCancel: (job: JobView) => void;
}

function ActionsCell({ job, onCancel }: Pick<Props, "job" | "onCancel">) {
  const active = job.status === "queued" || job.status === "running";
  const requested = job.status === "running" && job.cancel_requested;
  return (
    <div className="jc-actions" role="cell">
      {active && (
        <ActionButton
          icon={requested ? "spinner" : "trash"}
          label={requested ? "Cancelling job" : "Cancel job"}
          tip={requested ? "Waiting for the job to stop" : "Cancel job"}
          aria-label={requested ? "Cancelling job" : "Cancel job"}
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
    <div className={`jc-${JOB_COL.length} jc-length`} role="cell">
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
  const detail = job.status === "failed" && job.error ? job.error : null;
  const rounds = roundsText(job.progress);
  const cell = (col: string) => `jc-${col}`;
  return (
    <div className="jobs-row jobs-grid" role="row" aria-rowindex={index + 2} data-job={job.id}>
      <div className={cell(JOB_COL.icon)} role="cell">
        {linked ? (
          <Cover url={`/api/maps/${encodeURIComponent(job.map_id ?? "")}/cover`} />
        ) : (
          <span className="cover cover-empty jobs-kind-icon">
            <Icon name={KIND_ICON[job.kind]} />
          </span>
        )}
      </div>
      <div className={`${cell(JOB_COL.title)} jc-title`} role="cell">
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
      <LengthCell job={job} now={now} />
      <div className={`${cell(JOB_COL.operation)} jobs-kind`} role="cell">
        {KIND_LABEL[job.kind]}
      </div>
      <div className={cell(JOB_COL.status)} role="cell">
        <JobStatusChip job={job} />
      </div>
      <div className={`${cell(JOB_COL.queue)} jobs-num`} role="cell">
        {job.status === "queued" && job.position ? job.position : ""}
      </div>
      <div className={`${cell(JOB_COL.rounds)} jobs-num jobs-rounds`} role="cell">
        {rounds ?? ""}
      </div>
      <ActionsCell job={job} onCancel={onCancel} />
    </div>
  );
}
