import type { Finding } from "../api/review";
import type { Proposal } from "../api/types";
import { Alert } from "./Alert";
import { FindingCard } from "./FindingCard";
import { ProposalCard } from "./ProposalCard";

function groupBy<T>(list: T[], key: (item: T) => string): Map<string, T[]> {
  const out = new Map<string, T[]>();
  for (const item of list) {
    const k = key(item);
    out.set(k, [...(out.get(k) ?? []), item]);
  }
  return out;
}

/** One row of the list: a proposal, or a finding that has none. */
type Entry = { proposal: Proposal } | { finding: Finding };

const rule = (e: Entry) => ("proposal" in e ? e.proposal.rule : e.finding.rule);
const difficulty = (e: Entry) => ("proposal" in e ? e.proposal.difficulty : e.finding.difficulty);

/** Every proposal, plus each finding of the latest scan that no proposal covers. */
function entries(proposals: Proposal[], findings: Finding[]): Entry[] {
  const open = findings
    .filter((f) => f.proposal_id === null || !proposals.some((p) => p.id === f.proposal_id))
    .map((finding): Entry => ({ finding }));
  const all = proposals.map((proposal): Entry => ({ proposal }));
  return [...open, ...all];
}

/** Findings and proposals grouped by difficulty, then by rule. The toolbar lives on the map page. */
export function ProposalGroups({
  proposals,
  findings = [],
  scanned = true,
  mapId,
  open,
  onToggle,
  clean = false,
}: {
  proposals: Proposal[];
  findings?: Finding[];
  /** False when the map has never been scanned. */
  scanned?: boolean;
  mapId: string;
  open: ReadonlySet<string>;
  onToggle: (id: string, on: boolean) => void;
  /** A clean fixed copy: no empty-state prompt. */
  clean?: boolean;
}) {
  const rows = entries(proposals, findings);
  return (
    <>
      <div className="fixes-scroll">
        {rows.length === 0 && !clean && !scanned && (
          <Alert
            variant="info"
            title="Not scanned yet"
            message="Scan the map to look for issues and propose fixes."
          />
        )}
        {rows.length === 0 && !clean && scanned && (
          <Alert variant="success" title="No issues found" message="The last scan found nothing." />
        )}
        {[...groupBy(rows, difficulty)].map(([diff, byDiff]) => (
          <section key={diff}>
            <h2 className="group-title">{diff}</h2>
            {[...groupBy(byDiff, rule)].map(([name, byRule]) => (
              <div key={name}>
                <p className="muted">
                  {name} ({byRule.length})
                </p>
                {byRule.map((e) =>
                  "proposal" in e ? (
                    <ProposalCard
                      key={`p${e.proposal.id}`}
                      proposal={e.proposal}
                      mapId={mapId}
                      open={open.has(String(e.proposal.id))}
                      onToggle={(on) => onToggle(String(e.proposal.id), on)}
                    />
                  ) : (
                    <FindingCard
                      key={`f${e.finding.rule}${e.finding.beat_start}${e.finding.message}`}
                      finding={e.finding}
                    />
                  ),
                )}
              </div>
            ))}
          </section>
        ))}
      </div>
    </>
  );
}
