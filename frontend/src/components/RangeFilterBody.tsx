import { useId, useState } from "react";
import { formatClock, parseClock } from "../lib/clock";
import { inverted, parseBounded } from "../lib/range";
import { stepBound } from "../lib/stepRange";
import { ClearFilterButton, type RowClear } from "./ClearFilterButton";
import { StepButtons } from "./StepButtons";

/** "duration" is mm:ss; "integer" whole numbers only; "number" allows two decimals. */
export type RangeKind = "duration" | "number" | "integer";

const STEP_FAST = 5;

interface FieldProps {
  label: string;
  kind: RangeKind;
  value: number | null;
  /** Largest accepted value; the smallest is always 0. */
  max: number;
  placeholder: string;
  onCommit: (next: number | null) => void;
  /** Arrow stepping (duration and integer kinds): allowed span, start when unset, accessible noun. */
  stepper?: { lo: number; hi: number; start: number; noun: string };
}

function parseKind(kind: RangeKind, text: string, max: number) {
  if (kind === "duration") return parseClock(text);
  if (kind === "integer" && !/^\d{0,4}$/.test(text)) return undefined;
  return parseBounded(text, 0, max);
}

function RangeField({ label, kind, value, max, placeholder, onCommit, stepper }: FieldProps) {
  const id = useId();
  const parse = (text: string) => parseKind(kind, text, max);
  const shown = kind === "duration" ? formatClock(value) : value === null ? "" : String(value);
  const [draft, setDraft] = useState(shown);
  const parsed = parse(draft);
  const bad = parsed === undefined || (parsed ?? 0) > max;
  const [seen, setSeen] = useState(value);
  if (seen !== value) {
    // A change from outside (Clear, a preset, the URL, an arrow) replaces whatever is typed.
    setSeen(value);
    if (parse(draft) !== value) setDraft(shown);
  }
  const step = (direction: 1 | -1, fast: boolean) => {
    if (!stepper) return;
    const delta = direction * (fast ? STEP_FAST : 1);
    onCommit(stepBound(value, delta, stepper.lo, stepper.hi, stepper.start));
  };
  return (
    <span className="range-field">
      <input
        id={id}
        className="range-input"
        type="text"
        inputMode={kind === "number" ? "decimal" : "numeric"}
        autoComplete="off"
        aria-label={label}
        placeholder={placeholder}
        aria-invalid={bad}
        value={draft}
        onKeyDown={(e) => {
          if (!stepper || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
          e.preventDefault();
          step(e.key === "ArrowUp" ? 1 : -1, false);
        }}
        onChange={(e) => {
          // Integer inputs refuse the whole edit when it holds a point or a letter.
          if (kind === "integer" && !/^\d*$/.test(e.target.value)) return;
          setDraft(e.target.value);
          const next = parse(e.target.value);
          if (next !== undefined && (next ?? 0) <= max) onCommit(next);
        }}
      />
      {stepper && <StepButtons noun={stepper.noun} onStep={step} />}
    </span>
  );
}

interface Props {
  /** Column name for the field labels, e.g. "Length" or "BPM". */
  name: string;
  kind: RangeKind;
  min: number | null;
  max: number | null;
  /** Known smallest and largest value, shown as placeholders and as the arrows' start. */
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
  const stepped = duration || kind === "integer";
  // Whole-number kinds round a fractional facet bound outward: min down, max up.
  const edge = (which: "min" | "max") => {
    const v = bounds?.[which];
    if (v === null || v === undefined) return null;
    return !stepped ? v : which === "min" ? Math.floor(v) : Math.ceil(v);
  };
  const hint = (which: "min" | "max") => {
    const v = edge(which);
    if (duration) return v === null ? "mm:ss" : formatClock(v);
    return v === null ? "Any" : String(v);
  };
  const noun = duration ? "length" : name;
  const stepper = (which: "min" | "max") =>
    stepped
      ? {
          lo: which === "min" ? 0 : (min ?? 0),
          hi: which === "min" ? (max ?? limit) : limit,
          start: edge(which) ?? 0,
          noun: `${which === "min" ? "minimum" : "maximum"} ${noun}`,
        }
      : undefined;
  return (
    <div className="filter-body">
      <div className="filter-row">
        <RangeField
          label={duration ? "Minimum length" : `${name}, at least`}
          kind={kind}
          value={min}
          max={limit}
          placeholder={hint("min")}
          onCommit={(v) => onChange({ min: v }, true)}
          stepper={stepper("min")}
        />
        <span className="range-sep" aria-hidden="true">
          -
        </span>
        <RangeField
          label={duration ? "Maximum length" : `${name}, at most`}
          kind={kind}
          value={max}
          max={limit}
          placeholder={hint("max")}
          onCommit={(v) => onChange({ max: v }, true)}
          stepper={stepper("max")}
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
