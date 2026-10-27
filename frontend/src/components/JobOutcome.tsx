import type { Job } from "../api/types";

interface Props {
  job: Job | null;
  error: string | null;
}

/** Result box under a finished apply or learn job. */
export function JobOutcome({ job, error }: Props) {
  if (!job && !error) return null;
  const result = job?.result ?? {};
  const conflict = result["conflict"];
  const folder = result["folder"];
  return (
    <div className="result" role="status">
      {error && <p className="err">{conflict ? `Conflict: ${String(conflict)}` : error}</p>}
      {!error && typeof folder === "string" && <p className="ok">Written to: {folder}</p>}
      {!error && typeof folder !== "string" && <p className="ok">Job finished.</p>}
    </div>
  );
}
