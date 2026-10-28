import type { Proposal } from "../api/types";
import { Alert } from "./Alert";
import { ProposalCard } from "./ProposalCard";

function groupBy<T>(list: T[], key: (item: T) => string): Map<string, T[]> {
  const out = new Map<string, T[]>();
  for (const item of list) {
    const k = key(item);
    out.set(k, [...(out.get(k) ?? []), item]);
  }
  return out;
}

/** Proposals grouped by difficulty, then by rule. The toolbar lives on the map page. */
export function ProposalGroups({
  proposals,
  mapId,
  open,
  onToggle,
  clean = false,
}: {
  proposals: Proposal[];
  mapId: string;
  open: ReadonlySet<string>;
  onToggle: (id: string, on: boolean) => void;
  /** A clean fixed copy: no "No fixes yet" prompt. */
  clean?: boolean;
}) {
  const none = proposals.length === 0;
  return (
    <>
      <div className="fixes-scroll">
        {none && !clean && (
          <Alert
            variant="info"
            title="No fixes yet"
            message="Scan the map to look for fixes to propose."
          />
        )}
        {[...groupBy(proposals, (p) => p.difficulty)].map(([difficulty, byDiff]) => (
          <section key={difficulty}>
            <h2 className="group-title">{difficulty}</h2>
            {[...groupBy(byDiff, (p) => p.rule)].map(([rule, byRule]) => (
              <div key={rule}>
                <p className="muted">
                  {rule} ({byRule.length})
                </p>
                {byRule.map((p) => (
                  <ProposalCard
                    key={p.id}
                    proposal={p}
                    mapId={mapId}
                    open={open.has(String(p.id))}
                    onToggle={(on) => onToggle(String(p.id), on)}
                  />
                ))}
              </div>
            ))}
          </section>
        ))}
      </div>
    </>
  );
}
