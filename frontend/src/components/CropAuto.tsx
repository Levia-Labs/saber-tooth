import { useState } from "react";
import "../styles/cropauto.css";
import { clock } from "../lib/crop";
import { percent, points, type CropProposal } from "../lib/cropauto";
import { EmptyState } from "./EmptyState";

interface Props {
  proposals: CropProposal[] | null;
  reason: string | null;
  selected: number;
  onSelect: (index: number) => void;
  onCustom: () => void;
}

/** The scoring components of one proposal, points earned out of the most each can give. */
function Breakdown({ id, proposal }: { id: string; proposal: CropProposal }) {
  return (
    <ul
      className="crop-card-breakdown"
      id={id}
      aria-label={`Score breakdown of proposal ${proposal.rank}`}
    >
      {proposal.breakdown.map((part) => (
        <li key={part.key}>
          <span>{part.label}</span>
          <span className="crop-card-part-bar" aria-hidden="true">
            <span
              style={{
                width: `${part.max_points > 0 ? (part.points / part.max_points) * 100 : 0}%`,
              }}
            />
          </span>
          <span className="crop-card-points">
            {points(part.points)} / {points(part.max_points)}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** The Auto crop proposals as selectable cards, each with an expandable score breakdown; a spinner
 * while loading, an empty state if none fit. */
export function CropAuto({ proposals, reason, selected, onSelect, onCustom }: Props) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  const toggle = (rank: number) =>
    setOpen((was) => {
      const next = new Set(was);
      if (!next.delete(rank)) next.add(rank);
      return next;
    });
  if (proposals === null) {
    return <EmptyState icon="spinner" text="" pending="Finding the best crops" />;
  }
  if (proposals.length === 0) {
    return (
      <EmptyState
        icon="crop"
        text="No automatic crop fits this song"
        hint={reason ?? "The song is too short for a 1 or 2 minute crop. Use a custom crop."}
        action={
          <button type="button" className="pill" onClick={onCustom}>
            Custom crop
          </button>
        }
      />
    );
  }
  return (
    <div className="crop-auto" role="radiogroup" aria-label="Auto crop proposals">
      {proposals.map((p, i) => (
        <div key={p.rank} className="crop-card" data-selected={i === selected}>
          <button
            type="button"
            role="radio"
            className="crop-card-pick"
            aria-checked={i === selected}
            onClick={() => onSelect(i)}
          >
            <span className="crop-card-head">
              <span className="crop-card-rank">#{p.rank}</span>
              <span className="crop-card-range">
                {clock(p.start_s)} to {clock(p.end_s)}
              </span>
              <span className="crop-card-length">{p.target}</span>
            </span>
            <span className="crop-card-reason">{p.reason}</span>
            <span className="crop-card-score">
              <span className="crop-card-bar" aria-hidden="true">
                <span style={{ width: `${percent(p.score)}%` }} />
              </span>
              <span>Score {percent(p.score)}</span>
            </span>
          </button>
          <button
            type="button"
            className="crop-card-toggle"
            aria-expanded={open.has(p.rank)}
            aria-controls={`crop-breakdown-${p.rank}`}
            onClick={() => toggle(p.rank)}
          >
            {open.has(p.rank) ? "Hide breakdown" : "Show breakdown"}
          </button>
          {open.has(p.rank) && <Breakdown id={`crop-breakdown-${p.rank}`} proposal={p} />}
        </div>
      ))}
    </div>
  );
}
