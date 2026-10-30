import { useRef, type ReactNode } from "react";
import type { Playlist } from "../../api/playlists";
import { LP_COLUMNS } from "../../lib/lpcolumns";
import { useColumns } from "../../lib/useColumns";
import { lpFilterCount, type LpSort, type LpState, type LpSync } from "../../lib/lpfilters";
import { Link } from "react-router";
import { ActionButton, ActionLink } from "../Buttons";
import { Cover } from "../Chips";
import { ConfirmDialog } from "../ConfirmDialog";
import { FilterPopover } from "../FilterPopover";
import { JobsFilterBody } from "../JobsFilterBody";
import { TextFilterBody } from "../TextFilterBody";
import { Icon } from "../icons";
import { Tip } from "../Tip";

interface Props {
  rows: Playlist[];
  all: Playlist[];
  state: LpState;
  update: (patch: Partial<LpState>) => void;
  exportEnabled: boolean;
  /** Address of a playlist's page, opened from this list. */
  hrefOf: (p: Playlist) => string;
  onExport: (p: Playlist) => void;
  onDelete: (p: Playlist) => void;
  empty: ReactNode;
}

function Head({
  label,
  sort,
  state,
  update,
  filter,
}: {
  label: string;
  sort?: LpSort;
  state: LpState;
  update: Props["update"];
  filter?: ReactNode;
}) {
  const sorted = sort !== undefined && state.sort === sort;
  const aria = sorted ? (state.ascending ? "ascending" : "descending") : "none";
  return (
    <div className="th" role="columnheader" aria-sort={sort ? aria : undefined}>
      <div className="th-row">
        {sort ? (
          <Tip text={`Sort by ${label}`}>
            <button
              type="button"
              className="th-sort"
              aria-label={`Sort by ${label}`}
              onClick={() =>
                update({ sort, ascending: sorted ? !state.ascending : sort === "title" })
              }
            >
              <span className="th-label">{label}</span>
            </button>
          </Tip>
        ) : (
          <span className="th-label">{label}</span>
        )}
        {filter}
        {sort && (
          <span className="th-slot" aria-hidden="true">
            {sorted && <Icon name={state.ascending ? "sort-asc" : "sort-desc"} />}
          </span>
        )}
      </div>
    </div>
  );
}

function Header({ state, update, all }: Pick<Props, "state" | "update" | "all">) {
  const counts = lpFilterCount(state);
  const syncOn: LpSync[] = state.sync === "any" ? [] : [state.sync];
  const count = (f: (p: Playlist) => boolean) => all.filter(f).length;
  const h = { state, update };
  return (
    <div className="lib-head lp-grid" role="row" aria-rowindex={1}>
      <div className="th th-quiet" role="columnheader">
        <span className="th-label">Icon</span>
      </div>
      <Head
        {...h}
        label="Title"
        sort="title"
        filter={
          <FilterPopover label="Title" tip="Filter by title or author" count={counts.title}>
            <TextFilterBody
              label="Title contains"
              placeholder="Title"
              q={state.q}
              onChange={(q) => update({ q })}
              rowClear={{
                column: "Title",
                disabled: !counts.title,
                onClear: () => update({ q: "" }),
              }}
            />
          </FilterPopover>
        }
      />
      <Head
        {...h}
        label="Songs"
        sort="songs"
        filter={
          <FilterPopover label="Songs" tip="Filter by missing songs" count={counts.songs}>
            <JobsFilterBody<"missing">
              label="Songs"
              options={[
                {
                  value: "missing",
                  label: "Has missing songs",
                  count: count((p) => p.missing_count > 0),
                },
              ]}
              selected={state.missing ? ["missing"] : []}
              onChange={(next) => update({ missing: next.length > 0 })}
              rowClear={{
                column: "Songs",
                disabled: !counts.songs,
                onClear: () => update({ missing: false }),
              }}
            />
          </FilterPopover>
        }
      />
      <Head {...h} label="Folder" sort="folder" />
      <Head
        {...h}
        label="Sync"
        sort="sync"
        filter={
          <FilterPopover label="Sync" tip="Filter by sync" count={counts.sync}>
            <JobsFilterBody<"on" | "off">
              label="Sync"
              options={[
                { value: "on", label: "Syncing", count: count((p) => p.sync) },
                { value: "off", label: "Not syncing", count: count((p) => !p.sync) },
              ]}
              selected={syncOn as ("on" | "off")[]}
              onChange={(next) => update({ sync: next.find((v) => v !== state.sync) ?? "any" })}
              rowClear={{
                column: "Sync",
                disabled: !counts.sync,
                onClear: () => update({ sync: "any" }),
              }}
            />
          </FilterPopover>
        }
      />
      <Head {...h} label="Actions" />
    </div>
  );
}

function Row({
  p,
  index,
  exportEnabled,
  hrefOf,
  onExport,
  onDelete,
}: Omit<Props, "rows" | "all" | "state" | "update" | "empty"> & { p: Playlist; index: number }) {
  return (
    <div className="lp-row lp-grid" role="row" aria-rowindex={index + 2} data-playlist={p.id}>
      <div role="cell">
        <Cover url={p.cover_url} />
      </div>
      <div className="lp-title" role="cell">
        <Link className="lp-name" to={hrefOf(p)} title={p.title}>
          {p.title}
        </Link>
        {p.author && <span className="lp-sub">{p.author}</span>}
      </div>
      <div className="lp-songs" role="cell">
        {p.songs_count}
        {p.missing_count > 0 && (
          <span className="lp-missing" title="No installed map matches these songs">
            {p.missing_count} missing
          </span>
        )}
      </div>
      <div className="lp-folder" role="cell">
        {p.folder ? p.folder : <span className="lp-sub">Playlists</span>}
      </div>
      <div role="cell">
        {p.sync ? (
          <span className="lp-sync" title={p.sync_url}>
            <Icon name="ok" /> On
          </span>
        ) : (
          <span className="lp-sub">Off</span>
        )}
      </div>
      <div className="lp-actions" role="cell">
        <ActionLink icon="review" label={`Edit ${p.title}`} tip="Edit playlist" to={hrefOf(p)} />
        <ActionButton
          icon="download"
          label={`Export ${p.title}`}
          tip={
            exportEnabled
              ? "Write the .bplist into the playlists folder"
              : "Playlist export is not configured"
          }
          disabled={!exportEnabled}
          onClick={() => onExport(p)}
        />
        <ConfirmDialog
          title={`Delete ${p.title}?`}
          description="The playlist is removed here; a .bplist already exported stays where it is."
          confirmLabel="Delete playlist"
          danger
          onConfirm={() => onDelete(p)}
        >
          <ActionButton icon="trash" label={`Delete ${p.title}`} tip="Delete playlist" />
        </ConfirmDialog>
      </div>
    </div>
  );
}

/** The playlists table: sort and filter in the header, one row per playlist. */
export function LpTable({ rows, all, state, update, empty, ...actions }: Props) {
  const table = useRef<HTMLDivElement>(null);
  const columns = useColumns(table, LP_COLUMNS);
  return (
    <div className="lib-scroll lp-scroll" tabIndex={-1}>
      <div
        role="table"
        aria-label="Playlists"
        aria-rowcount={rows.length + 1}
        className="lib-table lp-table"
        ref={table}
        style={columns.style}
      >
        <Header state={state} update={update} all={all} />
        <div role="rowgroup">
          {rows.map((p, i) => (
            <Row key={p.id} p={p} index={i} {...actions} />
          ))}
        </div>
      </div>
      {rows.length === 0 && empty}
    </div>
  );
}
