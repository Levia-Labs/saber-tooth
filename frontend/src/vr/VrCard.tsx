import { Link } from "react-router";
import { useFix } from "../api/fix";
import type { MapItem } from "../api/types";
import { Cover, LevelChips, StatusChip } from "../components/Chips";
import { PreviewButton } from "../components/PreviewButton";
import { formatDuration } from "../lib/format";
import { mapName } from "../lib/status";

/** One map as a large card: cover, title, status, levels, length and the three actions. */
export function VrCard({ item }: { item: MapItem }) {
  const name = mapName(item);
  const fix = useFix(item, name);
  const busy = item.job !== null || item.status === "unreadable";
  const copy = item.fixed_copy_id;
  return (
    <article className="vr-card" data-map={item.id}>
      <Cover url={item.cover_url} big />
      <div className="vr-card-body">
        <h2 className="vr-card-title">{name}</h2>
        <p className="vr-help">{item.mapper || "Unknown mapper"}</p>
        <div className="vr-card-meta">
          <StatusChip item={item} />
          <LevelChips names={item.difficulties} />
          <span>{formatDuration(item.duration_s)}</span>
        </div>
        <div className="vr-actions">
          <PreviewButton src={item.audio_url} start={item.preview_start} title={name} />
          <button
            type="button"
            className="btn accent"
            aria-label={`Fix ${name}`}
            disabled={busy}
            onClick={() => void fix()}
          >
            Fix
          </button>
          <Link
            className="btn plain"
            aria-label={`${copy ? "Open fixed copy of" : "Open"} ${name}`}
            to={`/vr/maps/${encodeURIComponent(copy || item.id)}`}
          >
            {copy ? "Open fixed copy" : "Open"}
          </Link>
        </div>
      </div>
    </article>
  );
}
