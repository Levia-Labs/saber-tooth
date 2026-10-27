import { useId, useState } from "react";
import { LEVEL_KEYS } from "../../api/types";
import {
  BS_ORDERS,
  cleanTag,
  NUMBERS,
  type BsOrder,
  type BsState,
  type Scope,
} from "../../lib/bsfilters";
import { LEVELS } from "../../lib/levels";
import { toggle } from "../../lib/urlstate";
import { Icon } from "../icons";
import { Tip } from "../Tip";
import { Box } from "./Box";

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

type NumKey = keyof typeof NUMBERS;

function NumberField(props: {
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

export function RatingBody({ state, update }: Props) {
  return (
    <>
      <NumberField
        label="Minimum rating (%)"
        field="minRating"
        state={state}
        update={update}
        scale={100}
      />
      <NumberField label="Min upvotes" field="minUpvotes" state={state} update={update} />
    </>
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
        state={state}
        update={update}
        step={0.1}
      />
      <NumberField
        label="Notes per second, at most"
        field="npsMax"
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
      <div className="filter-actions">
        <button type="button" className="btn plain" onClick={() => update({ tags: [] })}>
          <Icon name="filter-x" />
          <span className="label-hide-mobile">Clear</span>
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
      <label htmlFor={`${base}-new`}>Other tag</label>
      <div className="filter-actions">
        <input
          id={`${base}-new`}
          type="text"
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
      </div>
    </div>
  );
}

export function TempoBody({ state, update }: Props) {
  return (
    <div className="filter-body">
      <NumberField label="Length, at least (seconds)" field="durationMin" {...{ state, update }} />
      <NumberField label="Length, at most (seconds)" field="durationMax" {...{ state, update }} />
      <NumberField label="BPM, at least" field="bpmMin" {...{ state, update }} />
      <NumberField label="BPM, at most" field="bpmMax" {...{ state, update }} />
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
      <label htmlFor={`${id}-from`}>Uploaded from</label>
      <input
        id={`${id}-from`}
        type="date"
        value={state.from}
        onChange={(e) => update({ from: e.target.value })}
      />
      <label htmlFor={`${id}-to`}>Uploaded until</label>
      <input
        id={`${id}-to`}
        type="date"
        value={state.to}
        onChange={(e) => update({ to: e.target.value })}
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
        value={state.order}
        onChange={(e) => update({ order: e.target.value as BsOrder })}
      >
        {BS_ORDERS.map((o) => (
          <option key={o} value={o}>
            {o}
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
