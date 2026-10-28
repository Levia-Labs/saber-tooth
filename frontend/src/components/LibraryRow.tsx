import { Link } from "react-router";
import type { MapItem } from "../api/types";
import { formatEnvironment } from "../lib/environment";
import { formatBpm, formatDuration } from "../lib/format";
import { TIPS } from "../lib/tips";
import { mapName, reviewNeeds } from "../lib/status";
import { ActionLink } from "./Buttons";
import { Cover, LevelChips, StatusChip } from "./Chips";
import { FixButton } from "./FixButton";
import { FixedCopyLink } from "./FixedCopyLink";
import { PreviewButton } from "./PreviewButton";

export function LibraryRow({ item, index }: { item: MapItem; index: number }) {
  const name = mapName(item);
  const href = `/maps/${encodeURIComponent(item.id)}`;
  // Scan and Apply live on the map page; the eye carries whatever waits there.
  const needs = reviewNeeds(item);
  const reviewLabel = needs.text ? `Review ${name}, ${needs.text}` : `Review ${name}`;
  return (
    <div className="lib-row lib-grid" role="row" aria-rowindex={index + 2} data-map={item.id}>
      <div className="col-cover" role="cell">
        <Cover url={item.cover_url} />
      </div>
      <div className={`col-title${item.audio_url ? " with-preview" : ""}`} role="cell">
        <Link className="title-link" to={href} title={name}>
          {name}
        </Link>
        <PreviewButton src={item.audio_url} start={item.preview_start} title={name} />
      </div>
      <div className="col-sub" role="cell">
        <div className="sub">
          {item.parse_error ? (
            <span className="sub-unreadable">Unreadable Info file</span>
          ) : (
            <span>{item.mapper || "Unknown mapper"}</span>
          )}
          {item.environment && <span> &middot; {formatEnvironment(item.environment)}</span>}
          <span className="sub-tempo">
            {" "}
            &middot; {formatDuration(item.duration_s)} &middot; {formatBpm(item.bpm)}
          </span>
        </div>
        <LevelChips names={item.difficulties} className="levels-inline" />
        <FixedCopyLink item={item} />
      </div>
      <div className="col-author" role="cell" title={item.mapper}>
        {item.mapper}
      </div>
      <div className="col-levels" role="cell">
        <LevelChips names={item.difficulties} />
      </div>
      <div className="col-length num" role="cell">
        {formatDuration(item.duration_s)}
      </div>
      <div className="col-bpm num" role="cell">
        {formatBpm(item.bpm)}
      </div>
      <div className="col-env" role="cell" title={formatEnvironment(item.environment)}>
        {formatEnvironment(item.environment)}
      </div>
      <div className="col-status" role="cell">
        <StatusChip item={item} />
      </div>
      <div className="col-actions" role="cell">
        <div className="actions">
          <FixButton item={item} />
          <ActionLink
            icon="review"
            label={reviewLabel}
            tip={needs.text ? `${TIPS.review} Waiting: ${needs.text}.` : TIPS.review}
            to={href}
            className={needs.count > 0 ? "needs-action" : undefined}
          >
            {needs.count > 0 && (
              <span className="badge-count" aria-hidden="true">
                {needs.count}
              </span>
            )}
          </ActionLink>
        </div>
      </div>
    </div>
  );
}
