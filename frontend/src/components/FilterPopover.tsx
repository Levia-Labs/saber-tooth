import * as Popover from "@radix-ui/react-popover";
import type { ReactNode } from "react";
import { Icon } from "./icons";
import { Tip } from "./Tip";

interface Props {
  /** Column name, used for the accessible label and heading. */
  label: string;
  tip: string;
  count: number;
  children: ReactNode;
}

/** Shared header of every filter panel: title left, icon-only close button top right. */
export function PanelHeader({ title }: { title: string }) {
  return (
    <header className="popover-head">
      <h3 className="popover-title">{title}</h3>
      <Tip text="Close">
        <Popover.Close className="btn icon plain popover-x" aria-label="Close filter">
          <Icon name="reject" />
        </Popover.Close>
      </Tip>
    </header>
  );
}

/** Filter button for a column header; opens an anchored, focus-trapped popover. */
export function FilterPopover({ label, tip, count, children }: Props) {
  const active = count > 0;
  const trigger = (
    <Popover.Trigger
      className={`filter-btn${active ? " active" : ""}`}
      aria-label={active ? `Filter ${label}, ${count} active` : `Filter ${label}`}
    >
      <Icon name="filter" filled={active} />
      {active && (
        <span className="filter-badge" aria-hidden="true">
          {count}
        </span>
      )}
    </Popover.Trigger>
  );
  return (
    <Popover.Root modal>
      <Tip text={tip}>{trigger}</Tip>
      <Popover.Portal>
        <Popover.Content
          className="popover"
          align="start"
          sideOffset={6}
          collisionPadding={8}
          aria-label={`${label} filter`}
          onOpenAutoFocus={(e) => {
            // Land on the first field, not the close button, so its tooltip stays shut and Escape closes the panel.
            const target = e.currentTarget as HTMLElement;
            const field = target.querySelector<HTMLElement>(
              "input, button:not(.popover-x), [tabindex]:not([tabindex='-1'])",
            );
            e.preventDefault();
            (field ?? target).focus();
          }}
        >
          <PanelHeader title={label} />
          {children}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
