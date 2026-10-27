import { Link } from "react-router";
import { dismissFix, useFixOutcomes, type FixOutcome } from "../api/fix";
import { fixSummary, readFixReport } from "../lib/fixreport";
import { Alert } from "./Alert";

function OutcomeAlert({ outcome }: { outcome: FixOutcome }) {
  const { job, error, name } = outcome;
  const onDismiss = () => dismissFix(outcome.key);
  if (error !== null || !job) {
    return (
      <Alert
        variant="danger"
        title={`Fix failed: ${name}`}
        message="The map could not be fixed. The original is unchanged."
        details={[error ?? "job failed"]}
        onDismiss={onDismiss}
      />
    );
  }
  const rep = readFixReport(job);
  const open = rep.fixedId ? (
    <Link className="btn plain" to={`/maps/${encodeURIComponent(rep.fixedId)}`}>
      Open fixed map
    </Link>
  ) : undefined;
  if (rep.errorsAfter > 0 || rep.unfixed.length > 0) {
    return (
      <Alert
        variant="danger"
        title={`Fix incomplete: ${name}`}
        message={`${fixSummary(rep)}. ${rep.errorsAfter} errors remain.`}
        details={rep.unfixed}
        actions={open}
        onDismiss={onDismiss}
      />
    );
  }
  if (!rep.folder) {
    return (
      <Alert
        variant="info"
        title={`Nothing to fix: ${name}`}
        message="No changes were needed."
        onDismiss={onDismiss}
      />
    );
  }
  return (
    <Alert
      variant="success"
      title={`Fixed: written to ${rep.folder}`}
      message={`${fixSummary(rep)}.`}
      actions={open}
      onDismiss={onDismiss}
    />
  );
}

/** Alerts under finished fix jobs; limit to one map with `mapId`. */
export function FixOutcomes({ mapId }: { mapId?: string }) {
  const outcomes = useFixOutcomes(mapId);
  return (
    <>
      {outcomes.map((o) => (
        <OutcomeAlert key={o.key} outcome={o} />
      ))}
    </>
  );
}
