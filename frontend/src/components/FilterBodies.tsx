import * as Checkbox from "@radix-ui/react-checkbox";
import { useId, useState } from "react";
import { LEVEL_KEYS, type Facets, type LevelKey, type StatusKey } from "../api/types";
import { formatEnvironment } from "../lib/environment";
import { LEVELS } from "../lib/levels";
import { STATUS_META, STATUS_ORDER } from "../lib/status";
import { toggle, type LevelMode } from "../lib/urlstate";
import { ClearFilterButton, type RowClear } from "./ClearFilterButton";
import { Icon } from "./icons";

export { SEARCH_DEBOUNCE_MS, TextFilterBody } from "./TextFilterBody";

const ENV_SEARCH_MIN = 10;

interface StatusProps {
  selected: StatusKey[];
  facets: Facets | undefined;
  onChange: (next: StatusKey[]) => void;
  rowClear?: RowClear;
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

export function StatusFilterBody({ selected, facets, onChange, rowClear }: StatusProps) {
  const base = useId();
  return (
    <div className="filter-body">
      <div className="filter-actions">
        <button
          type="button"
          className="btn icon"
          aria-label="Select all"
          title="Select all"
          onClick={() => onChange([...STATUS_ORDER])}
        >
          <Icon name="approve" />
        </button>
        {rowClear ? (
          <ClearFilterButton {...rowClear} />
        ) : (
          <button
            type="button"
            className="btn icon"
            aria-label="Clear"
            title="Clear"
            onClick={() => onChange([])}
          >
            <Icon name="filter-x" />
          </button>
        )}
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
  rowClear?: RowClear;
}

export function EnvFilterBody({ selected, facets, onChange, rowClear }: EnvProps) {
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
        <div className="filter-row">
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
          {rowClear && <ClearFilterButton {...rowClear} />}
        </div>
      )}
      {rowClear && names.length <= ENV_SEARCH_MIN && (
        <div className="filter-actions end">
          <ClearFilterButton {...rowClear} />
        </div>
      )}
      {!rowClear && (
        <div className="filter-actions">
          <button
            type="button"
            className="btn icon"
            aria-label="Clear"
            title="Clear"
            onClick={() => onChange([])}
          >
            <Icon name="filter-x" />
          </button>
        </div>
      )}
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
  rowClear?: RowClear;
}

/** Searchable checklist of mapper names with map counts. */
export function MapperListBody({ selected, facets, onChange, rowClear }: MapperProps) {
  const base = useId();
  const [search, setSearch] = useState("");
  const all = facets?.mappers ?? [];
  const names = [...new Set([...selected, ...all.map((m) => m.name)])];
  const counts = new Map(all.map((m) => [m.name, m.count]));
  const needle = search.trim().toLowerCase();
  const shown = names.filter((n) => n.toLowerCase().includes(needle));
  return (
    <div className="filter-body">
      <div className="filter-row">
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
        {rowClear && <ClearFilterButton {...rowClear} />}
      </div>
      {!rowClear && (
        <div className="filter-actions">
          <button
            type="button"
            className="btn icon"
            aria-label="Clear"
            title="Clear"
            onClick={() => onChange([])}
          >
            <Icon name="filter-x" />
          </button>
        </div>
      )}
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
  rowClear?: RowClear;
}

export function LevelsFilterBody({ selected, mode, facets, onChange, rowClear }: LevelsProps) {
  const base = useId();
  return (
    <div className="filter-body">
      <div className="filter-row">
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
        {rowClear && <ClearFilterButton {...rowClear} />}
      </div>
      {!rowClear && (
        <div className="filter-actions">
          <button
            type="button"
            className="btn icon"
            aria-label="Clear"
            title="Clear"
            onClick={() => onChange({ level: [] })}
          >
            <Icon name="filter-x" />
          </button>
        </div>
      )}
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
