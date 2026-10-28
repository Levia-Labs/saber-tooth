import { createContext, useContext, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface Slot {
  el: HTMLElement | null;
  setEl: (el: HTMLElement | null) => void;
}

const SlotContext = createContext<Slot>({ el: null, setEl: () => {} });

/** Lets a page's toolbar render into the title row (BsTabs) that sits above it in the tree. */
export function BarSlotProvider({ children }: { children: ReactNode }) {
  const [el, setEl] = useState<HTMLElement | null>(null);
  return <SlotContext value={{ el, setEl }}>{children}</SlotContext>;
}

/** The right end of the title row: the place the toolbar is portalled to. */
export function BarSlot() {
  const { setEl } = useContext(SlotContext);
  return <div className="bs-bar-slot" ref={setEl} />;
}

/** Renders `children` in the title row's slot, or in place when there is none. */
export function InBar({ children }: { children: ReactNode }) {
  const { el } = useContext(SlotContext);
  return el ? createPortal(children, el) : <>{children}</>;
}
