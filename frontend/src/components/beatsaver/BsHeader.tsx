import * as Checkbox from "@radix-ui/react-checkbox";
import type { ReactNode } from "react";
import { bsCounts, type BsOrder, type BsState, type LocalSort } from "../../lib/bsfilters";
import { BS_TIPS } from "../../lib/bstips";
import { LABELS, type ColumnKey } from "../../lib/columns";
import type { ColumnsApi } from "../../lib/useColumns";
import { FilterPopover } from "../FilterPopover";
import { TextFilterBody } from "../FilterBodies";
import { HeaderCell } from "../HeaderCell";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import { LevelsBody, TagsBody, type Patch } from "./BsFilterBodies";
import { BpmBody, LengthBody, RatingBody, UpvotesBody } from "./BsNumberBodies";

interface Props {
  state: BsState;
  update: Patch;
  columns: ColumnsApi;
  allSelected: boolean;
  onSelectAll: () => void;
}

interface CellProps {
  col: ColumnKey;
  columns: ColumnsApi;
  state: BsState;
  update: Patch;
  sort?: { order?: BsOrder; local?: LocalSort; tip: string };
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
      label={LABELS[col]}
      columns={columns}
      filter={filter}
      {...(sort && { onSort: click, tip: sort.tip })}
      order={sorted ? (state.ascending ? "asc" : "desc") : undefined}
    />
  );
}
/** Sticky header row: sort and filters on Rating, Upvotes, Length and BPM; filters on Title, Levels and Tags. */
export function BsHeader({ state, update, columns, allSelected, onSelectAll }: Props) {
  const counts = bsCounts(state);
  const cell = { state, update, columns };
  return (
    <div className="lib-head lib-grid" role="row" aria-rowindex={1}>
      <div className="th col-select" role="columnheader">
        <Tip text={BS_TIPS.selectAll}>
          <Checkbox.Root
            className="checkbox"
            checked={allSelected}
            aria-label="Select all loaded maps"
            onCheckedChange={onSelectAll}
          >
            <Checkbox.Indicator>
              <Icon name="approve" />
            </Checkbox.Indicator>
          </Checkbox.Root>
        </Tip>
      </div>
      <Cell col="cover" {...cell} />
      <Cell
        col="title"
        {...cell}
        filter={
          <FilterPopover label="Title" tip={BS_TIPS.title} count={counts.title}>
            <TextFilterBody
              label="Search BeatSaver"
              q={state.q}
              onChange={(q, replace) => update({ q }, replace)}
            />
          </FilterPopover>
        }
      />
      <Cell col="author" {...cell} />
      <Cell
        col="levels"
        {...cell}
        filter={
          <FilterPopover label="Levels" tip={BS_TIPS.levels} count={counts.levels}>
            <LevelsBody state={state} update={update} />
          </FilterPopover>
        }
      />
      <Cell
        col="rating"
        {...cell}
        sort={{ order: "Rating", tip: BS_TIPS.sortRating }}
        filter={
          <FilterPopover label="Rating" tip={BS_TIPS.rating} count={counts.rating}>
            <RatingBody state={state} update={update} />
          </FilterPopover>
        }
      />
      <Cell
        col="upvotes"
        {...cell}
        sort={{ local: "upvotes", tip: BS_TIPS.sortUpvotes }}
        filter={
          <FilterPopover label="Upvotes" tip={BS_TIPS.upvotes} count={counts.upvotes}>
            <UpvotesBody state={state} update={update} />
          </FilterPopover>
        }
      />
      <Cell
        col="length"
        {...cell}
        sort={{ order: "Duration", tip: BS_TIPS.sortLength }}
        filter={
          <FilterPopover label="Length" tip={BS_TIPS.length} count={counts.length}>
            <LengthBody state={state} update={update} />
          </FilterPopover>
        }
      />
      <Cell
        col="bpm"
        {...cell}
        sort={{ local: "bpm", tip: BS_TIPS.sortBpm }}
        filter={
          <FilterPopover label="BPM" tip={BS_TIPS.bpm} count={counts.bpm}>
            <BpmBody state={state} update={update} />
          </FilterPopover>
        }
      />
      <Cell
        col="tags"
        {...cell}
        filter={
          <FilterPopover label="Tags" tip={BS_TIPS.tags} count={counts.tags}>
            <TagsBody state={state} update={update} />
          </FilterPopover>
        }
      />
      <Cell col="status" {...cell} />
      <Cell col="actions" {...cell} />
    </div>
  );
}
