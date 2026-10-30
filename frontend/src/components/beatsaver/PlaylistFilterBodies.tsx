import { useId } from "react";
import {
  PL_LOCAL_LABELS,
  PL_LOCAL_SORTS,
  PL_NUMBERS,
  PL_ORDERS,
  PL_ORDER_LABELS,
  plOrderPatch,
  type PlState,
} from "../../lib/plfilters";
import { ClearFilterButton, type RowClear } from "../ClearFilterButton";
import { DatePicker } from "../DatePicker";
import { NumberField, StateRange } from "../StateBodies";
import { Box } from "./Box";

export type PlPatch = (patch: Partial<PlState>, replace?: boolean) => void;

interface Props {
  state: PlState;
  update: PlPatch;
  /** Desktop popover wiring: a clear icon beside the first field. */
  rowClear?: RowClear;
}

export function PlRatingBody({ state, update, rowClear }: Props) {
  return (
    <NumberField
      label="Minimum rating (%)"
      field="minRating"
      bounds={PL_NUMBERS.minRating}
      state={state}
      update={update}
      scale={100}
      rowClear={rowClear}
    />
  );
}

export function PlUpvotesBody({ state, update, rowClear }: Props) {
  return (
    <NumberField
      label="Min upvotes"
      field="minUpvotes"
      bounds={PL_NUMBERS.minUpvotes}
      state={state}
      update={update}
      rowClear={rowClear}
    />
  );
}

const rangeBody = (name: string, kind: "number" | "duration", prefix: string, limit: number) =>
  function PlRangeBody({ state, update, rowClear }: Props) {
    return (
      <StateRange
        name={name}
        kind={kind}
        prefix={prefix}
        limit={limit}
        state={state}
        update={update}
        rowClear={rowClear}
      />
    );
  };

export const PlMapsBody = rangeBody("Maps", "number", "maps", PL_NUMBERS.mapsMax.max);
export const PlLengthBody = rangeBody("Length", "duration", "duration", PL_NUMBERS.durationMax.max);
export const PlNpsBody = rangeBody("NPS", "number", "nps", PL_NUMBERS.npsMax.max);

export function PlCreatedBody({ state, update, rowClear }: Props) {
  const id = useId();
  return (
    <div className="filter-body">
      {rowClear && (
        <div className="filter-actions">
          <ClearFilterButton {...rowClear} />
        </div>
      )}
      <span className="field-label">Created from</span>
      <DatePicker
        id={`${id}-from`}
        label="Created from"
        value={state.from}
        max={state.to || undefined}
        onChange={(from) => update({ from })}
      />
      <span className="field-label">Created until</span>
      <DatePicker
        id={`${id}-to`}
        label="Created until"
        value={state.to}
        min={state.from || undefined}
        onChange={(to) => update({ to })}
      />
    </div>
  );
}

export function PlMoreBody({ state, update }: Props) {
  const id = useId();
  return (
    <div className="filter-body">
      <Box
        id={`${id}-curated`}
        checked={state.curated}
        onToggle={() => update({ curated: !state.curated })}
      >
        Curated playlists only
      </Box>
      <Box
        id={`${id}-verified`}
        checked={state.verified}
        onToggle={() => update({ verified: !state.verified })}
      >
        Verified authors only
      </Box>
    </div>
  );
}

/** Order select and direction toggle, in the sheet and in the mobile bar. */
export function PlOrderSelect({ state, update }: Props) {
  const id = useId();
  return (
    <div className="filter-body">
      <label htmlFor={id}>Order by</label>
      <select
        id={id}
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
      <Box
        id={`${id}-asc`}
        checked={state.ascending}
        onToggle={() => update({ ascending: !state.ascending })}
      >
        Ascending
      </Box>
    </div>
  );
}
