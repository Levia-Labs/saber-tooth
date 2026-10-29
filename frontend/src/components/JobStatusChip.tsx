import type { JobView } from "../api/types";
import { jobChip, jobIcon, jobStatusLabel } from "../lib/jobstatus";
import { Icon } from "./icons";
import { Tip } from "./Tip";

/** A job's state as the library's status chip: icon box with a coloured edge and a tooltip. */
export function JobStatusChip({ job }: { job: Pick<JobView, "status" | "cancel_requested"> }) {
  const kind = jobChip(job);
  const label = jobStatusLabel(job);
  return (
    <Tip text={label}>
      <span className={`chip chip-${kind}`} data-status={job.status} role="img" aria-label={label}>
        <Icon
          name={jobIcon(job)}
          {...(job.status === "running" ? { className: "alert-spin" } : {})}
        />
      </span>
    </Tip>
  );
}
