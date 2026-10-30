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
import { ListToolbar, Section } from "./ListToolbar";
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

const ORDER_OPTIONS = [
  ...PL_ORDERS.map((o) => ({ value: o, label: PL_ORDER_LABELS[o] })),
  ...PL_LOCAL_SORTS.map((o) => ({ value: `local:${o}`, label: PL_LOCAL_LABELS[o] })),
];

/** The full filter sheet and clear; on narrow screens also order and direction. */
export function PlaylistToolbar({ state, update, clear, narrow }: Props) {
  return (
    <ListToolbar
      total={plTotal(plCounts(state))}
      clear={clear}
      narrow={narrow}
      sort={{
        options: ORDER_OPTIONS,
        value: state.localSort ? `local:${state.localSort}` : state.order,
        ascending: state.ascending,
        onOrder: (v) => update(plOrderPatch(v)),
        onToggle: () => update({ ascending: !state.ascending }),
      }}
      moreTip={PL_TIPS.moreFilters}
      clearTip={PL_TIPS.clearFilters}
      sheetTitle="Playlist filters"
      showLabel="Show playlists"
    >
      <Section title="Name">
        <TextFilterBody
          label="Search playlists"
          q={state.q}
          onChange={(q, replace) => update({ q }, replace)}
        />
      </Section>
      <Section title="Author">
        <TextFilterBody
          label="Author contains"
          q={state.owner}
          onChange={(owner, replace) => update({ owner }, replace)}
        />
      </Section>
      <Section title="Maps">
        <PlMapsBody state={state} update={update} />
      </Section>
      <Section title="Rating">
        <PlRatingBody state={state} update={update} />
      </Section>
      <Section title="Upvotes">
        <PlUpvotesBody state={state} update={update} />
      </Section>
      <Section title="Length">
        <PlLengthBody state={state} update={update} />
      </Section>
      <Section title="NPS">
        <PlNpsBody state={state} update={update} />
      </Section>
      <Section title="Created">
        <PlCreatedBody state={state} update={update} />
      </Section>
      <Section title="More">
        <PlMoreBody state={state} update={update} />
      </Section>
      <Section title="Order">
        <PlOrderSelect state={state} update={update} />
      </Section>
    </ListToolbar>
  );
}
