import * as Checkbox from "@radix-ui/react-checkbox";
import { useEffect, useId, useRef, useState } from "react";
import type { Facets, StatusKey } from "../api/types";
import { STATUS_META, STATUS_ORDER } from "../lib/status";
import { toggle } from "../lib/urlstate";
import { Icon } from "./icons";

export const SEARCH_DEBOUNCE_MS = 250;
const ENV_SEARCH_MIN = 10;

interface TitleProps {
  q: string;
  onChange: (q: string, replace: boolean) => void;
}

export function TitleFilterBody({ q, onChange }: TitleProps) {
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
      <label htmlFor={id}>Name or mapper</label>
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
  const shown = names.filter((n) => n.toLowerCase().includes(search.trim().toLowerCase()));
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
              {name}
            </Box>
            <span className="count">{counts.get(name) ?? 0}</span>
          </div>
        ))}
        {!shown.length && <p className="muted">No environments.</p>}
      </div>
    </div>
  );
}
