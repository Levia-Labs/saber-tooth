import { Icon } from "./icons";
import { Tip } from "./Tip";

/** Desktop popover wiring: one icon button that clears a whole column filter. */
export interface RowClear {
  /** Column name, e.g. "Status". */
  column: string;
  disabled: boolean;
  onClear: () => void;
}

/** Icon-only clear button placed beside a filter's input in the desktop popovers. */
export function ClearFilterButton({ column, disabled, onClear }: RowClear) {
  return (
    <Tip text="Clear this filter">
      <button
        type="button"
        className="btn icon clear-filter"
        aria-label={`Clear ${column} filter`}
        disabled={disabled}
        onClick={onClear}
      >
        <Icon name="filter-x" />
      </button>
    </Tip>
  );
}
