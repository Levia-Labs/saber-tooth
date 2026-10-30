import { useLayoutEffect, useRef } from "react";
import { quantizeToast, TOAST_FLOOR_PX, TOAST_STEP_PX } from "../lib/quantize";

/**
 * Snaps the element's width up to a multiple of 50 px (times `--ui-scale` in VR), at least 650 px
 * (scaled), measured from its natural content width. CSS min and max width then clamp it, so a
 * narrow viewport gets the full stack width. Re-measures when `deps` change and whenever the
 * element resizes.
 */
export function useQuantizedWidth<T extends HTMLElement>(deps: readonly unknown[]) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const fit = () => {
      el.style.width = ""; // back to fit-content, to read the natural width
      const natural = el.getBoundingClientRect().width;
      const scale = Number.parseFloat(getComputedStyle(el).getPropertyValue("--ui-scale")) || 1;
      const step = TOAST_STEP_PX * scale;
      el.style.width = `${quantizeToast(natural, step, TOAST_FLOOR_PX * scale, Infinity)}px`;
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(el);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}
