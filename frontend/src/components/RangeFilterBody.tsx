import { useId, useState } from "react";
import { durationInput, inverted, parseBounded, parseDuration } from "../lib/range";
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
    kind === "duration" ? parseDuration(text) : parseBounded(text, 0, max);
  const shown = kind === "duration" ? durationInput(value) : value === null ? "" : String(value);
  const [draft, setDraft] = useState(shown);
  const bad = parse(draft) === undefined || (parse(draft) ?? 0) > max;
  const [seen, setSeen] = useState(value);
  if (seen !== value) {
    // A change from outside (Clear, a preset, the URL) replaces whatever is typed.
    setSeen(value);
    if (parse(draft) !== value) setDraft(shown);
  }
  return (
    <div className="filter-body">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        inputMode={kind === "duration" ? "numeric" : "decimal"}
        autoComplete="off"
        placeholder={placeholder}
        aria-invalid={bad}
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          const next = parse(e.target.value);
          if (next !== undefined && (next ?? 0) <= max) onCommit(next);
        }}
      />
    </div>
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

/** Minimum and maximum inputs of a numeric column filter; the same body serves popover and sheet. */
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
  const text = (v: number | null | undefined) =>
    v === null || v === undefined ? "Any" : kind === "duration" ? durationInput(v) : String(v);
  const unit = kind === "duration" ? " (m:ss)" : "";
  return (
    <div className="filter-body">
      {rowClear && (
        <div className="filter-actions">
          <ClearFilterButton {...rowClear} />
        </div>
      )}
      <RangeField
        label={`${name}, at least${unit}`}
        kind={kind}
        value={min}
        max={limit}
        placeholder={text(bounds?.min)}
        onCommit={(v) => onChange({ min: v }, true)}
      />
      <RangeField
        label={`${name}, at most${unit}`}
        kind={kind}
        value={max}
        max={limit}
        placeholder={text(bounds?.max)}
        onCommit={(v) => onChange({ max: v }, true)}
      />
      {inverted(min, max) && (
        <p className="err" role="alert">
          The minimum is above the maximum, so this filter is ignored.
        </p>
      )}
    </div>
  );
}
