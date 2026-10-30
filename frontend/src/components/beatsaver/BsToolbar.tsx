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
import { LevelsBody, MoreBody, TagsBody, type Patch } from "./BsFilterBodies";
import { BpmBody, LengthBody, RatingBody, UpvotesBody } from "./BsNumberBodies";
import { ListToolbar, Section } from "./ListToolbar";
import { PresetsBar } from "./PresetsBar";

interface Props {
  state: BsState;
  update: Patch;
  set: (next: BsState) => void;
  clear: () => void;
  /** Narrow screens: the column headers have no filters, so the bar also offers order. */
  narrow: boolean;
}

const ORDER_OPTIONS = [
  ...BS_ORDERS.map((o) => ({ value: o, label: o })),
  ...LOCAL_SORTS.map((o) => ({ value: `local:${o}`, label: LOCAL_LABELS[o] })),
];

/** Presets, the full filter sheet and clear; on narrow screens also order and direction. */
export function BsToolbar({ state, update, set, clear, narrow }: Props) {
  return (
    <ListToolbar
      total={bsTotal(bsCounts(state))}
      clear={clear}
      narrow={narrow}
      sort={{
        options: ORDER_OPTIONS,
        value: state.localSort ? `local:${state.localSort}` : state.order,
        ascending: state.ascending,
        onOrder: (v) => update(orderPatch(v)),
        onToggle: () => update({ ascending: !state.ascending }),
      }}
      moreTip={BS_TIPS.moreFilters}
      clearTip="Remove every filter."
      sheetTitle="Filters"
      showLabel="Show maps"
      lead={<PresetsBar state={state} onApply={set} />}
    >
      <Section title="Search">
        <TextFilterBody
          label="Search BeatSaver"
          q={state.q}
          onChange={(q, replace) => update({ q }, replace)}
        />
      </Section>
      <Section title="Levels">
        <LevelsBody state={state} update={update} />
      </Section>
      <Section title="Rating">
        <RatingBody state={state} update={update} />
      </Section>
      <Section title="Upvotes">
        <UpvotesBody state={state} update={update} />
      </Section>
      <Section title="Length">
        <LengthBody state={state} update={update} />
      </Section>
      <Section title="BPM">
        <BpmBody state={state} update={update} />
      </Section>
      <Section title="Tags">
        <TagsBody state={state} update={update} />
      </Section>
      <Section title="More">
        <MoreBody state={state} update={update} />
      </Section>
    </ListToolbar>
  );
}
