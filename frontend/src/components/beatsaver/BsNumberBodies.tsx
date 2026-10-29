import { useId } from "react";
import { NUMBERS, type BsState } from "../../lib/bsfilters";
import { RangeFilterBody } from "../RangeFilterBody";
import type { Patch } from "./BsFilterBodies";

interface Props {
  state: BsState;
  update: Patch;
}

type NumKey = keyof typeof NUMBERS;

export function NumberField(props: {
  label: string;
  field: NumKey;
  state: BsState;
  update: Patch;
  /** Multiply for display, e.g. 100 turns a 0-1 fraction into a percentage. */
  scale?: number;
  step?: number;
}) {
  const { label, field, state, update, scale = 1, step = 1 } = props;
  const id = useId();
  const { min, max } = NUMBERS[field];
  const value = state[field];
  return (
    <div className="filter-body">
      <label htmlFor={id}>{label}</label>
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
          if (raw === "") return update({ [field]: null }, true);
          const n = Number(raw) / scale;
          if (Number.isFinite(n)) update({ [field]: Math.min(max, Math.max(min, n)) }, true);
        }}
      />
    </div>
  );
}

export function RatingBody({ state, update }: Props) {
  return (
    <NumberField
      label="Minimum rating (%)"
      field="minRating"
      state={state}
      update={update}
      scale={100}
    />
  );
}

export function UpvotesBody({ state, update }: Props) {
  return <NumberField label="Min upvotes" field="minUpvotes" state={state} update={update} />;
}

export function LengthBody({ state, update }: Props) {
  return (
    <RangeFilterBody
      name="Length"
      kind="duration"
      min={state.durationMin}
      max={state.durationMax}
      limit={NUMBERS.durationMax.max}
      onChange={(r, replace) =>
        update(
          { ...("min" in r && { durationMin: r.min }), ...("max" in r && { durationMax: r.max }) },
          replace,
        )
      }
    />
  );
}

export function BpmBody({ state, update }: Props) {
  return (
    <RangeFilterBody
      name="BPM"
      kind="integer"
      min={state.bpmMin}
      max={state.bpmMax}
      limit={NUMBERS.bpmMax.max}
      onChange={(r, replace) =>
        update(
          { ...("min" in r && { bpmMin: r.min }), ...("max" in r && { bpmMax: r.max }) },
          replace,
        )
      }
    />
  );
}
