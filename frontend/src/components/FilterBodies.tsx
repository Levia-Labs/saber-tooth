import * as Checkbox from "@radix-ui/react-checkbox";
import { useEffect, useId, useRef, useState } from "react";
import { LEVEL_KEYS, type Facets, type LevelKey, type StatusKey } from "../api/types";
import { formatEnvironment } from "../lib/environment";
import { LEVELS } from "../lib/levels";
import { STATUS_META, STATUS_ORDER } from "../lib/status";
import { toggle, type LevelMode } from "../lib/urlstate";
import { Icon } from "./icons";

export const SEARCH_DEBOUNCE_MS = 250;
const ENV_SEARCH_MIN = 10;

interface TextProps {
  q: string;
  /** Visible label of the text box, e.g. "Title contains". */
  label: string;
  onChange: (q: string, replace: boolean) => void;
}

/** Debounced "contains" text box shared by the Title and Author filters. */
export function TextFilterBody({ q, label, onChange }: TextProps) {
  const [text, setText] = useState(q);
  const [emitted, setEmitted] = useState(q);
  const [seen, setSeen] = useState(q);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // An outside change (clear all, back button) replaces the text; our own debounced echo does not.
  if (q !== seen) {
    setSeen(q);
    if (q !== emitted) {
      setEmitted(q);
      setText(q);
    }
  }
  const pending = useRef<string | null>(null);
  const emit = useRef(onChange);
  useEffect(() => {
    emit.current = onChange;
  }, [onChange]);
  // Closing the popover unmounts this body: send a search typed in the last 250 ms before it goes.
  useEffect(
    () => () => {
      clearTimeout(timer.current);
      if (pending.current !== null) emit.current(pending.current, true);
    },
    [],
  );
  const change = (value: string) => {
    setText(value);
    clearTimeout(timer.current);
    pending.current = value;
    timer.current = setTimeout(() => {
      pending.current = null;
      setEmitted(value);
      onChange(value, true);
    }, SEARCH_DEBOUNCE_MS);
  };
  const id = useId();
  return (
    <div className="filter-body">
      <label htmlFor={id}>{label}</label>
      <div className="field">
        <Icon name="search" />
        <input
          id={id}
          type="search"
          value={text}
          maxLength={200}
          autoComplete="off"
          onChange={(e) => change(e.target.value)}
        />
      </div>
      <button
        type="button"
        className="btn plain"
        disabled={!text}
        onClick={() => {
          clearTimeout(timer.current);
          pending.current = null;
          setText("");
          setEmitted("");
          onChange("", true);
        }}
      >
        Clear
      </button>
    </div>
  );
}

interface StatusProps {
  selected: StatusKey[];
  facets: Facets | undefined;
  onChange: (next: StatusKey[]) => void;
}

function Box(props: { id: string; checked: boolean; onToggle: () => void; children: string }) {
  return (
    <div className="check">
      <Checkbox.Root
        id={props.id}
        className="checkbox"
        checked={props.checked}
        onCheckedChange={props.onToggle}
      >
        <Checkbox.Indicator>
          <Icon name="approve" />
        </Checkbox.Indicator>
      </Checkbox.Root>
      <label htmlFor={props.id}>{props.children}</label>
    </div>
  );
}

