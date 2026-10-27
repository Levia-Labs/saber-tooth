import { lazy, type ComponentType, type LazyExoticComponent } from "react";

const FLAG = "st-chunk-reload";
const RELOAD_WINDOW_MS = 10_000;

/** True for the failure of a dynamic import whose file is gone (a new build replaced the old one). */
export function isChunkLoadError(err: unknown): boolean {
  const text = err instanceof Error ? `${err.name} ${err.message}` : String(err);
  return /dynamically imported module|importing a module script|Loading chunk|Unable to preload/i.test(
    text,
  );
}

function recentlyReloaded(): boolean {
  try {
    const at = Number(sessionStorage.getItem(FLAG));
    return Number.isFinite(at) && Date.now() - at < RELOAD_WINDOW_MS;
  } catch {
    return true;
  }
}

/**
 * React.lazy for a route page. A tab opened before a rebuild still points at page chunks the new
 * build deleted; the import then fails and the route crashes. Reload once to pick up the new
 * index, and only throw when the reload did not help.
 */
export function lazyRoute<T extends ComponentType>(
  load: () => Promise<{ default: T }>,
  reload: () => void = () => window.location.reload(),
): LazyExoticComponent<T> {
  return lazy(async () => {
    try {
      return await load();
    } catch (err) {
      if (!isChunkLoadError(err) || recentlyReloaded()) throw err;
      try {
        sessionStorage.setItem(FLAG, String(Date.now()));
      } catch {
        throw err;
      }
      reload();
      return new Promise<never>(() => undefined);
    }
  });
}
