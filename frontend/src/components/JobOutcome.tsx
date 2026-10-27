import type { Job } from "../api/types";
import { toAlert } from "../lib/alerts";
import { SpecAlert } from "./Alert";

interface Props {
  job: Job | null;
  error: string | null;
  onRetry?: () => void;
  onReview?: () => void;
}

/** Alert under a finished or failed job: scan, apply, generate or learn. */
export function JobOutcome({ job, error, onRetry, onReview }: Props) {
  return <SpecAlert spec={toAlert(job, error)} onRetry={onRetry} onReview={onReview} />;
}
