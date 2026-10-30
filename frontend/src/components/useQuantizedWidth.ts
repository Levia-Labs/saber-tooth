import { useLayoutEffect, useRef } from "react";
import { quantize, TOAST_STEP_PX } from "../lib/quantize";

/** The mobile breakpoint of alerts.css, where toasts take the full stack width instead. */
export const MOBILE_QUERY = "(max-width: 640px)";

/**
 * Snaps the element's width up to a multiple of 50 px (times `--ui-scale` in VR) measured from its
 * natural content width; re-measures when `deps` change and whenever the element resizes.
 */
export function useQuantizedWidth<T extends HTMLElement>(deps: readonly unknown[]) {
  const ref = useRef<T>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const fit = () => {
      if (window.matchMedia(MOBILE_QUERY).matches) {
        el.style.width = "";
        return;
      }
      el.style.width = ""; // back to fit-content, to read the natural width
      const natural = el.getBoundingClientRect().width;
      const scale = Number.parseFloat(getComputedStyle(el).getPropertyValue("--ui-scale")) || 1;
      el.style.width = `${quantize(natural, TOAST_STEP_PX * scale)}px`;
    };
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(el);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}