export function StatusFilterBody({ selected, facets, onChange }: StatusProps) {
  const base = useId();
  return (
    <div className="filter-body">
      <div className="filter-actions">
        <button type="button" className="btn plain" onClick={() => onChange([...STATUS_ORDER])}>
          Select all
        </button>
        <button type="button" className="btn plain" onClick={() => onChange([])}>
          Clear
        </button>
      </div>
      <div role="group" aria-label="Status" className="checks">
        {STATUS_ORDER.map((key) => (
          <div className="check-row" key={key}>
            <Box
              id={`${base}-${key}`}
              checked={selected.includes(key)}
              onToggle={() => onChange(toggle(selected, key))}
            >
              {STATUS_META[key].label}
            </Box>
            <span className="count">{facets?.status[key] ?? 0}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface EnvProps {
  selected: string[];
  facets: Facets | undefined;
  onChange: (next: string[]) => void;
}

export function EnvFilterBody({ selected, facets, onChange }: EnvProps) {
  const base = useId();
  const [search, setSearch] = useState("");
  const all = facets?.environments ?? [];
  const names = [...new Set([...selected, ...all.map((e) => e.name)])];
  const counts = new Map(all.map((e) => [e.name, e.count]));
  const needle = search.trim().toLowerCase();
  const shown = names.filter(
    (n) => n.toLowerCase().includes(needle) || formatEnvironment(n).toLowerCase().includes(needle),
  );
  return (
    <div className="filter-body">
      {names.length > ENV_SEARCH_MIN && (
        <div className="field">
          <Icon name="search" />
          <input
            type="search"
            aria-label="Search environments"
            value={search}
            autoComplete="off"
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}
      <div className="filter-actions">
        <button type="button" className="btn plain" onClick={() => onChange([])}>
          Clear
        </button>
      </div>
      <div role="group" aria-label="Environment" className="checks">
        {shown.map((name, i) => (
          <div className="check-row" key={name}>
            <Box
              id={`${base}-${i}`}
              checked={selected.includes(name)}
              onToggle={() => onChange(toggle(selected, name))}
            >
              {formatEnvironment(name)}
            </Box>
            <span className="count">{counts.get(name) ?? 0}</span>
          </div>
        ))}
        {!shown.length && <p className="muted">No environments.</p>}
      </div>
    </div>
  );
}

interface MapperProps {
  selected: string[];
  facets: Facets | undefined;
  onChange: (next: string[]) => void;
}

/** Searchable checklist of mapper names with map counts. */
export function MapperListBody({ selected, facets, onChange }: MapperProps) {
  const base = useId();
  const [search, setSearch] = useState("");
  const all = facets?.mappers ?? [];
  const names = [...new Set([...selected, ...all.map((m) => m.name)])];
  const counts = new Map(all.map((m) => [m.name, m.count]));
  const needle = search.trim().toLowerCase();
  const shown = names.filter((n) => n.toLowerCase().includes(needle));
  return (
    <div className="filter-body">
      <div className="field">
        <Icon name="search" />
        <input
          type="search"
          aria-label="Search mappers"
          value={search}
          autoComplete="off"
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="filter-actions">
        <button type="button" className="btn plain" onClick={() => onChange([])}>
          Clear
        </button>
      </div>
      <div role="group" aria-label="Mapper" className="checks">
        {shown.map((name, i) => (
          <div className="check-row" key={name}>
            <Box
              id={`${base}-${i}`}
              checked={selected.includes(name)}
              onToggle={() => onChange(toggle(selected, name))}
            >
              {name}
            </Box>
            <span className="count">{counts.get(name) ?? 0}</span>
          </div>
        ))}
        {!shown.length && <p className="muted">No mappers.</p>}
      </div>
    </div>
  );
}

interface LevelsProps {
  selected: LevelKey[];
  mode: LevelMode;
  facets: Facets | undefined;
  onChange: (patch: { level?: LevelKey[]; levelMode?: LevelMode }) => void;
}

export function LevelsFilterBody({ selected, mode, facets, onChange }: LevelsProps) {
  const base = useId();
  return (
    <div className="filter-body">
      <div role="group" aria-label="Match" className="segmented">
        {(["any", "all"] as const).map((m) => (
          <button
            key={m}
            type="button"
            className="btn plain"
            aria-pressed={mode === m}
            onClick={() => onChange({ levelMode: m })}
          >
            {m === "any" ? "Any" : "All"}
          </button>
        ))}
      </div>
      <div className="filter-actions">
        <button type="button" className="btn plain" onClick={() => onChange({ level: [] })}>
          Clear
        </button>
      </div>
      <div role="group" aria-label="Levels" className="checks">
        {LEVEL_KEYS.map((key) => (
          <div className="check-row" key={key}>
            <Box
              id={`${base}-${key}`}
              checked={selected.includes(key)}
              onToggle={() => onChange({ level: toggle(selected, key) })}
            >
              {LEVELS.find((l) => l.key === key)?.label ?? key}
            </Box>
            <span className="count">{facets?.levels?.[key] ?? 0}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
