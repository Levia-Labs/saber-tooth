import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef } from "react";
import { approveProposal, rejectProposal } from "../api/client";
import { keys } from "../api/queries";
import type { Note, Proposal } from "../api/types";
import { isNotesless } from "../lib/timeline";
import { TIPS } from "../lib/tips";
import { useAnnounce } from "./Announcer";
import { ActionButton } from "./Buttons";
import { TimelineCanvas } from "./TimelineCanvas";

interface Props {
  proposal: Proposal;
  mapId: string;
  /** Optional filter applied to notes before drawing (e.g. the first 16 bars). */
  notesFilter?: (notes: Note[]) => Note[];
}

/** One proposed fix with its before and after timeline and approve and reject buttons. */
export function ProposalCard({ proposal: p, mapId, notesFilter }: Props) {
  const client = useQueryClient();
  const announce = useAnnounce();
  const card = useRef<HTMLElement>(null);
  const refocus = useRef(false);

  const decide = useMutation({
    mutationFn: (verb: "approve" | "reject") =>
      verb === "approve" ? approveProposal(p.id) : rejectProposal(p.id),
    onSuccess: async () => {
      refocus.current = true;
      await client.invalidateQueries({ queryKey: keys.proposals(mapId) });
      await client.invalidateQueries({ queryKey: keys.map(mapId) });
    },
    onError: (err: Error) => announce(`Error: ${err.message}`),
  });

  // The pressed button becomes disabled; hand focus to the next enabled button or the card.
  useEffect(() => {
    if (!refocus.current) return;
    refocus.current = false;
    const next = card.current?.querySelector<HTMLButtonElement>("button:not(:disabled)");
    (next ?? card.current)?.focus();
  }, [p.status]);

  const before = useMemo(() => (notesFilter ? notesFilter(p.before) : p.before), [p, notesFilter]);
  const after = useMemo(() => (notesFilter ? notesFilter(p.after) : p.after), [p, notesFilter]);
  const textOnly = isNotesless(before, after, [...p.walls_before, ...p.walls_after]);

  return (
    <article
      ref={card}
      tabIndex={-1}
      className={`card sev-${p.severity} st-${p.status}`}
      data-proposal={p.id}
    >
      <header>
        <div className="card-title">
          <strong>{p.summary}</strong>
          <span className="badge">{p.severity}</span>
          <span className="badge">{p.status}</span>
        </div>
        <div className="row">
          <ActionButton
            icon="approve"
            label="Approve"
            tip={TIPS.approve}
            text
            variant="approve"
            disabled={p.status === "approved" || decide.isPending}
            onClick={() => decide.mutate("approve")}
          />
          <ActionButton
            icon="reject"
            label="Reject"
            tip={TIPS.reject}
            text
            variant="reject"
            disabled={p.status === "rejected" || decide.isPending}
            onClick={() => decide.mutate("reject")}
          />
        </div>
      </header>
      {textOnly ? (
        <p className="muted">{p.summary}</p>
      ) : (
        <TimelineCanvas
          label={`Before and after note grids for ${p.summary}`}
          before={before}
          after={after}
          wallsBefore={p.walls_before}
          wallsAfter={p.walls_after}
          wallsContext={p.walls_context}
        />
      )}
    </article>
  );
}
