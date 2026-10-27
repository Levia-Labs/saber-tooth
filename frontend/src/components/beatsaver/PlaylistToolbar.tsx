import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import {
  PL_LOCAL_LABELS,
  PL_LOCAL_SORTS,
  PL_ORDERS,
  PL_ORDER_LABELS,
  plCounts,
  plOrderPatch,
  plTotal,
  type PlState,
} from "../../lib/plfilters";
import { PL_TIPS } from "../../lib/pltips";
import { TextFilterBody } from "../FilterBodies";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import {
  PlCreatedBody,
  PlLengthBody,
  PlMapsBody,
  PlMoreBody,
  PlNpsBody,
  PlOrderSelect,
  PlRatingBody,
  PlUpvotesBody,
  type PlPatch,
} from "./PlaylistFilterBodies";

interface Props {
  state: PlState;
  update: PlPatch;
  clear: () => void;
  /** Narrow screens: the column headers are gone, so the bar also offers order. */
  narrow: boolean;
}

function FilterSheet({ state, update, clear }: Omit<Props, "narrow">) {
  const total = plTotal(plCounts(state));
  const section = (title: string, body: ReactNode) => (
    <section>
      <h3>{title}</h3>
      {body}
    </section>
  );
  return (
    <Dialog.Root>
      <Tip text={PL_TIPS.moreFilters}>
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
            <Dialog.Title>Playlist filters</Dialog.Title>
            <button type="button" className="btn plain" disabled={!total} onClick={clear}>
              <Icon name="filter-x" />
              <span className="label-hide-mobile">Clear all</span>
            </button>
          </div>
          {section(
            "Name",
            <TextFilterBody
              label="Search playlists"
              q={state.q}
              onChange={(q, replace) => update({ q }, replace)}
            />,
          )}
          {section(
            "Author",
            <TextFilterBody
              label="Author contains"
              q={state.owner}
              onChange={(owner, replace) => update({ owner }, replace)}
            />,
          )}
          {section("Maps", <PlMapsBody state={state} update={update} />)}
          {section("Rating", <PlRatingBody state={state} update={update} />)}
          {section("Upvotes", <PlUpvotesBody state={state} update={update} />)}
          {section("Length", <PlLengthBody state={state} update={update} />)}
          {section("NPS", <PlNpsBody state={state} update={update} />)}
          {section("Created", <PlCreatedBody state={state} update={update} />)}
          {section("More", <PlMoreBody state={state} update={update} />)}
          {section("Order", <PlOrderSelect state={state} update={update} />)}
          <Dialog.Close className="btn primary">
            <Icon name="approve" />
            <span>Show playlists</span>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function OrderControls({ state, update }: { state: PlState; update: PlPatch }) {
  return (
    <div className="sort-group">
      <label className="sort-select">
        <span className="sr">Order by</span>
        <select
          value={state.localSort ? `local:${state.localSort}` : state.order}
          onChange={(e) => update(plOrderPatch(e.target.value))}
        >
          {PL_ORDERS.map((o) => (
            <option key={o} value={o}>
              {PL_ORDER_LABELS[o]}
            </option>
          ))}
          {PL_LOCAL_SORTS.map((o) => (
            <option key={o} value={`local:${o}`}>
              {PL_LOCAL_LABELS[o]}
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

/** The full filter sheet and clear; on narrow screens also order and direction. */
export function PlaylistToolbar({ state, update, clear, narrow }: Props) {
  const active = plTotal(plCounts(state)) > 0;
  return (
    <div className={narrow ? "lib-mobile-bar bs-toolbar" : "bs-toolbar"}>
      <div className="mobile-filters">
        {narrow && <OrderControls state={state} update={update} />}
        <FilterSheet state={state} update={update} clear={clear} />
        {active && (
          <Tip text={PL_TIPS.clearFilters}>
            <button type="button" className="btn icon tap" onClick={clear}>
              <Icon name="filter-x" />
              <span className="sr">Clear filters</span>
            </button>
          </Tip>
        )}
      </div>
    </div>
  );
}
