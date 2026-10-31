import { Link } from "react-router";
import type { Generator } from "../../api/generate";
import { stageStates } from "../../lib/genstages";
import { JobStatusChip } from "../JobStatusChip";
import { Spinner } from "../Spinner";
import { CardHead } from "../settings/CardHead";
import { StageList } from "./StageList";

type View = NonNullable<Generator["view"]>;

/** The running generate job: its status chip, what it is doing and the stage list. */
export function AnalyseCard({ view }: { view: View }) {
  const working = view.error === null && view.status !== "done";
  return (
    <section className="about-card gen-card" aria-labelledby="gen-job" aria-live="polite">
      <CardHead icon="queue" title="Generating" id="gen-job" />
      <div className="gen-job-head">
        <JobStatusChip
          job={{
            status: view.status,
            cancel_requested: false,
            position: view.position ?? null,
            progress: view.progress ?? null,
          }}
        />
        <span className="gen-label">{view.title ?? view.label}</span>
        {working && <Spinner label="Generating" />}
      </div>
      {view.error !== null && (
        <div className="gen-banner" role="alert">
          {view.error}
        </div>
      )}
      {view.existing ? (
        <Link className="gen-jobs-link" to={view.existing.to}>
          {view.existing.label}
        </Link>
      ) : (
        <StageList stages={stageStates(view, view.source)} />
      )}
      {view.status === "queued" && (
        <Link className="gen-jobs-link" to="/jobs">
          Open Jobs
        </Link>
      )}
    </section>
  );
}
