import { useState } from "react";
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
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  if (!proposals.length) return <p className="muted">No proposals. Scan the map first.</p>;
  const setOne = (id: string, on: boolean) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  return (
    <>
      <div className="card-controls">
        <button
          type="button"
          className="btn plain"
          onClick={() => setOpen(new Set(proposals.map((p) => String(p.id))))}
        >
          Expand all
        </button>
        <button type="button" className="btn plain" onClick={() => setOpen(new Set())}>
          Collapse all
        </button>
      </div>
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
                  onToggle={(on) => setOne(String(p.id), on)}
                />
              ))}
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
