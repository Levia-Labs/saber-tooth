import { useId, useState } from "react";
import { LEVEL_KEYS } from "../../api/types";
import {
  BS_ORDERS,
  cleanTag,
  LOCAL_LABELS,
  LOCAL_SORTS,
  NUMBERS,
  orderPatch,
  type BsState,
  type Scope,
} from "../../lib/bsfilters";
import { LEVELS } from "../../lib/levels";
import { toggle } from "../../lib/urlstate";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import { DatePicker } from "../DatePicker";
import { Box } from "./Box";
import { NumberField } from "../StateBodies";

export type Patch = (patch: Partial<BsState>, replace?: boolean) => void;
interface Props {
  state: BsState;
  update: Patch;
}

export const SUGGESTED_TAGS = [
  "electronic",
  "dubstep",
  "rock",
  "metal",
  "punk",
  "j-rock",
  "techno",
  "house",
  "trance",
  "drum-and-bass",
  "pop",
  "anime",
  "hip-hop-rap",
  "video-game",
  "dance",
  "country",
] as const;

function ScopeButtons(props: {
  label: string;
  value: Scope;
  onChange: (next: Scope) => void;
  words: [string, string];
}) {
  return (
    <div role="group" aria-label={props.label} className="segmented">
      {(["any", "all"] as const).map((m, i) => (
        <button
          key={m}
          type="button"
          className="btn plain"
          aria-pressed={props.value === m}
          onClick={() => props.onChange(m)}
        >
          {props.words[i]}
        </button>
      ))}
    </div>
  );
}

export function LevelsBody({ state, update }: Props) {
  const base = useId();
  return (
    <div className="filter-body">
      <ScopeButtons
        label="Required difficulties"
        value={state.diffsMode}
        words={["Any of these", "All of these"]}
        onChange={(diffsMode) => update({ diffsMode })}
      />
      <div role="group" aria-label="Standard difficulties" className="checks">
        {LEVEL_KEYS.map((key) => (
          <Box
            key={key}
            id={`${base}-${key}`}
            checked={state.diffs.includes(key)}
            onToggle={() => update({ diffs: toggle(state.diffs, key) })}
          >
            {LEVELS.find((l) => l.key === key)?.label ?? key}
          </Box>
        ))}
      </div>
      <NumberField
        label="Notes per second, at least"
        field="npsMin"
        bounds={NUMBERS.npsMin}
        state={state}
        update={update}
        step={0.1}
      />
      <NumberField
        label="Notes per second, at most"
        field="npsMax"
        bounds={NUMBERS.npsMax}
        state={state}
        update={update}
        step={0.1}
      />
      <ScopeButtons
        label="Notes per second applies to"
        value={state.npsScope}
        words={["Any difficulty", "Every difficulty"]}
        onChange={(npsScope) => update({ npsScope })}
      />
    </div>
  );
}

export function TagsBody({ state, update }: Props) {
  const base = useId();
  const [draft, setDraft] = useState("");
  const names = [...new Set([...state.tags, ...SUGGESTED_TAGS])];
  const add = () => {
    const tag = cleanTag(draft);
    if (tag && !state.tags.includes(tag)) update({ tags: [...state.tags, tag] });
    setDraft("");
  };
  return (
    <div className="filter-body">
      <p className="muted">Maps with any of the ticked tags.</p>
      <div className="filter-row">
        <input
          id={`${base}-new`}
          type="text"
          aria-label="Other tag"
          placeholder="Other tag"
          value={draft}
          maxLength={40}
          autoComplete="off"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            e.preventDefault();
            add();
          }}
        />
        <Tip text="Add this tag to the filter">
          <button
            type="button"
            className="btn icon"
            disabled={!cleanTag(draft)}
            aria-label="Add tag"
            onClick={add}
          >
            <Icon name="tag-plus" />
          </button>
        </Tip>
        <button type="button" className="btn plain" onClick={() => update({ tags: [] })}>
          <Icon name="filter-x" />
          <span className="label-collapsible">Clear</span>
        </button>
      </div>
      <div role="group" aria-label="Tags" className="checks bs-tag-checks">
        {names.map((tag, i) => (
          <Box
            key={tag}
            id={`${base}-${i}`}
            checked={state.tags.includes(tag)}
            onToggle={() => update({ tags: toggle(state.tags, tag) })}
          >
            {tag}
          </Box>
        ))}
      </div>
    </div>
  );
}

export function MoreBody({ state, update }: Props) {
  const id = useId();
  return (
    <div className="filter-body">
      <Box
        id={`${id}-ranked`}
        checked={state.ranked}
        onToggle={() => update({ ranked: !state.ranked })}
      >
        Ranked maps only
      </Box>
      <span className="field-label">Uploaded from</span>
      <DatePicker
        id={`${id}-from`}
        label="Uploaded from"
        value={state.from}
        max={state.to || undefined}
        onChange={(from) => update({ from })}
      />
      <span className="field-label">Uploaded until</span>
      <DatePicker
        id={`${id}-to`}
        label="Uploaded until"
        value={state.to}
        min={state.from || undefined}
        onChange={(to) => update({ to })}
      />
      <OrderSelect state={state} update={update} />
    </div>
  );
}

/** Order select and direction toggle, in the sheet and in the mobile bar. */
export function OrderSelect({ state, update }: Props) {
  const id = useId();
  return (
    <div className="filter-body">
      <label htmlFor={id}>Order by</label>
      <select
        id={id}
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
