import "../styles/cropauto.css";
import { clock } from "../lib/crop";
import { percent, type CropProposal } from "../lib/cropauto";
import { EmptyState } from "./EmptyState";

interface Props {
  proposals: CropProposal[] | null;
  reason: string | null;
  selected: number;
  onSelect: (index: number) => void;
  onCustom: () => void;
}

/** The Auto crop proposals as selectable cards; a spinner while loading, an empty state if none fit. */
export function CropAuto({ proposals, reason, selected, onSelect, onCustom }: Props) {
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
        <button
          key={p.rank}
          type="button"
          role="radio"
          className="crop-card"
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
      ))}
    </div>
  );
}
