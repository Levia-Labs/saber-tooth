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

/** How to load further pages while the saved position lies past the loaded rows. */
export interface MoreRows {
  load: () => void;
  /** A page is loading, or loading is paused (rate limit, failure): wait. */
  busy: boolean;
  /** Most pages to load for one restore. */
  cap?: number;
}

const DEFAULT_CAP = 20;

/**
 * Restores the saved position once `ready` (rows rendered) and tracks later scrolling. `count`
 * is the rows loaded so far. A position past the loaded rows loads further pages through
 * `more` (up to its cap) before scrolling; without `more` it is retried as rows load.
 * Nothing is saved until the restore has finished, so a reset to the top at mount cannot
 * overwrite the stored position.
 */
export function useListScroll(
  ready: boolean,
  count: number,
  hasMore: boolean,
  more?: MoreRows,
): void {
  const { pathname, search } = useLocation();
  const key = `${PREFIX}${pathname}${search}`;
  const goal = useRef({ key: "", top: null as number | null, done: true, loads: 0 });
  const load = more?.load;
  const busy = more?.busy ?? false;
  const cap = more?.cap ?? DEFAULT_CAP;
  useEffect(() => {
    const el = ready ? document.querySelector<HTMLElement>(".lib-scroll") : null;
    if (!el) return;
    if (goal.current.key !== key) {
      const top = read(key);
      goal.current = { key, top, done: top === null, loads: 0 };
    }
    const state = goal.current;
    if (!state.done && state.top !== null) {
      el.scrollTop = state.top;
      const reached = Math.abs(el.scrollTop - state.top) < 2;
      if (reached || !hasMore || (load !== undefined && state.loads >= cap)) {
        state.done = true;
      } else if (load !== undefined && !busy) {
        state.loads += 1;
        load();
      }
    }
    const onScroll = () => {
      if (state.done) write(key, el.scrollTop);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [ready, count, hasMore, key, load, busy, cap]);
}
