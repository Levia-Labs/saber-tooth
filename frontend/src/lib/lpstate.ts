// The Playlists table's filter and sort, kept for the session so the playlist page can link back
// to it intact and its footer can walk the same order.
import { LP_DEFAULT, type LpState } from "./lpfilters";

const KEY = "saber-tooth.playlists-state";

export function loadLpState(): LpState {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? { ...LP_DEFAULT, ...(JSON.parse(raw) as Partial<LpState>) } : LP_DEFAULT;
  } catch {
    return LP_DEFAULT;
  }
}

export function saveLpState(state: LpState): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Storage can be blocked or full; the footer then uses the default order.
  }
}
