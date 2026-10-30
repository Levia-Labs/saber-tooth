import * as Popover from "@radix-ui/react-popover";
import * as Tooltip from "@radix-ui/react-tooltip";
import { useEffect, useRef, useState, type ReactElement } from "react";
import { useMediaQuery } from "../lib/hooks";

export const LONG_PRESS_MS = 450;

interface Props {
  text: string;
  children: ReactElement;
  /** On touch devices, also show a small info button that opens the tip on tap. */
  info?: boolean;
}

/** Tooltip around one focusable element: shows on hover and focus, hides on Escape and blur. */
function HoverTip({ text, children }: Props) {
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

/**
 * Touch variant: long-press the control, or tap the info button, to read the same copy. The tip
 * is a sibling of the children, never their parent: a Radix Popover.Root around the children
 * would capture a Popover trigger among them and open the tip instead of its menu.
 */
function TouchTip({ text, children, info }: Props) {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const fired = useRef(false);
  const wrap = useRef<HTMLSpanElement>(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  const cancel = () => clearTimeout(timer.current);
  return (
    <>
      <span
        ref={wrap}
        className="tip-wrap"
        onPointerDown={(e) => {
          if (e.pointerType === "mouse") return;
          fired.current = false;
          timer.current = setTimeout(() => {
            fired.current = true;
            setOpen(true);
          }, LONG_PRESS_MS);
        }}
        onPointerUp={cancel}
        onPointerCancel={cancel}
        onPointerLeave={cancel}
        onContextMenu={(e) => e.preventDefault()}
        onClickCapture={(e) => {
          if (!fired.current) return;
          fired.current = false;
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        {children}
        {info && (
          <button
            type="button"
            className="tip-info"
            aria-label="What does this do?"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            i
          </button>
        )}
      </span>
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Anchor virtualRef={wrap} />
        <Popover.Portal>
          <Popover.Content
            className="tooltip"
            role="tooltip"
            side="top"
            sideOffset={8}
            collisionPadding={8}
            onOpenAutoFocus={(e) => e.preventDefault()}
            onInteractOutside={(e) => {
              if (e.target instanceof Node && wrap.current?.contains(e.target)) e.preventDefault();
            }}
          >
            {text}
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </>
  );
}

export function Tip(props: Props) {
  const touch = useMediaQuery("(hover: none)");
  return touch ? <TouchTip {...props} /> : <HoverTip {...props} />;
}

export const TipProvider = Tooltip.Provider;
