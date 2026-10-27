import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { approveProposal, rejectProposal } from "../api/client";
import { keys } from "../api/queries";
import type { Note, Proposal } from "../api/types";
import { beatRange, countOperations, isNotesless } from "../lib/timeline";
import { plural } from "../lib/format";
import { TIPS } from "../lib/tips";
import { useAnnounce } from "./Announcer";
import { ActionButton } from "./Buttons";
import { Icon } from "./icons";
import { TimelineCanvas } from "./TimelineCanvas";

interface Props {
  proposal: Proposal;
  mapId: string;
  /** Optional filter applied to notes before drawing (e.g. the first 16 bars). */
  notesFilter?: (notes: Note[]) => Note[];
  /** Expanded state owned by the parent (Expand all / Collapse all); omit for local state. */
  open?: boolean;
  onToggle?: (open: boolean) => void;
  defaultOpen?: boolean;
}

/** One proposed fix with its before and after timeline and approve and reject buttons. */
export function ProposalCard({
  proposal: p,
  mapId,
  notesFilter,
  open: controlled,
  onToggle,
  defaultOpen = false,
}: Props) {
  const [local, setLocal] = useState(defaultOpen);
  const open = controlled ?? local;
  const bodyId = useId();
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
    const next = card.current?.querySelector<HTMLButtonElement>(".row button:not(:disabled)");
    (next ?? card.current)?.focus();
  }, [p.status]);

  const before = useMemo(() => (notesFilter ? notesFilter(p.before) : p.before), [p, notesFilter]);
  const after = useMemo(() => (notesFilter ? notesFilter(p.after) : p.after), [p, notesFilter]);
  const range = beatRange(before, after, p.walls_before, p.walls_after);
  const ops = countOperations(before, after) + countOperations(p.walls_before, p.walls_after);
  const textOnly = isNotesless(before, after, [...p.walls_before, ...p.walls_after]);

  return (
    <article
      ref={card}
      tabIndex={-1}
      className={`card sev-${p.severity} st-${p.status}`}
      data-proposal={p.id}
    >
      <header className="card-sum">
        <button
          type="button"
          className="card-toggle"
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={() => {
            setLocal(!open);
            onToggle?.(!open);
          }}
        >
          <Icon name="chevron" className={open ? "chev open" : "chev"} />
          <span className="sum-rule">{p.rule}</span>
          <span className="sum-diff">{p.difficulty}</span>
          <span className="sum-range">{range}</span>
          <span className="sum-ops">{plural(ops, "operation")}</span>
          <span className="badge sum-sev">{p.severity}</span>
          {p.status !== "pending" && <span className="badge">{p.status}</span>}
        </button>
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
      <div id={bodyId} className="card-body" hidden={!open}>
        <p className="card-summary">
          <strong>{p.summary}</strong>
        </p>
        {textOnly ? null : (
          <TimelineCanvas
            label={`Before and after note grids for ${p.summary}`}
            before={before}
            after={after}
            wallsBefore={p.walls_before}
            wallsAfter={p.walls_after}
            wallsContext={p.walls_context}
          />
        )}
      </div>
    </article>
  );
}
