import { useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { formatEnvironment } from "../../lib/environment";
import { bpmLabel, formatBpm, formatBpmValue, formatDuration } from "../../lib/format";
import { LIBRARY_COLUMNS } from "../../lib/columns";
import { applyState, facetsOf, type SongRow } from "../../lib/lpsongs";
import { mapName } from "../../lib/status";
import { useColumns } from "../../lib/useColumns";
import { DEFAULT_STATE, filterCounts, totalFilters, type LibraryState } from "../../lib/urlstate";
import { ActionButton } from "../Buttons";
import { Cover, LevelChips, StatusChip } from "../Chips";
import { EmptyState } from "../EmptyState";
import { Icon } from "../icons";
import { LibraryHeader } from "../LibraryHeader";
import { PreviewButton } from "../PreviewButton";
import { Tip } from "../Tip";

interface Props {
  rows: SongRow[];
  onRemove: (row: SongRow) => void;
}

function MissingChip() {
  const label = "Missing: no installed map matches this song";
  return (
    <Tip text={label}>
      <span className="chip chip-unreadable" data-status="missing" role="img" aria-label={label}>
        <Icon name="unreadable" />
      </span>
    </Tip>
  );
}

function SongRowView({
  row,
  index,
  onRemove,
}: { row: SongRow; index: number } & Pick<Props, "onRemove">) {
  const { item, missing } = row;
  const name = missing ? item.title : mapName(item);
  const href = `/maps/${encodeURIComponent(item.id)}`;
  const env = formatEnvironment(item.environment);
  return (
    <div
      className={`lib-row lib-grid${missing ? " lp-gone" : ""}`}
      role="row"
      aria-rowindex={index + 2}
      data-map={item.id}
    >
      <div className="col-cover" role="cell">
        <Cover url={item.cover_url} />
      </div>
      <div className={`col-title${item.audio_url ? " with-preview" : ""}`} role="cell">
        {missing ? (
          <span className="title-link" title={name}>
            {name}
          </span>
        ) : (
          <Link className="title-link" to={href} title={name}>
            {name}
          </Link>
        )}
        <PreviewButton src={item.audio_url} start={item.preview_start} title={name} />
      </div>
      <div className="col-sub" role="cell">
        <div className="sub">
          <span>{item.mapper || "Unknown mapper"}</span>
          {item.environment && <span> &middot; {env}</span>}
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
      <div
        className="col-bpm num"
        role="cell"
        title={bpmLabel(item.bpm)}
        aria-label={bpmLabel(item.bpm)}
      >
        {formatBpmValue(item.bpm)}
      </div>
      <div className="col-env" role="cell" title={env}>
        {env}
      </div>
      <div className="col-status" role="cell">
        {missing ? <MissingChip /> : <StatusChip item={item} />}
      </div>
      <div className="col-actions" role="cell">
        <div className="actions">
          <ActionButton
            icon="trash"
            label={`Remove ${name} from playlist`}
            tip="Remove from playlist"
            onClick={() => onRemove(row)}
          />
        </div>
      </div>
    </div>
  );
}

/** The playlist's songs in the library's table: same columns, header sort and filters, column fit. */
export function LpSongTable({ rows, onRemove }: Props) {
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table, LIBRARY_COLUMNS);
  const [state, setState] = useState<LibraryState>(DEFAULT_STATE);
  const facets = useMemo(() => facetsOf(rows), [rows]);
  const shown = useMemo(() => applyState(rows, state), [rows, state]);
  const filtered = totalFilters(filterCounts(state)) > 0;
  return (
    <div className="lib-scroll lp-songs-scroll" tabIndex={-1}>
      <div
        role="table"
        aria-label="Songs in the playlist"
        aria-rowcount={shown.length + 1}
        className="lib-table"
        ref={table}
        style={columns.style}
      >
        <LibraryHeader
          state={state}
          facets={facets}
          update={(patch) => setState((s) => ({ ...s, ...patch }))}
          columns={columns.api}
        />
        <div role="rowgroup">
          {shown.map((r, i) => (
            <SongRowView key={r.key} row={r} index={i} onRemove={onRemove} />
          ))}
        </div>
      </div>
      {shown.length === 0 && (
        <EmptyState
          icon={filtered ? "search" : "playlist"}
          text={filtered ? "No songs match the filters." : "No songs yet."}
          {...(filtered ? {} : { hint: "Add songs from the library or a job's output." })}
          action={
            filtered ? (
              <button type="button" className="btn plain" onClick={() => setState(DEFAULT_STATE)}>
                Clear filters
              </button>
            ) : undefined
          }
        />
      )}
    </div>
  );
}
