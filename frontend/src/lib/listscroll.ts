// Keeps a list page's scroll position per origin (path and query) in sessionStorage, so "Back to
// list" lands where the reader left. The scroll region is the page's `.lib-scroll` element.
import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

const PREFIX = "saber-tooth.scroll:";

function read(key: string): number | null {
  try {
    const n = Number(sessionStorage.getItem(key));
    return n > 0 ? n : null;
  } catch {
    return null;
  }
}

function write(key: string, top: number): void {
  try {
    sessionStorage.setItem(key, String(Math.round(top)));
  } catch {
    // Storage can be blocked or full; the list then opens at the top.
  }
}

/**
 * Restores the saved position once `ready` (rows rendered) and tracks later scrolling. `count`
 * is the rows loaded so far: a position past the loaded rows is retried as more load while
 * `hasMore`. Nothing is saved until the restore has finished, so a reset to the top at mount
 * cannot overwrite the stored position.
 */
export function useListScroll(ready: boolean, count: number, hasMore: boolean): void {
  const { pathname, search } = useLocation();
  const key = `${PREFIX}${pathname}${search}`;
  const goal = useRef({ key: "", top: null as number | null, done: true });
  useEffect(() => {
    const el = ready ? document.querySelector<HTMLElement>(".lib-scroll") : null;
    if (!el) return;
    if (goal.current.key !== key) {
      const top = read(key);
      goal.current = { key, top, done: top === null };
    }
    const state = goal.current;
    if (!state.done && state.top !== null) {
      el.scrollTop = state.top;
      if (!hasMore || Math.abs(el.scrollTop - state.top) < 2) state.done = true;
    }
    const onScroll = () => {
      if (state.done) write(key, el.scrollTop);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [ready, count, hasMore, key]);
}
