import type { Proposal } from "../api/types";
import { ProposalCard } from "./ProposalCard";

function groupBy<T>(list: T[], key: (item: T) => string): Map<string, T[]> {
  const out = new Map<string, T[]>();
  for (const item of list) {
    const k = key(item);
    out.set(k, [...(out.get(k) ?? []), item]);
  }
  return out;
}

/** Proposals grouped by difficulty, then by rule. */
export function ProposalGroups({ proposals, mapId }: { proposals: Proposal[]; mapId: string }) {
  if (!proposals.length) return <p className="muted">No proposals. Scan the map first.</p>;
  return (
    <>
      {[...groupBy(proposals, (p) => p.difficulty)].map(([difficulty, byDiff]) => (
        <section key={difficulty}>
          <h2 className="group-title">{difficulty}</h2>
          {[...groupBy(byDiff, (p) => p.rule)].map(([rule, byRule]) => (
            <div key={rule}>
              <p className="muted">
                {rule} ({byRule.length})
              </p>
              {byRule.map((p) => (
                <ProposalCard key={p.id} proposal={p} mapId={mapId} />
              ))}
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
