import { useMediaQuery } from "./hooks";

/**
 * The responsive tiers. Each CSS rule uses the query text verbatim; media queries cannot read a
 * variable, so tests/breakpoint.test.ts keeps the stylesheets in step with this file.
 *
 *   - MOBILE_QUERY, below 1300 px: the mobile chrome. The bottom navigation bar and the filter
 *     sheet; the desktop side sheet starts at DESKTOP_QUERY.
 *   - MID_QUERY and COMPACT_QUERY: the table tiers. The lists stay tables below 1300 px and drop
 *     columns by the width they have (lib/columns.ts).
 *   - CARD_QUERY, below 720 px: the lists turn into card rows, because not even the compact column
 *     set fits. CARD_MAX_PX comes from the compact column minimums; tests/cardswitch.test.ts
 *     fails when they and this value disagree.
 *
 * Button labels do not follow a width: they collapse when their row overflows (labelCollapse.ts).
 *
 * VR never enters the mobile chrome or the cards: it keeps the desktop table rows at any size,
 * only bigger. src/vr/scale.ts rewrites the stylesheets and `matchMedia` through `mediaFor`: in
 * VR the mobile and card queries never match, the tiers scale by the UI scale, and
 * DESKTOP_QUERY starts at 1100 px.
 */
export const MOBILE_MAX_PX = 1299.98;
export const MOBILE_QUERY = `(max-width: ${MOBILE_MAX_PX}px)`;
export const DESKTOP_QUERY = "(min-width: 1300px)";
export const MID_QUERY = "(max-width: 1279.98px)";
export const COMPACT_QUERY = "(max-width: 1099.98px)";
export const CARD_MAX_PX = 719.98;
export const CARD_QUERY = `(max-width: ${CARD_MAX_PX}px)`;
/** DESKTOP_QUERY in VR. */
export const VR_DESKTOP_QUERY = "(min-width: 1100px)";
/** Genuinely tiny phones: the toolbar folds into a kebab menu. */
export const TINY_QUERY = "(max-width: 479px)";

/** The query to evaluate for `query` inside or outside VR; any other query passes through. */
export function mediaFor(query: string, vr: boolean): string {
  if (!vr) return query;
  const q = query.trim();
  if (q === MOBILE_QUERY || q === CARD_QUERY) return "not all";
  return q === DESKTOP_QUERY ? VR_DESKTOP_QUERY : query;
}

/** True where the filter sheet replaces the popovers: below 1300 px, and in VR the compact tier. */
export function useNarrow(): boolean {
  const mobile = useMediaQuery(MOBILE_QUERY);
  const compact = useMediaQuery(COMPACT_QUERY);
  return mobile || compact;
}
