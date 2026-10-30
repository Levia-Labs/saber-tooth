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
import { RangeFilterBody } from "../RangeFilterBody";
import { Box } from "./Box";

export type PlPatch = (patch: Partial<PlState>, replace?: boolean) => void;

interface Props {
  state: PlState;
  update: PlPatch;
  /** Desktop popover wiring: a clear icon beside the first field. */
  rowClear?: RowClear;
}

type NumKey = keyof typeof PL_NUMBERS;

function NumberField(props: {
  label: string;
  field: NumKey;
  state: PlState;
  update: PlPatch;
  scale?: number;
  rowClear?: RowClear;
}) {
  const { label, field, state, update, scale = 1, rowClear } = props;
  const id = useId();
  const { min, max } = PL_NUMBERS[field];
  const value = state[field];
  return (
    <div className="filter-body">
      <label htmlFor={id}>{label}</label>
      <div className={rowClear ? "filter-row" : undefined}>
        <input
          id={id}
          type="number"
          inputMode="decimal"
          min={min * scale}
          max={max * scale}
          step={1}
          value={value === null ? "" : Number((value * scale).toFixed(2))}
          onChange={(e) => {
            const raw = e.target.value;
            if (raw === "") return update({ [field]: null }, true);
            const n = Number(raw) / scale;
            if (Number.isFinite(n)) update({ [field]: Math.min(max, Math.max(min, n)) }, true);
          }}
        />
        {rowClear && <ClearFilterButton {...rowClear} />}
      </div>
    </div>
  );
}

export function PlRatingBody({ state, update, rowClear }: Props) {
  return (
    <NumberField
      label="Minimum rating (%)"
      field="minRating"
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
      state={state}
      update={update}
      rowClear={rowClear}
    />
  );
}

export function PlMapsBody({ state, update, rowClear }: Props) {
  return (
    <RangeFilterBody
      name="Maps"
      kind="number"
      min={state.mapsMin}
      max={state.mapsMax}
      limit={PL_NUMBERS.mapsMax.max}
      rowClear={rowClear}
      onChange={(r, replace) =>
        update(
          { ...("min" in r && { mapsMin: r.min }), ...("max" in r && { mapsMax: r.max }) },
          replace,
        )
      }
    />
  );
}

export function PlLengthBody({ state, update, rowClear }: Props) {
  return (
    <RangeFilterBody
      name="Length"
      kind="duration"
      min={state.durationMin}
      max={state.durationMax}
      limit={PL_NUMBERS.durationMax.max}
      rowClear={rowClear}
      onChange={(r, replace) =>
        update(
          {
            ...("min" in r && { durationMin: r.min }),
            ...("max" in r && { durationMax: r.max }),
          },
          replace,
        )
      }
    />
  );
}

export function PlNpsBody({ state, update, rowClear }: Props) {
  return (
    <RangeFilterBody
      name="NPS"
      kind="number"
      min={state.npsMin}
      max={state.npsMax}
      limit={PL_NUMBERS.npsMax.max}
      rowClear={rowClear}
      onChange={(r, replace) =>
        update(
          { ...("min" in r && { npsMin: r.min }), ...("max" in r && { npsMax: r.max }) },
          replace,
        )
      }
    />
  );
}

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
