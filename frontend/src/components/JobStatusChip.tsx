import type { JobView } from "../api/types";
import { jobChip, jobIcon, jobStatusLabel, jobTag } from "../lib/jobview";
import { Icon } from "./icons";
import { Tip } from "./Tip";

type Props = { job: Pick<JobView, "status" | "cancel_requested" | "position" | "progress"> };

/**
 * A job's state as the library's status chip: icon box with a coloured edge and a tooltip. Queue
 * position (info) and fix rounds (warning) sit inside the same widget.
 */
export function JobStatusChip({ job }: Props) {
  const kind = jobChip(job);
  const tag = jobTag(job);
  const word = jobStatusLabel(job);
  const label = tag ? `${word}, ${tag.label}` : word;
  return (
    <Tip text={label}>
      <span className={`chip chip-${kind}`} data-status={job.status} role="img" aria-label={label}>
        <Icon
          name={jobIcon(job)}
          {...(job.status === "running" ? { className: "alert-spin" } : {})}
        />
        {tag && (
          <span className={`jobs-tag jobs-tag-${tag.tone}`} aria-hidden="true">
            {tag.text}
          </span>
        )}
      </span>
    </Tip>
  );
}
