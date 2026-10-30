import { NUMBERS, type BsState } from "../../lib/bsfilters";
import { NumberField, StateRange } from "../StateBodies";
import type { Patch } from "./BsFilterBodies";

interface Props {
  state: BsState;
  update: Patch;
}

export function RatingBody({ state, update }: Props) {
  return (
    <NumberField
      label="Minimum rating (%)"
      field="minRating"
      bounds={NUMBERS.minRating}
      state={state}
      update={update}
      scale={100}
    />
  );
}

export function UpvotesBody({ state, update }: Props) {
  return (
    <NumberField
      label="Min upvotes"
      field="minUpvotes"
      bounds={NUMBERS.minUpvotes}
      state={state}
      update={update}
    />
  );
}

export function LengthBody({ state, update }: Props) {
  return (
    <StateRange
      name="Length"
      kind="duration"
      prefix="duration"
      limit={NUMBERS.durationMax.max}
      state={state}
      update={update}
    />
  );
}

export function BpmBody({ state, update }: Props) {
  return (
    <StateRange
      name="BPM"
      kind="integer"
      prefix="bpm"
      limit={NUMBERS.bpmMax.max}
      state={state}
      update={update}
    />
  );
}
