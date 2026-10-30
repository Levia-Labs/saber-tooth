import type { ReactNode } from "react";
import { LABELS, type ColumnKey } from "../../lib/columns";
import { plCounts, type PlLocalSort, type PlOrder, type PlState } from "../../lib/plfilters";
import { PL_TIPS } from "../../lib/pltips";
import type { ColumnsApi } from "../../lib/useColumns";
import { TextFilterBody } from "../FilterBodies";
import { FilterPopover } from "../FilterPopover";
import { HeaderCell } from "../HeaderCell";
import {
  PlCreatedBody,
  PlLengthBody,
  PlMapsBody,
  PlNpsBody,
  PlRatingBody,
  PlUpvotesBody,
  type PlPatch,
} from "./PlaylistFilterBodies";

interface Props {
  state: PlState;
  update: PlPatch;
  columns: ColumnsApi;
}

interface CellProps extends Props {
  col: ColumnKey;
  sort?: { order?: PlOrder; local?: PlLocalSort; tip: string };
  filter?: ReactNode;
}

function Cell({ col, columns, state, update, sort, filter }: CellProps) {
  const sorted =
    sort !== undefined &&
    (sort.local ? state.localSort === sort.local : !state.localSort && state.order === sort.order);
  const click = () =>
    update({
      ...(sort?.order && { order: sort.order }),
      localSort: sort?.local ?? null,
      ascending: sorted ? !state.ascending : false,
    });
  return (
    <HeaderCell
      col={col}
      label={col === "title" ? "Name" : LABELS[col]}
      columns={columns}
      filter={filter}
      {...(sort && { onSort: click, tip: sort.tip })}
      order={sorted ? (state.ascending ? "asc" : "desc") : undefined}
    />
  );
}

/** Sticky header row: sort and filters per column, X close and inline clear in every popover. */
export function PlaylistHeader({ state, update, columns }: Props) {
  const counts = plCounts(state);
  const cell = { state, update, columns };
  const clear = (column: string, n: number, patch: Partial<PlState>) => ({
    column,
    disabled: n === 0,
    onClear: () => update(patch, true),
  });
  return (
    <div className="lib-head lib-grid" role="row" aria-rowindex={1}>
      <Cell col="cover" {...cell} />
      <Cell
        col="title"
        {...cell}
        filter={
          <FilterPopover label="Name" tip={PL_TIPS.title} count={counts.title}>
            <TextFilterBody
              label="Search playlists"
              placeholder="Name"
              q={state.q}
              onChange={(q, replace) => update({ q }, replace)}
              rowClear={clear("Name", counts.title, { q: "" })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="author"
        {...cell}
        filter={
          <FilterPopover label="Author" tip={PL_TIPS.author} count={counts.author}>
            <TextFilterBody
              label="Author contains"
              placeholder="Author"
              q={state.owner}
              onChange={(owner, replace) => update({ owner }, replace)}
              rowClear={clear("Author", counts.author, { owner: "" })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="maps"
        {...cell}
        sort={{ local: "maps", tip: PL_TIPS.sortMaps }}
        filter={
          <FilterPopover label="Maps" tip={PL_TIPS.maps} count={counts.maps}>
            <PlMapsBody
              state={state}
              update={update}
              rowClear={clear("Maps", counts.maps, { mapsMin: null, mapsMax: null })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="rating"
        {...cell}
        sort={{ order: "Rating", tip: PL_TIPS.sortRating }}
        filter={
          <FilterPopover label="Rating" tip={PL_TIPS.rating} count={counts.rating}>
            <PlRatingBody
              state={state}
              update={update}
              rowClear={clear("Rating", counts.rating, { minRating: null })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="upvotes"
        {...cell}
        sort={{ local: "upvotes", tip: PL_TIPS.sortUpvotes }}
        filter={
          <FilterPopover label="Upvotes" tip={PL_TIPS.upvotes} count={counts.upvotes}>
            <PlUpvotesBody
              state={state}
              update={update}
              rowClear={clear("Upvotes", counts.upvotes, { minUpvotes: null })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="length"
        {...cell}
        sort={{ local: "length", tip: PL_TIPS.sortLength }}
        filter={
          <FilterPopover label="Length" tip={PL_TIPS.length} count={counts.length}>
            <PlLengthBody
              state={state}
              update={update}
              rowClear={clear("Length", counts.length, { durationMin: null, durationMax: null })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="nps"
        {...cell}
        filter={
          <FilterPopover label="NPS" tip={PL_TIPS.nps} count={counts.nps}>
            <PlNpsBody
              state={state}
              update={update}
              rowClear={clear("NPS", counts.nps, { npsMin: null, npsMax: null })}
            />
          </FilterPopover>
        }
      />
      <Cell
        col="created"
        {...cell}
        sort={{ order: "Latest", tip: PL_TIPS.sortCreated }}
        filter={
          <FilterPopover label="Created" tip={PL_TIPS.created} count={counts.created}>
            <PlCreatedBody
              state={state}
              update={update}
              rowClear={clear("Created", counts.created, { from: "", to: "" })}
            />
          </FilterPopover>
        }
      />
      <Cell col="actions" {...cell} />
    </div>
  );
}
