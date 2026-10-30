import type { Finding } from "../api/review";
import { Icon } from "./icons";

function clock(s: number | null): string | null {
  if (s === null) return null;
  const m = Math.floor(s / 60);
  return `${m}:${(s - m * 60).toFixed(1).padStart(4, "0")}`;
}

/** A finding the fixer has no proposal for: shown so the status count always matches the list. */
export function FindingCard({ finding: f }: { finding: Finding }) {
  const time = clock(f.time_s);
  return (
    <article
      className={`card sev-${f.severity === "error" ? "error" : "warning"} finding`}
      data-finding={`${f.rule}@${f.beat_start}`}
    >
      <header className="card-sum">
        <span className="card-toggle">
          <Icon name={f.severity === "error" ? "error" : "warning"} />
          <span className="sum-rule">{f.rule}</span>
          <span className="sum-diff">{f.difficulty}</span>
          <span className="sum-range">
            {time ? `${time} · ` : ""}beat {f.beat_start}
          </span>
          <span className="badge sum-sev">{f.severity}</span>
        </span>
      </header>
      <div className="card-body">
        <p className="card-summary">
          <strong>{f.message}</strong>
        </p>
        <p className="muted">No automatic fix for this finding. Edit it by hand.</p>
      </div>
    </article>
  );
}
