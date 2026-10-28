import type { BsMap } from "../api/beatsaver";
import { SpecAlert } from "../components/Alert";
import type { Downloads } from "../components/beatsaver/downloads";
import { Cover, LevelChips } from "../components/Chips";
import { PreviewButton } from "../components/PreviewButton";
import { errorToAlert } from "../lib/alerts";
import { formatCount, formatDuration } from "../lib/format";
import { useNearEnd } from "./useNearEnd";

const LABEL = {
  none: "Download",
  downloading: "Downloading",
  installed: "Installed",
  failed: "Retry download",
} as const;

/** One BeatSaver map as a large card with a large Download. */
export function VrBsCard({ map, downloads }: { map: BsMap; downloads: Downloads }) {
  const status = downloads.status(map);
  const label = LABEL[status.kind];
  const name = status.kind === "none" ? `${label} ${map.name}` : `${label}: ${map.name}`;
  const locked =
    downloads.runner.busy || status.kind === "installed" || status.kind === "downloading";
  return (
    <article className="vr-card" data-map={map.id}>
      <Cover url={map.cover_url} big />
      <div className="vr-card-body">
        <h2 className="vr-card-title">{map.name}</h2>
        <p className="vr-help">{map.mapper}</p>
        <div className="vr-card-meta">
          <LevelChips names={map.difficulties.map((d) => d.difficulty)} />
          <span>{formatDuration(map.duration)}</span>
          <span>{`${Math.round(map.rating * 100)}% liked, ${formatCount(map.upvotes)} upvotes`}</span>
        </div>
        <div className="vr-actions">
          <PreviewButton src={map.preview_url} title={map.name} />
          <button
            type="button"
            className="btn accent vr-big"
            aria-label={name}
            disabled={locked}
            onClick={() => void downloads.start([map.id])}
          >
            {label}
          </button>
        </div>
        {status.kind === "failed" && (
          <p className="vr-help" role="alert">
            {status.reason}
          </p>
        )}
      </div>
    </article>
  );
}

export interface ListProps {
  maps: BsMap[];
  pending: boolean;
  error: unknown;
  onRetry: () => void;
  hasNext: boolean;
  fetching: boolean;
  onMore: () => void;
  downloads: Downloads;
  emptyText: string;
}

/** The scrolling card grid with its loading, error and empty states and the end sentinel. */
export function VrBsList(p: ListProps) {
  const end = useNearEnd(p.onMore, p.hasNext && !p.fetching);
  const failed = p.error !== null && p.error !== undefined;
  return (
    <div className="vr-scroll">
      {p.pending && (
        <p className="vr-help" role="status">
          Loading maps
        </p>
      )}
      {failed && p.maps.length === 0 && (
        <SpecAlert spec={errorToAlert(p.error, "Could not load BeatSaver")} onRetry={p.onRetry} />
      )}
      {!p.pending && !failed && p.maps.length === 0 && !p.hasNext && (
        <p className="vr-empty">{p.emptyText}</p>
      )}
      <div className="vr-grid">
        {p.maps.map((map) => (
          <VrBsCard key={map.id} map={map} downloads={p.downloads} />
        ))}
      </div>
      <div ref={end} aria-hidden="true" />
      {p.fetching && (
        <p className="vr-help" role="status">
          Loading more maps
        </p>
      )}
    </div>
  );
}
