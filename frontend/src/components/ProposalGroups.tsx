import { useState, type ReactNode } from "react";
import type { Proposal } from "../api/types";
import { Alert } from "./Alert";
import { ActionButton } from "./Buttons";
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
export function ProposalGroups({
  proposals,
  mapId,
  actions,
  clean = false,
}: {
  proposals: Proposal[];
  mapId: string;
  actions?: ReactNode;
  /** A clean fixed copy: no expand/collapse and no "No fixes yet" prompt. */
  clean?: boolean;
}) {
  const [open, setOpen] = useState<ReadonlySet<string>>(new Set());
  const setOne = (id: string, on: boolean) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  const none = proposals.length === 0;
  return (
    <>
      <div className="map-toolbar" role="toolbar" aria-label="Fix actions">
        {actions}
        <span className="spacer" />
        {!clean && (
          <>
            <ActionButton
              icon="expand"
              label="Expand all"
              tip="Open every fix."
              text
              disabled={none}
              onClick={() => setOpen(new Set(proposals.map((p) => String(p.id))))}
            />
            <ActionButton
              icon="collapse"
              label="Collapse all"
              tip="Close every fix."
              text
              disabled={none}
              onClick={() => setOpen(new Set())}
            />
          </>
        )}
      </div>
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
                    onToggle={(on) => setOne(String(p.id), on)}
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
