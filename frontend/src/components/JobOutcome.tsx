import { useEffect, useRef } from "react";
import type { Job } from "../api/types";
import { toAlert } from "../lib/alerts";
import { specToInput } from "../lib/announcements";
import { useAnnounce } from "./Announcer";

interface Props {
  /** Toast key; the runner's progress toast uses the same label, so the outcome replaces it. */
  label: string;
  job: Job | null;
  error: string | null;
  onRetry?: () => void;
  onReview?: () => void;
}

/** Shows the result of a finished or failed job (scan, apply, learn) as a toast; renders nothing. */
export function JobOutcome({ label, job, error, onRetry, onReview }: Props) {
  const announce = useAnnounce();
  const handlers = useRef({ onRetry, onReview });
  useEffect(() => {
    handlers.current = { onRetry, onReview };
  });
  useEffect(() => {
    const spec = toAlert(job, error);
    if (spec) announce(specToInput(label, spec, handlers.current));
  }, [announce, label, job, error]);
  return null;
}
