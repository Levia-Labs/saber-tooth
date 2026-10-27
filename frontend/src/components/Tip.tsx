import * as Tooltip from "@radix-ui/react-tooltip";
import type { ReactElement } from "react";

/** Tooltip around one focusable element: shows on hover and focus, hides on Escape and blur. */
export function Tip({ text, children }: { text: string; children: ReactElement }) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="tooltip" side="top" sideOffset={8} collisionPadding={8}>
          {text}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

export const TipProvider = Tooltip.Provider;
