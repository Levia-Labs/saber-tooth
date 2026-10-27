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

/** Filter button for a column header; opens an anchored, focus-trapped popover. */
export function FilterPopover({ label, tip, count, children }: Props) {
  const active = count > 0;
  return (
    <Popover.Root modal>
      <Tip text={tip}>
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
      </Tip>
      <Popover.Portal>
        <Popover.Content
          className="popover"
          align="start"
          sideOffset={6}
          collisionPadding={8}
          aria-label={`${label} filter`}
        >
          {children}
          <Popover.Close className="btn plain popover-close">Close</Popover.Close>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
