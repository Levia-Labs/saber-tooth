import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { InBar } from "../BarSlot";
import { Icon } from "../icons";
import { Tip } from "../Tip";

/** A titled section of the filter sheet. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

interface SortProps {
  options: readonly { value: string; label: string }[];
  value: string;
  ascending: boolean;
  onOrder: (value: string) => void;
  onToggle: () => void;
}

/** Order select and direction toggle for the narrow bar. */
function SortControls({ options, value, ascending, onOrder, onToggle }: SortProps) {
  return (
    <div className="sort-group">
      <label className="sort-select">
        <span className="sr">Order by</span>
        <select value={value} onChange={(e) => onOrder(e.target.value)}>
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <button type="button" className="order-toggle" onClick={onToggle}>
        <Icon name={ascending ? "sort-asc" : "sort-desc"} />
        <span className="sr">{ascending ? "Ascending" : "Descending"}</span>
      </button>
    </div>
  );
}

interface Props {
  /** Active filter count. */
  total: number;
  clear: () => void;
  narrow: boolean;
  sort: SortProps;
  moreTip: string;
  clearTip: string;
  sheetTitle: string;
  showLabel: string;
  /** Before the filter button, e.g. presets. */
  lead?: ReactNode;
  /** The sheet's sections. */
  children: ReactNode;
}

/** Shared bar of the BeatSaver lists: lead, order (narrow), the filter sheet and clear. */
export function ListToolbar(props: Props) {
  const { total, clear, narrow, sort, moreTip, clearTip, sheetTitle, showLabel, lead, children } =
    props;
  return (
    <InBar>
      <div className={narrow ? "lib-mobile-bar bs-toolbar" : "bs-toolbar"}>
        {lead}
        <div className="mobile-filters">
          {narrow && <SortControls {...sort} />}
          <Dialog.Root>
            <Tip text={moreTip}>
              <Dialog.Trigger className="btn plain filters-btn">
                <Icon name="filter" filled={total > 0} />
                <span className="label-collapsible">More filters</span>
                {total > 0 && <span className="filter-badge static">{total}</span>}
              </Dialog.Trigger>
            </Tip>
            <Dialog.Portal>
              <Dialog.Overlay className="overlay" />
              <Dialog.Content className="sheet bs-sheet" aria-describedby={undefined}>
                <div className="sheet-head">
                  <Dialog.Title>{sheetTitle}</Dialog.Title>
                  <button type="button" className="btn plain" disabled={!total} onClick={clear}>
                    <Icon name="filter-x" />
                    <span className="label-collapsible">Clear all</span>
                  </button>
                </div>
                <div className="sheet-body">{children}</div>
                <div className="sheet-foot">
                  <Dialog.Close className="btn primary show-btn">
                    <Icon name="approve" />
                    <span>{showLabel}</span>
                  </Dialog.Close>
                </div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
          {total > 0 && (
            <Tip text={clearTip}>
              <button type="button" className="btn icon tap" onClick={clear}>
                <Icon name="filter-x" />
                <span className="sr">Clear filters</span>
              </button>
            </Tip>
          )}
        </div>
      </div>
    </InBar>
  );
}
