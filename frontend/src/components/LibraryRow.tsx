import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { applyMap, scanMap } from "../api/client";
import { markRunning } from "../api/queries";
import type { MapItem } from "../api/types";
import { formatEnvironment } from "../lib/environment";
import { formatBpm, formatDuration } from "../lib/format";
import { applyTip, TIPS } from "../lib/tips";
import { mapName } from "../lib/status";
import { ActionButton, ActionLink } from "./Buttons";
import { useAnnounce } from "./Announcer";
import { Cover, LevelChips, StatusChip } from "./Chips";
import { FixButton } from "./FixButton";
import { PreviewButton } from "./PreviewButton";

export function LibraryRow({ item, index }: { item: MapItem; index: number }) {
  const client = useQueryClient();
  const announce = useAnnounce();
  const name = mapName(item);
  const href = `/maps/${encodeURIComponent(item.id)}`;
  const busy = item.job !== null || item.status === "unreadable";
  const start = (kind: "scan" | "apply") =>
    jobStart(kind, item, (msg) => announce(`${kind} ${name}: ${msg}`), client);
  const scan = useMutation(start("scan"));
  const apply = useMutation(start("apply"));
  const pending = item.pending;
  const reviewLabel =
    pending > 0 ? `Review ${name}, ${pending} fixes waiting for review` : `Review ${name}`;
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
          <ActionLink icon="review" label={reviewLabel} tip={TIPS.review} to={href}>
            {pending > 0 && (
              <span className="badge-count" aria-hidden="true">
                {pending}
              </span>
            )}
          </ActionLink>
          <ActionButton
            icon="scan"
            label={`Scan ${name}`}
            tip={TIPS.scan}
            disabled={busy || scan.isPending}
            onClick={() => scan.mutate()}
          />
          {item.approved > 0 && (
            <ActionButton
              icon="apply"
              label={`Apply approved fixes for ${name}`}
              tip={applyTip(name)}
              disabled={busy || apply.isPending}
              onClick={() => apply.mutate()}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function jobStart(
  kind: "scan" | "apply",
  item: MapItem,
  onError: (msg: string) => void,
  client: ReturnType<typeof useQueryClient>,
) {
  return {
    mutationFn: () => (kind === "scan" ? scanMap(item.id) : applyMap(item.id)),
    onSuccess: (started: { job: string }) => markRunning(client, item, kind, started.job),
    onError: (err: Error) => onError(err.message),
  };
}
