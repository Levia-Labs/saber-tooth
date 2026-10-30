import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import {
  BS_ORDERS,
  bsCounts,
  bsTotal,
  LOCAL_LABELS,
  LOCAL_SORTS,
  orderPatch,
  type BsState,
} from "../../lib/bsfilters";
import { BS_TIPS } from "../../lib/bstips";
import { TextFilterBody } from "../FilterBodies";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import { LevelsBody, MoreBody, TagsBody, type Patch } from "./BsFilterBodies";
import { BpmBody, LengthBody, RatingBody, UpvotesBody } from "./BsNumberBodies";
import { InBar } from "../BarSlot";
import { PresetsBar } from "./PresetsBar";

interface Props {
  state: BsState;
  update: Patch;
  set: (next: BsState) => void;
  clear: () => void;
  /** Narrow screens: the column headers have no filters, so the bar also offers order. */
  narrow: boolean;
}

function MoreFilters({ state, update, clear }: Omit<Props, "set" | "narrow">) {
  const total = bsTotal(bsCounts(state));
  const section = (title: string, body: ReactNode) => (
    <section>
      <h3>{title}</h3>
      {body}
    </section>
  );
  return (
    <Dialog.Root>
      <Tip text={BS_TIPS.moreFilters}>
        <Dialog.Trigger className="btn plain filters-btn">
          <Icon name="filter" filled={total > 0} />
          <span className="label-hide-mobile">More filters</span>
          {total > 0 && <span className="filter-badge static">{total}</span>}
        </Dialog.Trigger>
      </Tip>
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="sheet bs-sheet" aria-describedby={undefined}>
          <div className="sheet-head">
            <Dialog.Title>Filters</Dialog.Title>
            <button type="button" className="btn plain" disabled={!total} onClick={clear}>
              <Icon name="filter-x" />
              <span className="label-hide-mobile">Clear all</span>
            </button>
          </div>
          <div className="sheet-body">
            {section(
              "Search",
              <TextFilterBody
                label="Search BeatSaver"
                q={state.q}
                onChange={(q, replace) => update({ q }, replace)}
              />,
            )}
            {section("Levels", <LevelsBody state={state} update={update} />)}
            {section("Rating", <RatingBody state={state} update={update} />)}
            {section("Upvotes", <UpvotesBody state={state} update={update} />)}
            {section("Length", <LengthBody state={state} update={update} />)}
            {section("BPM", <BpmBody state={state} update={update} />)}
            {section("Tags", <TagsBody state={state} update={update} />)}
            {section("More", <MoreBody state={state} update={update} />)}
          </div>
          <div className="sheet-foot">
            <Dialog.Close className="btn primary show-btn">
              <Icon name="approve" />
              <span>Show maps</span>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Presets, the full filter sheet and clear; on narrow screens also order and direction. */
export function BsToolbar({ state, update, set, clear, narrow }: Props) {
  const active = bsTotal(bsCounts(state)) > 0;
  return (
    <InBar>
      <div className={narrow ? "lib-mobile-bar bs-toolbar" : "bs-toolbar"}>
        <PresetsBar state={state} onApply={set} />
        <div className="mobile-filters">
          {narrow && <OrderControls state={state} update={update} />}
          <MoreFilters state={state} update={update} clear={clear} />
          {active && (
            <Tip text="Remove every filter.">
              <button type="button" className="btn icon tap" onClick={clear}>
                <Icon name="filter-x" />
                <span className="sr">Clear filters</span>
              </button>
            </Tip>
          )}
        </div>
      </div>
    </InBar>
  );
}

function OrderControls({ state, update }: { state: BsState; update: Patch }) {
  return (
    <div className="sort-group">
      <label className="sort-select">
        <span className="sr">Order by</span>
        <select
          value={state.localSort ? `local:${state.localSort}` : state.order}
          onChange={(e) => update(orderPatch(e.target.value))}
        >
          {BS_ORDERS.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
          {LOCAL_SORTS.map((o) => (
            <option key={o} value={`local:${o}`}>
              {LOCAL_LABELS[o]}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        className="order-toggle"
        onClick={() => update({ ascending: !state.ascending })}
      >
        <Icon name={state.ascending ? "sort-asc" : "sort-desc"} />
        <span className="sr">{state.ascending ? "Ascending" : "Descending"}</span>
      </button>
    </div>
  );
}
