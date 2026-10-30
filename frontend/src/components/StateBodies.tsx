import { useId } from "react";
import { ClearFilterButton, type RowClear } from "./ClearFilterButton";
import { RangeFilterBody, type RangeKind } from "./RangeFilterBody";

type Patch<S> = (patch: Partial<S>, replace?: boolean) => void;
type Num = number | null;

/** A single bounded number filter over the state field `field`. */
export function NumberField<S extends object>(props: {
  label: string;
  field: keyof S & string;
  bounds: { min: number; max: number };
  state: S;
  update: Patch<S>;
  /** Multiply for display, e.g. 100 turns a 0-1 fraction into a percentage. */
  scale?: number;
  step?: number;
  /** Desktop popover wiring: a clear icon beside the field. */
  rowClear?: RowClear;
}) {
  const { label, field, bounds, state, update, scale = 1, step = 1, rowClear } = props;
  const id = useId();
  const { min, max } = bounds;
  const value = (state as Record<string, Num>)[field] ?? null;
  const patch = (v: Num) => update({ [field]: v } as Partial<S>, true);
  const input = (
    <input
      id={id}
      type="number"
      inputMode="decimal"
      min={min * scale}
      max={max * scale}
      step={step}
      value={value === null ? "" : Number((value * scale).toFixed(2))}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === "") return patch(null);
        const n = Number(raw) / scale;
        if (Number.isFinite(n)) patch(Math.min(max, Math.max(min, n)));
      }}
    />
  );
  return (
    <div className="filter-body">
      <label htmlFor={id}>{label}</label>
      {rowClear ? (
        <div className="filter-row">
          {input}
          <ClearFilterButton {...rowClear} />
        </div>
      ) : (
        input
      )}
    </div>
  );
}

/** A min/max range filter over the state fields `${prefix}Min` and `${prefix}Max`. */
export function StateRange<S extends object>(props: {
  name: string;
  kind: RangeKind;
  prefix: string;
  limit: number;
  state: S;
  update: Patch<S>;
  rowClear?: RowClear;
}) {
  const { name, kind, prefix, limit, state, update, rowClear } = props;
  const values = state as Record<string, Num>;
  return (
    <RangeFilterBody
      name={name}
      kind={kind}
      min={values[`${prefix}Min`] ?? null}
      max={values[`${prefix}Max`] ?? null}
      limit={limit}
      rowClear={rowClear}
      onChange={(r, replace) =>
        update(
          {
            ...("min" in r && { [`${prefix}Min`]: r.min }),
            ...("max" in r && { [`${prefix}Max`]: r.max }),
          } as Partial<S>,
          replace,
        )
      }
    />
  );
}
