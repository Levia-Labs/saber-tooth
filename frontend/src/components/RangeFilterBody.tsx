import { useId, useState } from "react";
import { formatClock, parseClock } from "../lib/clock";
import { inverted, parseBounded } from "../lib/range";
import { ClearFilterButton, type RowClear } from "./ClearFilterButton";

export type RangeKind = "duration" | "number";

interface FieldProps {
  label: string;
  kind: RangeKind;
  value: number | null;
  /** Largest accepted value; the smallest is always 0. */
  max: number;
  placeholder: string;
  onCommit: (next: number | null) => void;
}

function RangeField({ label, kind, value, max, placeholder, onCommit }: FieldProps) {
  const id = useId();
  const parse = (text: string) =>
    kind === "duration" ? parseClock(text) : parseBounded(text, 0, max);
  const shown = kind === "duration" ? formatClock(value) : value === null ? "" : String(value);
  const [draft, setDraft] = useState(shown);
  const parsed = parse(draft);
  const bad = parsed === undefined || (parsed ?? 0) > max;
  const [seen, setSeen] = useState(value);
  if (seen !== value) {
    // A change from outside (Clear, a preset, the URL) replaces whatever is typed.
    setSeen(value);
    if (parse(draft) !== value) setDraft(shown);
  }
  return (
    <input
      id={id}
      className="range-input"
      type="text"
      inputMode={kind === "duration" ? "numeric" : "decimal"}
      autoComplete="off"
      aria-label={label}
      placeholder={placeholder}
      aria-invalid={bad}
      value={draft}
      onChange={(e) => {
        setDraft(e.target.value);
        const next = parse(e.target.value);
        if (next !== undefined && (next ?? 0) <= max) onCommit(next);
      }}
    />
  );
}

interface Props {
  /** Column name for the field labels, e.g. "Length" or "BPM". */
  name: string;
  kind: RangeKind;
  min: number | null;
  max: number | null;
  /** Known smallest and largest value, shown as placeholders. */
  bounds?: { min: number | null; max: number | null };
  limit: number;
  onChange: (patch: { min?: number | null; max?: number | null }, replace?: boolean) => void;
  rowClear?: RowClear;
}

/** Minimum and maximum inputs on one row, "min - max", with the clear button at its right end. */
export function RangeFilterBody({
  name,
  kind,
  min,
  max,
  bounds,
  limit,
  onChange,
  rowClear,
}: Props) {
  const duration = kind === "duration";
  const hint = (v: number | null | undefined) =>
    duration ? "mm:ss" : v === null || v === undefined ? "Any" : String(v);
  return (
    <div className="filter-body">
      <div className="filter-row">
        <RangeField
          label={duration ? "Minimum length" : `${name}, at least`}
          kind={kind}
          value={min}
          max={limit}
          placeholder={hint(bounds?.min)}
          onCommit={(v) => onChange({ min: v }, true)}
        />
        <span className="range-sep" aria-hidden="true">
          -
        </span>
        <RangeField
          label={duration ? "Maximum length" : `${name}, at most`}
          kind={kind}
          value={max}
          max={limit}
          placeholder={hint(bounds?.max)}
          onCommit={(v) => onChange({ max: v }, true)}
        />
        {rowClear && <ClearFilterButton {...rowClear} />}
      </div>
      {inverted(min, max) && (
        <p className="err" role="alert">
          The minimum is above the maximum, so this filter is ignored.
        </p>
      )}
    </div>
  );
}
