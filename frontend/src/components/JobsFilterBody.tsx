import { useId } from "react";
import { ClearFilterButton, type RowClear } from "./ClearFilterButton";
import { Box } from "./beatsaver/Box";

interface Props<T extends string> {
  label: string;
  options: readonly { value: T; label: string; count: number }[];
  selected: T[];
  onChange: (next: T[]) => void;
  rowClear: RowClear;
}

/** Multi-select checklist for the Status and Kind filters; each option shows how many jobs match. */
export function JobsFilterBody<T extends string>({
  label,
  options,
  selected,
  onChange,
  rowClear,
}: Props<T>) {
  const base = useId();
  const toggle = (value: T) =>
    onChange(options.map((o) => o.value).filter((v) => (v === value) !== selected.includes(v)));
  return (
    <div className="filter-body">
      <div className="filter-actions">
        <ClearFilterButton {...rowClear} />
      </div>
      <div role="group" aria-label={label} className="checks">
        {options.map((o) => (
          <div className="check-row" key={o.value}>
            <Box
              id={`${base}-${o.value}`}
              checked={selected.includes(o.value)}
              onToggle={() => toggle(o.value)}
            >
              {o.label}
            </Box>
            <span className="count">{o.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
