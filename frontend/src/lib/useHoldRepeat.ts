import { useCallback, useEffect, useRef, type PointerEvent, type MouseEvent } from "react";

export const HOLD_DELAY_MS = 400;
export const HOLD_INTERVAL_MS = 60;
export const HOLD_FAST_AFTER_MS = 1500;

/**
 * Press-and-hold repeat for a stepper button. `step(fast)` runs on press, again after 400 ms,
 * then every 60 ms; `fast` turns true once the press has lasted 1.5 s. Release, cancel, leave and
 * blur stop it. A click with no pointer (keyboard, assistive tech) steps once.
 */
export function useHoldRepeat(step: (fast: boolean) => void) {
  const latest = useRef(step);
  useEffect(() => {
    latest.current = step;
  });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const started = useRef(0);

  const stop = useCallback(() => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
  }, []);
  useEffect(() => stop, [stop]);

  const tick = useCallback(function next() {
    latest.current(Date.now() - started.current >= HOLD_FAST_AFTER_MS);
    timer.current = setTimeout(next, HOLD_INTERVAL_MS);
  }, []);

  return {
    onPointerDown: (e: PointerEvent) => {
      if (e.button !== 0) return;
      stop();
      started.current = Date.now();
      latest.current(false);
      timer.current = setTimeout(tick, HOLD_DELAY_MS);
    },
    onPointerUp: stop,
    onPointerCancel: stop,
    onPointerLeave: stop,
    onBlur: stop,
    onClick: (e: MouseEvent) => {
      if (e.detail === 0) latest.current(false);
    },
  };
}
